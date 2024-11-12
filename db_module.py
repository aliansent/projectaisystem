import os
import json
import hashlib
import random
import string
import time
import traceback
from flask import Flask, request, jsonify, make_response
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import mysql.connector
from mysql.connector import errorcode
from markupsafe import escape  
from variables_use import *

def safe_str(var):
    return str(var) if isinstance(var, Markup) else var

def get_dexscreener_price(token_address):
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

class ConnectDB:
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
            cursor = self.connection.cursor()
            cursor.execute(query, params)
            results = cursor.fetchall()
            cursor.close()
            return results
        except mysql.connector.Error as err:
            print(f"Error executing read query: {err}")
            return None

class ToolsExtra:
    def extract_tokens(db: ConnectDB, wallet: str, amount: float):
        # Step 1: Retrieve user account information for the specified wallet
        query = """
            SELECT username_hashed, password_hashed, balance_MINI 
            FROM users_accounts 
            WHERE wallet = %s
        """
        params = (wallet,)
        user_account = db.execute_read_query(query, params)

        if not user_account:
            return False, "Wallet not found."

        username_hashed, password_hashed, balance_MINI = user_account[0]

        # Step 2: Check if the amount to extract is greater than the current balance
        if amount > balance_MINI:
            return False, "Insufficient funds to perform this action."

        # Step 3: Update the balance by subtracting the specified amount
        new_balance = balance_MINI - amount
        update_query = """
            UPDATE users_accounts
            SET balance_MINI = %s
            WHERE wallet = %s
        """
        update_params = (new_balance, wallet)
        success, error = db.execute_query(update_query, update_params)

        if not success:
            return False, error

        # Step 4: Return True if the extraction was successful
        return True, None


