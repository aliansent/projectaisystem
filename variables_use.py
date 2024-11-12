import os

# URLs y direcciones de contratos
url_endpoint_solana = 'https://minimeme.io/solana_chain'
MINI_token_address = "9nmu7zbf1kKNb52cAohAzyjD3yRdG8Pszw15Umsupump"
PAMBI2_address = "3TdsyqMn2sCqxEFf9B8hATCrMEW1Xh2thUTs7fpr2Rur"
wallet_project = "BvFpU5BJnZymBzdQHX91SGVJTMaAm89z6Jr9Z4TaopBG"

# Variables de entorno para credenciales
DB_USER = os.getenv('USERDB')  # Usuario de la base de datos
DB_PASSWORD = os.getenv('PASSWORDDB')  # Contraseña de la base de datos
DB_HOST = os.getenv('DBHOST')  # Host de la base de datos
DB_PORT = os.getenv('PORTDB')  # Puerto de la base de datos

user_db = os.getenv('USERDB')  # Usuario de la base de datos (variable en minúsculas)
password_db = os.getenv('PASSWORDDB')  # Contraseña de la base de datos (variable en minúsculas)
host_db = os.getenv('DBHOST')  # Host de la base de datos (variable en minúsculas)
port_db = os.getenv('PORTDB')  # Puerto de la base de datos (variable en minúsculas)

# Token de Telegram
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT')

# Propietario y APIs 

OWNER_ID = int(os.getenv('ADMIN_TELEGRAM'))
API_SUNO = os.getenv('API_SUNO_KEY')
api_key = os.getenv('API_OPENAI')  # API Key de OpenAI

# ID del modelo finetuneado de OpenAI
model_generated_pages = "ft:gpt-4o-mini-2024-07-18:personal::AG9uqLsN"
