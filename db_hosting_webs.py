import mysql.connector
from mysql.connector import errorcode
from datetime import datetime
import datetime
import json
from variables_use import *

class DatabaseConnection:
    def __init__(self, user_db, password_db, host_db, port_db, database="MINI_platform"):
        self.user_db = user_db
        self.password_db = password_db
        self.host_db = host_db
        self.port_db = port_db
        self.database = database
        self.connection = None
        self.connect()

    def connect(self):
        try:
            self.connection = mysql.connector.connect(
                user=self.user_db,
                password=self.password_db,
                host=self.host_db,
                port=self.port_db,
                database=self.database
            )
            print(f"Connected to database '{self.database}'.")
        except mysql.connector.Error as err:
            if err.errno == errorcode.ER_BAD_DB_ERROR:
                print(f"Database '{self.database}' does not exist. Creating database.")
                try:
                    self.connection = mysql.connector.connect(
                        user=self.user_db,
                        password=self.password_db,
                        host=self.host_db,
                        port=self.port_db
                    )
                    cursor = self.connection.cursor()
                    cursor.execute(f"CREATE DATABASE `{self.database}`")
                    cursor.close()
                    self.connection.close()
                    self.connection = mysql.connector.connect(
                        user=self.user_db,
                        password=self.password_db,
                        host=self.host_db,
                        port=self.port_db,
                        database=self.database
                    )
                    print(f"Connected to database '{self.database}' after creation.")
                except mysql.connector.Error as err:
                    print(f"Failed creating database '{self.database}': {err}")
                    self.connection = None
            else:
                print(f"Error connecting to database '{self.database}': {err}")
                self.connection = None

    def close(self):
        if self.connection and self.connection.is_connected():
            self.connection.close()
            print(f"Connection to database '{self.database}' closed.")

    def execute_query(self, query, params=None):
        if not self.connection:
            print("No database connection.")
            return False, "No database connection."
        try:
            cursor = self.connection.cursor()
            cursor.execute(query, params)
            self.connection.commit()
            cursor.close()
            return True, None
        except mysql.connector.Error as err:
            error_message = f"Error executing query: {err}"
            print(error_message)
            self.connection.rollback()
            return False, error_message

    def execute_read_query(self, query, params=None):
        if not self.connection:
            print("No database connection.")
            return None
        try:
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute(query, params)
            results = cursor.fetchall()
            cursor.close()
            return results
        except mysql.connector.Error as err:
            print(f"Error executing read query: {err}")
            return None

    def fetch_one(self, query, params=None):
        """
        Ejecuta una consulta y devuelve una sola fila.
        """
        if not self.connection:
            print("No database connection.")
            return None
        try:
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute(query, params)
            result = cursor.fetchone()
            cursor.close()
            return result
        except mysql.connector.Error as err:
            print(f"Error executing fetch_one query: {err}")
            return None


