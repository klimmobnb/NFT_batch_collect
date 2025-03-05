import requests
from web3 import Web3
import time

# Конфигурационные переменные
NFT_CONTRACT_ADDRESS = '0x7b4e69bdb04efbd7cdb834b65e3eb6ed6e973056'  # Адрес контракта NFT
TARGET_ADDRESS = '0xB50Bd0ee3BfaA5ed1684a423005C839B51BdC2be'  # Адрес для перевода NFT
RPC_URL = 'https://monad-testnet.g.alchemy.com/v2/YKM6yoxIxglRwmQElX09ZmKUZOsaVqIW'  # RPC URL
GAS_PRICE_GWEI = '60'  # Цена газа в Gwei
GAS_LIMIT = 100000  # Лимит газа
MAGIC_EDEN_API_KEY = 'Bearer YOUR_API_KEY'  # API-ключ Magic Eden

# ABI для ERC-721 и ERC-1155
ERC721_CONTRACT_ABI = [
    {
        "inputs": [
            {"internalType": "address", "name": "from", "type": "address"},
            {"internalType": "address", "name": "to", "type": "address"},
            {"internalType": "uint256", "name": "tokenId", "type": "uint256"}
        ],
        "name": "safeTransferFrom",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function"
    }
]

ERC1155_CONTRACT_ABI = [
    {
        "inputs": [
            {"internalType": "address", "name": "from", "type": "address"},
            {"internalType": "address", "name": "to", "type": "address"},
            {"internalType": "uint256", "name": "id", "type": "uint256"},
            {"internalType": "uint256", "name": "amount", "type": "uint256"},
            {"internalType": "bytes", "name": "data", "type": "bytes"}
        ],
        "name": "safeTransferFrom",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

# Инициализация Web3
web3 = Web3(Web3.HTTPProvider(RPC_URL))

def load_private_keys(file_path):
    with open(file_path, 'r') as file:
        return [line.strip() for line in file if line.strip()]

def get_address_from_private_key(private_key):
    account = web3.eth.account.from_key(private_key)
    return account.address

def fetch_nfts(address):
    url = f"https://api-mainnet.magiceden.dev/v3/rtp/monad-testnet/users/{address}/tokens/v7?collection={NFT_CONTRACT_ADDRESS}&limit=20"
    headers = {"accept": "*/*", "Authorization": f"Bearer {MAGIC_EDEN_API_KEY}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get("tokens", [])
    else:
        print(f"Ошибка при получении NFT для {address}: {response.status_code}")
        return []

def filter_nfts(nfts_data):
    return [{'identifier': nft['token']['tokenId'], 'type': nft['token']['kind']} for nft in nfts_data]

def transfer_nfts(nfts, private_key):
    sender_address = get_address_from_private_key(private_key)
    sender_balance = web3.eth.get_balance(sender_address)
    gas_cost = float(GAS_PRICE_GWEI) * GAS_LIMIT * (10 ** 9)

    if sender_balance < gas_cost:
        print(f"Недостаточно средств для газа. Требуется: {gas_cost}, доступно: {sender_balance}")
        return

    for nft in nfts:
        token_id = int(nft['identifier'])
        nft_type = nft['type']
        contract_abi = ERC1155_CONTRACT_ABI if nft_type == "erc1155" else ERC721_CONTRACT_ABI
        contract = web3.eth.contract(address=web3.to_checksum_address(NFT_CONTRACT_ADDRESS), abi=contract_abi)
        try:
            nonce = web3.eth.get_transaction_count(sender_address)
            if nft_type == "erc1155":
                txn = contract.functions.safeTransferFrom(
                    sender_address, TARGET_ADDRESS, token_id, 1, b""
                ).build_transaction({
                    'from': sender_address,
                    'gas': GAS_LIMIT,
                    'gasPrice': web3.to_wei(GAS_PRICE_GWEI, 'gwei'),
                    'nonce': nonce
                })
            else:
                txn = contract.functions.safeTransferFrom(
                    sender_address, TARGET_ADDRESS, token_id
                ).build_transaction({
                    'from': sender_address,
                    'gas': GAS_LIMIT,
                    'gasPrice': web3.to_wei(GAS_PRICE_GWEI, 'gwei'),
                    'nonce': nonce
                })
            
            signed_txn = web3.eth.account.sign_transaction(txn, private_key)
            tx_hash = web3.eth.send_raw_transaction(signed_txn.raw_transaction)
            print(f"Отправлена транзакция: {tx_hash.hex()}")

            receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            if receipt.status == 1:
                print(f"Токен {token_id} успешно передан.")
            else:
                print(f"Ошибка при передаче токена {token_id}.")
                
        except Exception as e:
            print(f"Ошибка передачи токена {token_id}: {e}")

def main():
    private_keys = load_private_keys('wallets.txt')
    total_nfts = 0
    all_filtered_nfts = []

    for private_key in private_keys:
        address = get_address_from_private_key(private_key)
        print(f"Получение NFT для адреса: {address}")
        nfts_data = fetch_nfts(address)
        filtered_nfts = filter_nfts(nfts_data)
        total_nfts += len(filtered_nfts)
        all_filtered_nfts.append((private_key, filtered_nfts))
        print(f"Найдено {len(filtered_nfts)} NFT для адреса {address}")

    if total_nfts > 0:
        confirm = input("Перевести все NFT на целевой адрес? (yes/no): ")
        if confirm.lower() == 'yes':
            for private_key, filtered_nfts in all_filtered_nfts:
                transfer_nfts(filtered_nfts, private_key)
        else:
            print("Перевод отменен.")
    else:
        print("NFT для перевода не найдено.")

if __name__ == "__main__":
    main()
