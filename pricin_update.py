import requests
import json
import threading
import time

def get_dexscreener_price(token_address, chain="solana"):
    url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if 'pairs' in data and len(data['pairs']) > 0:
            # Filtrar los pares para obtener solo los de la red Solana
            solana_pairs = [pair for pair in data['pairs'] if pair.get('chainId') == chain]
            if len(solana_pairs) > 0:
                price_in_usdt = next((pair['priceUsd'] for pair in solana_pairs if 'priceUsd' in pair), None)
                if price_in_usdt:
                    return float(price_in_usdt)
                else:
                    return "USDT price not available for this token on Solana"
            else:
                return "Token not found on Solana or price not available"
        else:
            return "Token not found or price not available"
    else:
        return f"Error: {response.status_code}"

def update_price_in_background(token_address, filepath, interval=360):
    while True:
        price = get_dexscreener_price(token_address)
        if isinstance(price, float):
            with open(filepath, 'r+') as file:
                try:
                    data = json.load(file)
                except json.JSONDecodeError:
                    data = {}
                data["price_token_Strawberry"] = price
                file.seek(0)
                json.dump(data, file, indent=4)
                file.truncate()
        time.sleep(interval)

def start_price_update_thread(token_address, filepath, interval=360):
    price_update_thread = threading.Thread(target=update_price_in_background, args=(token_address, filepath, interval))
    price_update_thread.daemon = True
    price_update_thread.start()