class BuildDBWebs:
    def __init__(self, db_connection):
        self.db = db_connection
        self.create_tables()
        # Mapeo de tokens disponibles: tipo_token -> token_address
        self.tokens_available = {
            "MINI": MINI_token_address,    # Reemplaza con la dirección real de MINI
            "PAMBI2": PAMBI2_address       # Reemplaza con la dirección real de PAMBI2
        }

    def create_tables(self):
        self.create_web_articles_table()

    def create_web_articles_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS web_articles (
            id INT AUTO_INCREMENT PRIMARY KEY,
            wallet VARCHAR(255),
            url_web VARCHAR(255) UNIQUE,
            file_html_associate VARCHAR(255),
            alert_web TEXT,
            amount_donations FLOAT DEFAULT 0,
            amount_pays FLOAT DEFAULT 0,
            quanty_donations INT DEFAULT 0,
            quanty_pays INT DEFAULT 0,
            last_donation_date DATE,
            last_pay_date DATE,
            tags_search TEXT,
            ranking_position FLOAT DEFAULT 0,
            pay_price_usd FLOAT DEFAULT 0
        )
        """
        success, error = self.db.execute_query(query)
        if success:
            print("Tabla 'web_articles' creada o ya existe.")
        else:
            print(f"Error al crear la tabla 'web_articles': {error}")

    def get_dexscreener_price(self, token_address):
        """
        Obtiene el precio en USD de un token dado su address desde el archivo JSON guardado.
        """
        try:
            with open('update_charts.json', 'r') as json_file:
                data = json.load(json_file)
                if token_address in data:
                    return data[token_address]['price']
                else:
                    print(f"No se encontraron datos para el token {token_address}")
                    return None
        except Exception as e:
            print(f"Excepción al leer el archivo JSON: {e}")
            return None

    def _get_token_price(self, type_token):
        """
        Obtiene el precio en USD de un token basado en su tipo.
        """
        token_address = self.tokens_available.get(type_token)
        if not token_address:
            raise ValueError(f"Tipo de token no reconocido: {type_token}")
        
        price = self.get_dexscreener_price(token_address)  # Cambiado de type_token a token_address
        if price is None:
            raise ValueError(f"No se pudo obtener el precio para el token: {type_token}")
        
        return price

    def donation_update(self, amount_dotante, date_time, type_token, url_web, signature_tx):
        """
        Actualiza la cantidad de donaciones para un artículo web dado.

        Parámetros:
        - amount_dotante (float): La cantidad de tokens donados.
        - date_time (datetime): La fecha y hora de la donación.
        - type_token (str): El tipo de token donado ('MINI' o 'PAMBI2').
        - url_web (str): La URL del artículo web.
        - signature_tx (str): La firma de la transacción.
        """
        try:
            # Obtener el precio del token en USD
            token_price = self._get_token_price(type_token)
            new_donation_usd = amount_dotante * token_price

            # Consultar los detalles actuales de donaciones para la URL dada
            select_query = """
            SELECT amount_donations, quanty_donations, ranking_position
            FROM web_articles
            WHERE url_web = %s
            """
            result = self.db.fetch_one(select_query, (url_web,))

            if result is None:
                raise ValueError(f"No se encontró un artículo web con url_web: {url_web}")

            current_amount = result['amount_donations']
            current_quanty = result['quanty_donations']
            current_ranking = result['ranking_position']

            updated_amount = current_amount + new_donation_usd
            updated_quanty = current_quanty + 1

            # Determinar si se debe actualizar la fecha de la última donación y ranking
            if updated_amount > 1:
                updated_ranking = current_ranking + 0.000001
                update_query = """
                UPDATE web_articles
                SET amount_donations = %s,
                    last_donation_date = %s,
                    quanty_donations = quanty_donations + 1,
                    ranking_position = %s
                WHERE url_web = %s
                """
                # Usar la fecha actual
                current_date = datetime.datetime.now().date()
                success, error = self.db.execute_query(update_query, (updated_amount, current_date, updated_ranking, url_web))
                if success:
                    print(f"Donación actualizada correctamente para {url_web}.")
                else:
                    print(f"Error al actualizar la donación: {error}")
            else:
                update_query = """
                UPDATE web_articles
                SET amount_donations = %s,
                    quanty_donations = quanty_donations + 1
                WHERE url_web = %s
                """
                success, error = self.db.execute_query(update_query, (updated_amount, url_web))
                if success:
                    print(f"Donación actualizada correctamente para {url_web} sin actualizar la fecha ni el ranking.")
                else:
                    print(f"Error al actualizar la donación: {error}")

            # Opcional: Manejar la firma de la transacción según sea necesario
            # Por ejemplo, almacenar en una tabla separada de transacciones
            # self.log_transaction(signature_tx, ...)

        except Exception as e:
            # Manejar excepciones (por ejemplo, registrar el error)
            print(f"Error al actualizar la donación: {e}")

    # Opcional: Puedes añadir métodos adicionales según tus necesidades
    # def log_transaction(self, signature_tx, ...):
    #     pass

