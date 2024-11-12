import requests
import threading
import time
import json

# Diccionario para almacenar los datos de los tokens
token_data = {}


def get_dexscreener_data(token_address):
    """
    Obtiene el precio en USD, volumen de 24 horas, liquidez, marketcap y FDV de un token dado su address utilizando la API de DexScreener.
    """
    try:
        # DexScreener API endpoint
        url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            pair_data = data['pairs'][0]
            price = float(pair_data['priceUsd'])
            volume_24h = float(pair_data['volume']['h24'])
            liquidity = float(pair_data['liquidity']['usd'])
            
            # Obtener marketcap y FDV (si están disponibles en los datos de la API)
            marketcap = pair_data.get('fdv')  # FDV (Fully Diluted Valuation) es una estimación del marketcap futuro
            fdv = marketcap  # FDV es igual al marketcap si se trata del valor completamente diluido
            
            # Actualizar el diccionario con los nuevos datos
            token_data[token_address] = {
                'price': price,
                '24h_volume': volume_24h,
                'liquidity': liquidity,
                'marketcap': marketcap if marketcap is not None else "N/A",
                'fdv': fdv if fdv is not None else "N/A"
            }
        else:
            print(f"Error al obtener los datos del token: {response.status_code}")
    except Exception as e:
        print(f"Excepción al obtener los datos del token: {e}")

def fetch_data_periodically(token_addresses):
    """
    Función que se ejecuta en un hilo separado para obtener datos cada 2 segundos y guardar en un archivo JSON.
    """
    while True:
        for token_address in token_addresses:
            get_dexscreener_data(token_address)
        with open('update_charts.json', 'w') as json_file:
            json.dump(token_data, json_file, indent=4)
        time.sleep(2)