class AccountsDBTools:
    def __init__(self, user_db, password_db, host_db, port_db, database="MINI_platform"):
        # Define token addresses
        self.MINI_token_address = MINI_token_address  # Dirección real de MINI DBTool
        self.PAMBI2_address = PAMBI2_address          # Dirección real de PAMBI2

        self.db_connection = ConnectDB(user_db, password_db, host_db, port_db, database)
        if self.db_connection.connection:
            self.create_users_table()
        else:
            print("Failed to connect to main database. Exiting.")
            exit(1)

        # Connect to users_deposits database
        self.users_deposits_connection = ConnectDB(user_db, password_db, host_db, port_db, 'users_deposits')
        if self.users_deposits_connection.connection:
            self.create_transactions_table()
        else:
            print("Failed to connect to users_deposits database. Exiting.")
            exit(1)

    def create_users_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS users_accounts (
            id INT AUTO_INCREMENT PRIMARY KEY,
            wallet VARCHAR(255) UNIQUE,
            username_hashed VARCHAR(255),
            password_hashed VARCHAR(255),
            balance_MINI FLOAT DEFAULT 0.0,
            balance_PAMBI2 FLOAT DEFAULT 0.0,
            address_token_MINI VARCHAR(255) DEFAULT %s,
            address_token_PAMBI2 VARCHAR(255) DEFAULT %s,
            amount_in_usd FLOAT DEFAULT 0.0
        )
        """
        params = (self.MINI_token_address, self.PAMBI2_address)
        self.db_connection.execute_query(query, params)
        print("Table 'users_accounts' created or already exists.")

    def create_transactions_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS transactions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            wallet_sender VARCHAR(255) NOT NULL,
            token_address VARCHAR(255) DEFAULT NULL,
            amount DECIMAL(20, 8) NOT NULL DEFAULT 0.0,
            type ENUM('deposit', 'withdraw', 'verify_signup', 'auth_account') NOT NULL,
            signature_tx VARCHAR(255) UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        self.users_deposits_connection.execute_query(query)
        print("Table 'transactions' created or already exists in 'users_deposits' database.")

    @staticmethod
    def hash_value(value):
        return hashlib.sha256(value.encode()).hexdigest()

    def transaction_exists(self, signature_tx):
        query = "SELECT 1 FROM transactions WHERE signature_tx = %s"
        params = (signature_tx,)
        result = self.users_deposits_connection.execute_read_query(query, params)
        return bool(result)

    def insert_transaction(self, wallet_sender, token_address, amount, type, signature_tx):
        query = """
        INSERT INTO transactions (wallet_sender, token_address, amount, type, signature_tx)
        VALUES (%s, %s, %s, %s, %s)
        """
        params = (wallet_sender, token_address, amount, type, signature_tx)
        self.users_deposits_connection.execute_query(query, params)

    def register_new_user(self, wallet, username, password, signature_tx, balance_MINI=0.0, balance_PAMBI2=0.0):
        try:
            # No es necesario alterar los datos con escape o safe_str
            # Hash the password and username
            password_hashed = self.hash_value(password)
            username_hashed = self.hash_value(username)

            # Obtain current token prices
            price_MINI = get_dexscreener_price(self.MINI_token_address)
            price_PAMBI2 = get_dexscreener_price(self.PAMBI2_address)

            # Ensure balances are floats
            try:
                balance_MINI = float(balance_MINI)
            except (TypeError, ValueError):
                balance_MINI = 0.0

            try:
                balance_PAMBI2 = float(balance_PAMBI2)
            except (TypeError, ValueError):
                balance_PAMBI2 = 0.0

            # Check if wallet exists
            query_check_wallet = "SELECT balance_MINI, balance_PAMBI2 FROM users_accounts WHERE wallet = %s"
            params_check_wallet = (wallet,)
            result_wallet = self.db_connection.execute_read_query(query_check_wallet, params_check_wallet)

            if result_wallet:
                # If the wallet already exists, maintain previous balances if new ones are 0
                previous_balance_MINI = float(result_wallet[0][0])
                previous_balance_PAMBI2 = float(result_wallet[0][1])

                # Maintain previous balances if 0.0 is passed as balance
                balance_MINI = previous_balance_MINI if balance_MINI == 0.0 else balance_MINI + previous_balance_MINI
                balance_PAMBI2 = previous_balance_PAMBI2 if balance_PAMBI2 == 0.0 else balance_PAMBI2 + previous_balance_PAMBI2

                # Recalculate the total in USD based on updated balances
                if price_MINI is None or price_PAMBI2 is None:
                    print("No se pudieron obtener los precios de los tokens. Manteniendo amount_in_usd anterior.")
                    # Obtener amount_in_usd anterior
                    query_get_amount_usd = "SELECT amount_in_usd FROM users_accounts WHERE wallet = %s"
                    params_get_amount_usd = (wallet,)
                    result_amount_usd = self.db_connection.execute_read_query(query_get_amount_usd, params_get_amount_usd)
                    if result_amount_usd:
                        amount_in_usd = float(result_amount_usd[0][0])
                    else:
                        amount_in_usd = 0.0
                else:
                    amount_in_usd = (balance_MINI * price_MINI) + (balance_PAMBI2 * price_PAMBI2)

                # Update existing user
                query_update = """
                UPDATE users_accounts
                SET username_hashed = %s, password_hashed = %s, balance_MINI = %s, balance_PAMBI2 = %s, amount_in_usd = %s
                WHERE wallet = %s
                """
                params_update = (username_hashed, password_hashed, balance_MINI, balance_PAMBI2, amount_in_usd, wallet)
                self.db_connection.execute_query(query_update, params_update)
                print("User updated successfully.")

                # Insert transaction into users_deposits database
                #self.insert_transaction(wallet_sender=wallet, token_address=None, amount=0.0, type='auth_account', signature_tx=signature_tx)

                return "User updated successfully."
            else:
                # Check if username exists
                query_check_username = "SELECT username_hashed FROM users_accounts WHERE username_hashed = %s"
                params_check_username = (username_hashed,)
                result_username = self.db_connection.execute_read_query(query_check_username, params_check_username)

                if result_username:
                    return "The username already exists."
                else:
                    # Calculate amount_in_usd for the new user
                    if price_MINI is None or price_PAMBI2 is None:
                        print("No se pudieron obtener los precios de los tokens. Estableciendo amount_in_usd en 0.")
                        amount_in_usd = 0.0
                    else:
                        amount_in_usd = (balance_MINI * price_MINI) + (balance_PAMBI2 * price_PAMBI2)

                    # Insert new user
                    query_insert = """
                    INSERT INTO users_accounts (wallet, username_hashed, password_hashed, balance_MINI, balance_PAMBI2, amount_in_usd)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """
                    params_insert = (wallet, username_hashed, password_hashed, balance_MINI, balance_PAMBI2, amount_in_usd)
                    self.db_connection.execute_query(query_insert, params_insert)
                    print("User registered successfully.")

                    #self.insert_transaction(wallet_sender=wallet, token_address=None, amount=0.0, type='auth_account', signature_tx=signature_tx)

                    return "User registered successfully."
        except Exception as e:
            print(f"Error in register_new_user (AccountsDBTools.py): {str(e)}")
            print(traceback.format_exc())
            return "Error during user registration."

    def login_session(self, username, password, amount_pay):
        try:
            username_hashed = self.hash_value(username)
            password_hashed = self.hash_value(password)

            query = """
            SELECT wallet, password_hashed, balance_MINI, balance_PAMBI2, amount_in_usd
            FROM users_accounts
            WHERE username_hashed = %s
            """
            params = (username_hashed,)
            result = self.db_connection.execute_read_query(query, params)

            if result:
                user_data = result[0]
                if user_data[1] == password_hashed:
                    current_amount_in_usd = float(user_data[4])
                    try:
                        amount_pay = float(amount_pay)
                    except (TypeError, ValueError):
                        print("Invalid amount_pay value in login_session.")
                        return json.dumps({"error": "Invalid amount_pay value."})

                    print("balance in account: " + str(current_amount_in_usd))
                    print("balance pay: " + str(amount_pay))
                    if current_amount_in_usd < amount_pay:
                        return json.dumps({"error": "Insufficient balance in USD, please deposit more funds."})

                    # Deduct amount_pay from the amount_in_usd
                    new_amount_in_usd = current_amount_in_usd - amount_pay

                    # Update the amount_in_usd in the database
                    update_query = """
                    UPDATE users_accounts
                    SET amount_in_usd = %s
                    WHERE username_hashed = %s
                    """
                    update_params = (new_amount_in_usd, username_hashed)
                    self.db_connection.execute_query(update_query, update_params)

                    user_info = {
                        "wallet": user_data[0],
                        "balance_MINI": float(user_data[2]),
                        "balance_PAMBI2": float(user_data[3]),
                        "amount_in_usd": new_amount_in_usd
                    }
                    return json.dumps(user_info)
                else:
                    print("Incorrect password in login_session.")
                    return json.dumps({"error": "Incorrect password."})
            else:
                print("User not found in login_session.")
                return json.dumps({"error": "User not found."})
        except Exception as e:
            print(f"Error in login_session (AccountsDBTools.py): {str(e)}")
            print(traceback.format_exc())
            return json.dumps({"error": "An error occurred during login."})


class ToolsDB:
    def __init__(self, user_db, password_db, host_db, port_db, database="MINI_platform", withdraw_db="users_deposits_MINI"):
        self.user_db = user_db
        self.password_db = password_db
        self.host_db = host_db
        self.port_db = port_db
        self.database = database
        self.withdraw_db = withdraw_db
        self.connection = None
        self.withdraw_connection = None
        self.users_deposits_connection = None  # Para conectar con 'users_deposits'
        self.create_connection()
        self.create_withdraw_connection()
        self.create_users_deposits_connection()  # Método para conectar con 'users_deposits'
        # Definir direcciones de tokens
        self.MINI_token_address = MINI_token_address  # Dirección real de MINI
        self.PAMBI2_address = PAMBI2_address          # Dirección real de PAMBI2

    def create_connection(self):
        try:
            self.connection = mysql.connector.connect(
                user=self.user_db,
                password=self.password_db,
                host=self.host_db,
                port=self.port_db,
                database=self.database
            )
            print(f"Connected to main database '{self.database}'.")
        except mysql.connector.Error as err:
            if err.errno == errorcode.ER_BAD_DB_ERROR:
                print(f"The main database '{self.database}' does not exist.")
                # Crear la base de datos principal
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
                    print(f"Database '{self.database}' created successfully.")
                    # Reconectar a la base de datos recién creada
                    self.connection.close()
                    self.connection = mysql.connector.connect(
                        user=self.user_db,
                        password=self.password_db,
                        host=self.host_db,
                        port=self.port_db,
                        database=self.database
                    )
                    print(f"Connected to main database '{self.database}' after creation.")
                except mysql.connector.Error as err:
                    print(f"Failed creating database '{self.database}': {err}")
                    self.connection = None
            else:
                print(f"Error connecting to main database: {err}")
                self.connection = None

    def create_withdraw_connection(self):
        try:
            self.withdraw_connection = mysql.connector.connect(
                user=self.user_db,
                password=self.password_db,
                host=self.host_db,
                port=self.port_db,
                database=self.withdraw_db
            )
            print(f"Connected to withdrawals database '{self.withdraw_db}'.")
        except mysql.connector.Error as err:
            if err.errno == errorcode.ER_BAD_DB_ERROR:
                print(f"The withdrawals database '{self.withdraw_db}' does not exist.")
                # Crear la base de datos de withdrawals
                try:
                    self.withdraw_connection = mysql.connector.connect(
                        user=self.user_db,
                        password=self.password_db,
                        host=self.host_db,
                        port=self.port_db
                    )
                    cursor = self.withdraw_connection.cursor()
                    cursor.execute(f"CREATE DATABASE `{self.withdraw_db}`")
                    cursor.close()
                    print(f"Database '{self.withdraw_db}' created successfully.")
                    # Reconectar a la base de datos recién creada
                    self.withdraw_connection.close()
                    self.withdraw_connection = mysql.connector.connect(
                        user=self.user_db,
                        password=self.password_db,
                        host=self.host_db,
                        port=self.port_db,
                        database=self.withdraw_db
                    )
                    print(f"Connected to withdrawals database '{self.withdraw_db}' after creation.")
                except mysql.connector.Error as err:
                    print(f"Failed creating database '{self.withdraw_db}': {err}")
                    self.withdraw_connection = None
            else:
                print(f"Error connecting to withdrawals database: {err}")
                self.withdraw_connection = None

    def create_users_deposits_connection(self):
        try:
            self.users_deposits_connection = mysql.connector.connect(
                user=self.user_db,
                password=self.password_db,
                host=self.host_db,
                port=self.port_db,
                database='users_deposits'
            )
            print(f"Connected to users_deposits database 'users_deposits'.")
        except mysql.connector.Error as err:
            if err.errno == errorcode.ER_BAD_DB_ERROR:
                print(f"The database 'users_deposits' does not exist.")
                # Crear la base de datos 'users_deposits'
                try:
                    self.users_deposits_connection = mysql.connector.connect(
                        user=self.user_db,
                        password=self.password_db,
                        host=self.host_db,
                        port=self.port_db
                    )
                    cursor = self.users_deposits_connection.cursor()
                    cursor.execute(f"CREATE DATABASE `users_deposits`")
                    cursor.close()
                    print(f"Database 'users_deposits' created successfully.")
                    # Reconectar a la base de datos recién creada
                    self.users_deposits_connection.close()
                    self.users_deposits_connection = mysql.connector.connect(
                        user=self.user_db,
                        password=self.password_db,
                        host=self.host_db,
                        port=self.port_db,
                        database='users_deposits'
                    )
                    print(f"Connected to database 'users_deposits' after creation.")
                except mysql.connector.Error as err:
                    print(f"Failed creating database 'users_deposits': {err}")
                    self.users_deposits_connection = None
            else:
                print(f"Error connecting to database 'users_deposits': {err}")
                self.users_deposits_connection = None

    def execute_query(self, query, params=None, connection=None):
        connection = connection or self.connection
        if not connection:
            print("No database connection.")
            return False, "No database connection."
        try:
            cursor = connection.cursor()
            cursor.execute(query, params)
            connection.commit()
            cursor.close()
            return True, None
        except mysql.connector.Error as err:
            error_message = f"Error during query execution: {err}"
            print(error_message)
            print(traceback.format_exc())
            if connection.is_connected():
                try:
                    connection.rollback()
                except mysql.connector.Error as rollback_err:
                    print(f"Error rolling back transaction: {rollback_err}")
                    print(traceback.format_exc())
            return False, error_message

    def execute_read_query(self, query, params=None, connection=None):
        connection = connection or self.connection
        if not connection:
            print("No database connection.")
            return None
        try:
            cursor = connection.cursor()
            cursor.execute(query, params)
            results = cursor.fetchall()
            cursor.close()
            return results
        except mysql.connector.Error as err:
            print(f"Error during read query: {err}")
            print(traceback.format_exc())
            return None

    def table_exists(self, table_name, connection):
        query = "SHOW TABLES LIKE %s"
        result = self.execute_read_query(query, (table_name,), connection)
        exists = bool(result)
        return exists

    def create_wallet_table(self, table_name):
        create_table_query = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            id INT AUTO_INCREMENT PRIMARY KEY,
            wallet_sender VARCHAR(255) NOT NULL,
            token_address VARCHAR(255) NOT NULL,
            amount DECIMAL(20, 8) NOT NULL,
            type ENUM('deposit', 'withdraw', 'verify_signup') NOT NULL,
            signature_tx VARCHAR(255) UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        self.execute_query(create_table_query, connection=self.withdraw_connection)
        print(f"Wallet table '{table_name}' created or already exists.")

    def get_latest_balance(self, table_name):
        query_latest_balance = f"""
        SELECT updated_balance 
        FROM {table_name} 
        ORDER BY id DESC LIMIT 1 
        """
        latest_balance = self.execute_read_query(query_latest_balance, connection=self.connection)
        if latest_balance:
            return float(latest_balance[0][0])
        else:
            return 0.0

    def get_table_name(self, token_type, table_type='accounts'):
        base_name = 'pool_' + table_type
        if token_type == 'MINI':
            return f"{base_name}_MINI"
        elif token_type == 'PAMBI2':
            return f"{base_name}_PAMBI2"
        else:
            raise ValueError("Unsupported token type")

    def transaction_exists(self, table_name, signature_tx):
        query = f"SELECT 1 FROM {table_name} WHERE signature_tx = %s"
        result = self.execute_read_query(query, (signature_tx,), self.withdraw_connection)
        exists = bool(result)
        return exists

    def transaction_exists_global(self, signature_tx):
        query = "SELECT 1 FROM transactions WHERE signature_tx = %s"
        params = (signature_tx,)
        result = self.execute_read_query(query, params, connection=self.users_deposits_connection)
        return bool(result)

    def deposit_tokens(self, wallet_sender, amount, token_type, token_address, wallet_recipient, signature_tx):
        try:
            # Verificar la dirección del token
            if token_address not in [self.MINI_token_address, self.PAMBI2_address]:
                error_msg = "The token address is not correct."
                print(f"Error in deposit_tokens (ToolsDB.py): {error_msg}")
                return {"error": error_msg}

            # Verificar si la transacción ya existe globalmente
            if self.transaction_exists_global(signature_tx):
                error_msg = "This transaction has already been processed."
                print(f"Error in deposit_tokens (ToolsDB.py): {error_msg}")
                return {"error": error_msg}

            balance_column = 'balance_MINI' if token_type == 'MINI' else 'balance_PAMBI2'
            table_name = f'wallet_{wallet_sender}'

            if not self.table_exists(table_name, self.withdraw_connection):
                self.create_wallet_table(table_name)

            if self.transaction_exists(table_name, signature_tx):
                error_msg = "This transaction has already been processed."
                print(f"Error in deposit_tokens (ToolsDB.py): {error_msg}")
                return {"error": error_msg}

            insert_tx_query = f"""
            INSERT INTO {table_name} (wallet_sender, token_address, amount, type, signature_tx)
            VALUES (%s, %s, %s, %s, %s)
            """
            insert_tx_params = (wallet_sender, token_address, float(amount), 'deposit', signature_tx)
            success, error = self.execute_query(insert_tx_query, insert_tx_params, connection=self.withdraw_connection)
            if not success:
                error_msg = f"Failed to insert transaction: {error}"
                print(f"Error in deposit_tokens (ToolsDB.py): {error_msg}")
                return {"error": error_msg}

            table_name_pool = self.get_table_name(token_type, 'accounts')

            # Crear tabla de pool si no existe
            if not self.table_exists(table_name_pool, self.connection):
                self.create_pool_table(table_name_pool, token_address)

            latest_balance = self.get_latest_balance(table_name_pool)
            updated_balance = latest_balance + float(amount)

            query_insert_pool = f"""
            INSERT INTO {table_name_pool} (wallet_source, amount, type_of_movement, updated_balance, address_token)
            VALUES (%s, %s, %s, %s, %s)
            """
            params_insert_pool = (wallet_sender, float(amount), 'deposit_tokens', updated_balance, token_address)
            self.execute_query(query_insert_pool, params_insert_pool)

            # Obtener el precio en USD del token depositado
            token_price = get_dexscreener_price(token_address)
            if token_price is None:
                print("No se pudo obtener el precio del token. No se actualizará amount_in_usd.")
                price_usd = 0.0
            else:
                price_usd = token_price * float(amount)

            # Actualizar balance del usuario
            query_update_user = f"""
            UPDATE users_accounts
            SET {balance_column} = {balance_column} + %s
            WHERE wallet = %s
            """
            params_update_user = (float(amount), wallet_sender)
            self.execute_query(query_update_user, params_update_user)

            # Actualizar amount_in_usd si price_usd es válido
            if price_usd > 0:
                query_update_amount_usd = """
                UPDATE users_accounts
                SET amount_in_usd = amount_in_usd + %s
                WHERE wallet = %s
                """
                params_update_amount_usd = (price_usd, wallet_sender)
                self.execute_query(query_update_amount_usd, params_update_amount_usd)

            # Insertar la transacción en la tabla 'transactions' de 'users_deposits'
            insert_global_tx_query = """
            INSERT INTO transactions (wallet_sender, token_address, amount, type, signature_tx)
            VALUES (%s, %s, %s, %s, %s)
            """
            insert_global_tx_params = (wallet_sender, token_address, float(amount), 'deposit', signature_tx)
            success, error = self.execute_query(insert_global_tx_query, insert_global_tx_params, connection=self.users_deposits_connection)
            if not success:
                error_msg = f"Failed to insert transaction into global transactions: {error}"
                print(f"Error in deposit_tokens (ToolsDB.py): {error_msg}")
                return {"error": error_msg}

            print("Deposit successful.")
            return "Deposit successful"
        except Exception as e:
            print(f"Exception in deposit_tokens (ToolsDB.py): {str(e)}")
            print(traceback.format_exc())
            return {"error": "An unexpected error occurred during deposit."}

    def create_pool_table(self, table_name, token_address):
        create_table_query = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            id INT AUTO_INCREMENT PRIMARY KEY,
            wallet_source VARCHAR(255),
            amount FLOAT,
            type_of_movement VARCHAR(255),
            updated_balance FLOAT,
            address_token VARCHAR(255) DEFAULT '{token_address}'
        )
        """
        self.execute_query(create_table_query, connection=self.connection)
        print(f"Pool table '{table_name}' created or already exists.")

class ToolsChecking:
    def __init__(self, db_connection):
        self.db_connection = db_connection

    def get_wallet_balances(self, wallet):
        query = """
        SELECT balance_MINI, balance_PAMBI2 FROM users_accounts WHERE wallet = %s
        """
        params = (wallet,)
        results = self.db_connection.execute_read_query(query, params)
        if results:
            balance_MINI, balance_PAMBI2 = results[0]
            return float(balance_MINI), float(balance_PAMBI2)
        else:
            return None, None


class CostExtracAccount:
    def __init__(self, user_db, password_db, host_db, port_db, database="MINI_platform"):
        self.db_connection = ConnectDB(user_db, password_db, host_db, port_db, database)
        if not self.db_connection.connection:
            print("Failed to connect to database. Exiting.")
            exit(1)

    def tools_subtract_cost(self, wallet, amount):
        try:
            # Create a cursor object to interact with the database
            cursor = self.db_connection.connection.cursor()
            
            # Select the specific row based on the wallet
            select_query = "SELECT amount_in_usd FROM users_accounts WHERE wallet = %s"
            cursor.execute(select_query, (wallet,))
            result = cursor.fetchone()

            if result:
                current_amount = result[0]
                
                # Subtract the given amount
                new_amount = current_amount - amount
                if new_amount < 0:
                    print("Warning: The resulting amount is negative. Setting amount_in_usd to 0.")
                    new_amount = 0

                # Update the amount_in_usd in the database
                update_query = "UPDATE users_accounts SET amount_in_usd = %s WHERE wallet = %s"
                cursor.execute(update_query, (new_amount, wallet))
                
                # Commit the transaction to save the changes
                self.db_connection.connection.commit()
                print(f"Amount successfully updated. New amount_in_usd for wallet {wallet}: {new_amount}")
            else:
                print(f"Wallet {wallet} not found in the database.")

        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            # Close the cursor
            cursor.close()
