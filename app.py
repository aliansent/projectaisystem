import os
import re
import time
import json
import shutil
import random
import string
import hashlib
import threading
from datetime import datetime, timedelta  # Modificado aquí start_bot
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

import requests
from bs4 import BeautifulSoup

from flask import (
    Flask, render_template, request, jsonify, redirect, 
    url_for, make_response, session, Response, send_from_directory
)
from flask_session import Session
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.security import generate_password_hash, check_password_hash
from markupsafe import escape
from jinja2 import Template

from dotenv import load_dotenv

import logging
from logging.handlers import RotatingFileHandler

import mysql.connector
from mysql.connector import errorcode, pooling

from threading import Thread, Lock
import asyncio

from telegram import (
    Update, InputMediaPhoto, InputMediaVideo, 
    InputMediaAudio, InputMediaDocument
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, 
    ContextTypes, MessageHandler, filters
)

from route_mount import *
from db_module import *
from update_charts import *
from variables_use import *
from db_hosting_webs import DatabaseConnection, BuildDBWebs
import session_module as account_mg
import chat_module as chatMD
import calculator_sessions as calc
import tools_auth_chain as auth_chain



load_dotenv()
conection_webhosting=DatabaseConnection(
    user_db=os.getenv('USERDB'),
    password_db=os.getenv('PASSWORDDB'),
    host_db=os.getenv('DBHOST'),
    port_db=os.getenv('PORTDB'),
    database="MINI_platform")

hosting_connect_db=BuildDBWebs(conection_webhosting)
hosting_connect_db.create_web_articles_table()
# Configuración básica de logging
logging.basicConfig(level=logging.INFO)  # Puedes 10.0 cambiar a DEBUG para más detalles
logger = logging.getLogger(__name__)

prince_per_session = 0.01
app = Flask(__name__)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=60)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY_SERVER')

Session(app)
def generate_static_hash(value):
    return hashlib.sha256(value.encode()).hexdigest()
# Initialize Flask-Limiter for rate limiting
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=["60 per minute"]  # Global limit: 60 requests per minute
)

# Initialize Database Connections
conection_webhosting = DatabaseConnection(
    user_db=os.getenv('USERDB'),
    password_db=os.getenv('PASSWORDDB'),
    host_db=os.getenv('DBHOST'),
    port_db=os.getenv('PORTDB'),
    database="MINI_platform"
)

hosting_connect_db = BuildDBWebs(conection_webhosting)
hosting_connect_db.create_web_articles_table()

db_mini_platform = ConnectDB(
    user_db=DB_USER,
    password_db=DB_PASSWORD,
    host_db=DB_HOST,
    port_db=DB_PORT,
    database='MINI_platform'
)

db_airdrop_mini_task = ConnectDB(
    user_db=DB_USER,
    password_db=DB_PASSWORD,
    host_db=DB_HOST,
    port_db=DB_PORT,
    database='airdrop-mini-task'
)
# Global Variables Classes
class GlobalVariables:
    def __init__(self):
        self.inactivity_period = 5 * 24 * 60 * 60  # 5 days
        self.wallet_peding_auth = {}
        self.wallet_peding_auth_times = {}
        self.pendding_verify_signup = {}
        self.wallet_project = wallet_project  # Ensure wallet_project is defined in variables_use
        self.pending_web_upload = {}
        self.html_current_code = {}
        self.sessions_airdrop = {}  # Handle airdrop sessions here
        self.active_tasks = {}
        self.tasks_lock = Lock()
        self.sessions = {}
        self.session_times = {}

class ChatSessionManager:
    def __init__(self):
        self.ChatHistory = {}
        self.chat_module = {}
        self.chattimes = {}
        self.sessions_online = {}
        self.account_sessions_global = {}
        self.sesion_remove_inactive_time = 24 * 60 * 60  # 1 day
        self.hashAvalible = []
        self.hash_invite_sessions = {}
        self.hash_apunt = {}
        self.hash_sesions_index = []
        self.session_pricings = {}
        self.html_current_code = {}
        self.hash_invite_session_avalible = []
        self.invited_nick_name = []
        self.hashsessions_init_invited = []
        self.chat_history_locks = {}  # Handle locks per chat hash
        self.global_lock = threading.Lock()  # Optional: Global lock

global_vars = GlobalVariables()
chat_sessions = ChatSessionManager()

# Class to handle MySQL database connections with pooling
class ConnectDB:
    def __init__(self, user_db, password_db, host_db, port_db, database):
        self.user_db = user_db
        self.password_db = password_db
        self.host_db = host_db
        self.port_db = port_db
        self.database = database
        self.pool = None
        self.initialize_pool()
        self.ensure_database()

    def initialize_pool(self):
        try:
            self.pool = pooling.MySQLConnectionPool(
                pool_name="mypool_" + self.database,
                pool_size=10,  # Adjust the pool size as needed
                pool_reset_session=True,
                user=self.user_db,
                password=self.password_db,
                host=self.host_db,
                port=self.port_db,
                database=self.database
            )
            print(f"Connection pool 'mypool_{self.database}' created successfully.")
        except mysql.connector.Error as err:
            print(f"Error creating connection pool: {err}")
            self.pool = None

    def ensure_database(self):
        if not self.pool:
            try:
                temp_conn = mysql.connector.connect(
                    user=self.user_db,
                    password=self.password_db,
                    host=self.host_db,
                    port=self.port_db
                )
                temp_cursor = temp_conn.cursor()
                temp_cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.database}")
                temp_cursor.close()
                temp_conn.close()
                print(f"Database '{self.database}' ensured.")
                # Re-initialize the pool with the new database
                self.initialize_pool()
            except mysql.connector.Error as err:
                print(f"Error ensuring database '{self.database}': {err}")

    def execute_query(self, query, params=None):
        if not self.pool:
            print("No connection pool available.")
            return False, "No connection pool available."
        try:
            conn = self.pool.get_connection()
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            cursor.close()
            conn.close()
            return True, None
        except mysql.connector.Error as err:
            error_message = f"Error executing query: {err}"
            print(error_message)
            return False, error_message

    def execute_read_query(self, query, params=None):
        if not self.pool:
            print("No connection pool available.")
            return None
        try:
            conn = self.pool.get_connection()
            cursor = conn.cursor()
            cursor.execute(query, params)
            results = cursor.fetchall()
            cursor.close()
            conn.close()
            return results
        except mysql.connector.Error as err:
            print(f"Error executing read query: {err}")
            return None

# Initialize the connection to the MINI_platform database
db_mini_platform = ConnectDB(
    user_db=DB_USER,
    password_db=DB_PASSWORD,
    host_db=DB_HOST,
    port_db=DB_PORT,
    database='MINI_platform'
)

# Initialize the connection to the airdrop-mini-task database
db_airdrop_mini_task = ConnectDB(
    user_db=DB_USER,
    password_db=DB_PASSWORD,
    host_db=DB_HOST,
    port_db=DB_PORT,
    database='airdrop-mini-task'
)

# Function to generate a random 18-character hexadecimal hash
def generate_hash_mask():
    return ''.join(random.choices('0123456789abcdef', k=18))

# Function to ensure the airdrop_account_user table exists
def ensure_airdrop_table():
    create_table_query = """
        CREATE TABLE IF NOT EXISTS airdrop_account_user (
            id_telegram VARCHAR(50) PRIMARY KEY,
            hash_mask VARCHAR(18),
            point_for_airdrop INT DEFAULT 0
        )
    """
    success, error = db_mini_platform.execute_query(create_table_query)
    if not success:
        print(f"Error creating airdrop_account_user table: {error}")

# Ensure the table exists on startup
ensure_airdrop_table()

# Telegram bot handlers and functions
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    # Check if the user already exists
    select_query = "SELECT hash_mask FROM airdrop_account_user WHERE id_telegram = %s"
    result = db_mini_platform.execute_read_query(select_query, (user_id,))

    if result:
        # Existing user, use the same hash_mask
        existing_hash = result[0][0]
        print(f"Existing user: id_telegram={user_id}, hash_mask={existing_hash}")
        hash_mask = existing_hash
    else:
        # New user, generate a new hash_mask
        hash_mask = generate_hash_mask()
        insert_query = "INSERT INTO airdrop_account_user (id_telegram, hash_mask, point_for_airdrop) VALUES (%s, %s, %s)"
        success, error = db_mini_platform.execute_query(insert_query, (user_id, hash_mask, 0))
        if success:
            print(f"New user registered: id_telegram={user_id}, hash_mask={hash_mask}")
        else:
            print(f"Error registering new user: {error}")
            await update.message.reply_text("There was an error registering you. Please try again.")
            return

    # Send the game link to the user
    game_url = f"https://minimeme.io/game/{hash_mask}"
    await update.message.reply_text(
        f"Welcome! Access the game through this link: {game_url}\n\n"
        "⚠️ Warning: Do not share this link with anyone. It grants direct access to your game session."
    )

async def game_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    # Get the hash_mask of the user
    select_query = "SELECT hash_mask FROM airdrop_account_user WHERE id_telegram = %s"
    result = db_mini_platform.execute_read_query(select_query, (user_id,))

    if result:
        hash_mask = result[0][0]
        game_url = f"https://minimeme.io/game/{hash_mask}"
        await update.message.reply_text(f"Link to your game: {game_url}. Make sure you do not share this link with anyone, it is the access link to your game session \nYour hash: {hash_mask}")

    else:
        await update.message.reply_text("You are not registered yet. Please use /start to register.")

# New handler for sending global messages
async def send_global(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sender_id = update.effective_user.id
    if sender_id != OWNER_ID:
        # If the user is not the owner, ignore the command
        return

    # Get all user IDs who have started the bot
    select_query = "SELECT id_telegram FROM airdrop_account_user"
    users = db_mini_platform.execute_read_query(select_query)
    if not users:
        await update.message.reply_text("There are no users to send the message to.")
        return

    user_ids = [int(user[0]) for user in users]

    # Get the message text, excluding the command
    message_text = update.message.text
    if message_text and message_text.startswith('/send_global'):
        # Remove the command from the message text
        message_text = message_text.partition(' ')[2]
        if message_text:
            message_text = message_text.strip()
        else:
            message_text = ""

    # Get the caption, excluding the command
    caption = update.message.caption
    if caption and caption.startswith('/send_global'):
        # Remove the command from the caption
        caption = caption.partition(' ')[2]
        if caption:
            caption = caption.strip()
        else:
            caption = ""

    # Get media if any
    media_group = []
    if update.message.media_group_id:
        # It's a media group
        media_messages = await context.bot.get_updates(offset=update.update_id - 10)
        for msg_update in media_messages:
            msg = msg_update.message
            if msg.media_group_id == update.message.media_group_id:
                if msg.photo:
                    media_group.append(InputMediaPhoto(media=msg.photo[-1].file_id))
                elif msg.video:
                    media_group.append(InputMediaVideo(media=msg.video.file_id))
                elif msg.document:
                    media_group.append(InputMediaDocument(media=msg.document.file_id))
    else:
        # Single message
        if update.message.photo:
            media_group.append(InputMediaPhoto(media=update.message.photo[-1].file_id))
        elif update.message.video:
            media_group.append(InputMediaVideo(media=update.message.video.file_id))
        elif update.message.audio:
            media_group.append(InputMediaAudio(media=update.message.audio.file_id))
        elif update.message.document:
            media_group.append(InputMediaDocument(media=update.message.document.file_id))

    # Send the message to each user
    for user_id in user_ids:
        try:
            if media_group:
                if len(media_group) > 1:
                    # Send as a media group
                    if caption or message_text:
                        media_group[0].caption = caption or message_text
                    await context.bot.send_media_group(chat_id=user_id, media=media_group)
                else:
                    # Send a single media
                    media_item = media_group[0]
                    media_caption = caption or message_text
                    if isinstance(media_item, InputMediaPhoto):
                        await context.bot.send_photo(chat_id=user_id, photo=media_item.media, caption=media_caption)
                    elif isinstance(media_item, InputMediaVideo):
                        await context.bot.send_video(chat_id=user_id, video=media_item.media, caption=media_caption)
                    elif isinstance(media_item, InputMediaAudio):
                        await context.bot.send_audio(chat_id=user_id, audio=media_item.media, caption=media_caption)
                    elif isinstance(media_item, InputMediaDocument):
                        await context.bot.send_document(chat_id=user_id, document=media_item.media, caption=media_caption)
            else:
                # Only text
                await context.bot.send_message(chat_id=user_id, text=message_text)
            await asyncio.sleep(0.05)  # Pause between messages
        except Exception as e:
            logger.error(f"Error sending message to {user_id}: {e}")

async def new_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sender_id = update.effective_user.id
    if sender_id != OWNER_ID:
        await update.message.reply_text("You are not authorized to use this command.")
        return

    # Get the message text, excluding the command
    message_text = update.message.text
    if message_text and message_text.startswith('/new_task'):
        # Remove the command from the message text
        json_text = message_text.partition(' ')[2]
        if json_text:
            json_text = json_text.strip()
        else:
            await update.message.reply_text("Please provide a JSON object after the command.")
            return
    else:
        await update.message.reply_text("Invalid command usage.")
        return

    # Parse the JSON
    try:
        task_data = json.loads(json_text)
    except json.JSONDecodeError as e:
        await update.message.reply_text(f"Invalid JSON format: {e}")
        return

    # Extract required fields
    required_fields = ['text', 'url_task', 'time_online', 'points_won', 'url_redirect_task']
    missing_fields = [field for field in required_fields if field not in task_data]
    if missing_fields:
        await update.message.reply_text(f"The following required fields are missing: {', '.join(missing_fields)}")
        return

    text = task_data['text']
    url_task = task_data['url_task']
    time_online = task_data['time_online']
    points_won = task_data['points_won']
    url_redirect_task = task_data['url_redirect_task']

    # Validate fields
    try:
        time_online_hours = float(time_online)
        points_won = int(points_won)
        if time_online_hours <= 0 or points_won <= 0:
            await update.message.reply_text("The fields 'time_online' and 'points_won' must be positive numbers.")
            return
    except ValueError:
        await update.message.reply_text("Invalid values for 'time_online' or 'points_won'.")
        return

    # Calculate expiration time
    expiration_time = datetime.utcnow() + timedelta(hours=time_online_hours)

    # Add the task to global_vars.active_tasks
    with global_vars.tasks_lock:
        global_vars.active_tasks[url_task] = {
            'text': text,
            'url_task': url_task,
            'expiration_time': expiration_time,
            'points_won': points_won,
            'url_redirect_task': url_redirect_task
        }

    # Set up a timer to remove the task after 'time_online_hours'
    def remove_task():
        with global_vars.tasks_lock:
            del global_vars.active_tasks[url_task]
        print(f"The task {url_task} has expired and has been removed.")

    timer = threading.Timer(time_online_hours * 3600, remove_task)
    timer.start()

    # Build the message
    task_url = f"https://minimeme.io/task_for_airdrop/{url_task}"
    message_to_send = f"{text}\nComplete the task here: {task_url}"

    # Send the message to all users
    select_query = "SELECT id_telegram FROM airdrop_account_user"
    users = db_mini_platform.execute_read_query(select_query)
    if not users:
        await update.message.reply_text("There are no users to send the message to.")
        return

    user_ids = [int(user[0]) for user in users]

    for user_id in user_ids:
        try:
            await context.bot.send_message(chat_id=user_id, text=message_to_send)
            await asyncio.sleep(0.05)  # Pause between messages
        except Exception as e:
            logger.error(f"Error sending message to {user_id}: {e}")

    # Send confirmation to the admin
    await update.message.reply_text("Complete this new task and earn more points for the airdrop! 🚀")

# Error handler for the Telegram bot
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(msg="Exception while handling an update:", exc_info=context.error)
    # Optionally, notify the admin or take corrective actions
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text("An error occurred. Please try again later.")
def run_telegram_bot():
    import asyncio
    global application
    asyncio.set_event_loop(asyncio.new_event_loop())
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Añade tus handlers aquí
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("game", game_command))
    application.add_handler(CommandHandler("send_global", send_global))
    application.add_handler(CommandHandler("new_task", new_task))

    # Añade el manejador de errores
    application.add_error_handler(error_handler)

    # Inicia el bot sin registrar manejadores de señales
    application.run_polling(stop_signals=None)

# Function to generate a session_id
def generate_session_id():
    return uuid4().hex

# Function to log errors and respond
def log_and_respond(error_message, status_code):
    print(f"Error: {error_message}")  # Log the error to the console
    return jsonify({"error": error_message}), status_code

# Function to ensure that the user's table exists in 'airdrop-mini-task' database
def ensure_user_task_table(id_user):
    # Check if the table with the name id_user exists
    table_exists_query = """
        SELECT COUNT(*)
        FROM information_schema.tables
        WHERE table_name = %s AND table_schema = %s
    """
    table_exists = db_airdrop_mini_task.execute_read_query(table_exists_query, (id_user, db_airdrop_mini_task.database))
    if table_exists and table_exists[0][0] == 0:
        # Table does not exist, create it
        create_table_query = f"""
            CREATE TABLE `{id_user}` (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(255),
                task_complete VARCHAR(255),
                amount INT DEFAULT 0,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        success, error = db_airdrop_mini_task.execute_query(create_table_query)
        if not success:
            return False, error
    else:
        # Check if 'username' and 'amount' columns exist; if not, add them
        columns_query = """
            SELECT column_name FROM information_schema.columns
            WHERE table_name = %s AND table_schema = %s
        """
        columns = db_airdrop_mini_task.execute_read_query(columns_query, (id_user, db_airdrop_mini_task.database))
        existing_columns = [column[0] for column in columns] if columns else []
        
        if 'username' not in existing_columns:
            add_username_column = f"""
                ALTER TABLE `{id_user}` ADD COLUMN username VARCHAR(255)
            """
            success, error = db_airdrop_mini_task.execute_query(add_username_column)
            if not success:
                return False, error
        
        if 'amount' not in existing_columns:
            add_amount_column = f"""
                ALTER TABLE `{id_user}` ADD COLUMN amount INT DEFAULT 0
            """
            success, error = db_airdrop_mini_task.execute_query(add_amount_column)
            if not success:
                return False, error

    return True, None

# Route to handle the completion of follow tasks
@app.route('/follow_task_complete', methods=['POST'])
def follow_task_complete():
    # Get data from the POST request
    data = request.json
    if not data or 'username' not in data or 'social_media' not in data:
        return log_and_respond("Missing required data: username and social_media", 400)

    username = data['username']
    social_media = data['social_media']

    # Clean up social_media to remove punctuation and make it lowercase
    import re
    social_media_cleaned = re.sub(r'[^\w\s]', '', social_media).strip().lower()

    # Map social media names to task types
    social_media_task_map = {
        'xcom': 'x.com_follow',
        'x': 'x.com_follow',
        'telegram': 'telegram_follow',
        'tiktok': 'tiktok_follow'
        # Add more mappings as needed
    }

    # Debugging output
    print(f"Received social_media: '{social_media}', cleaned: '{social_media_cleaned}'")

    task_complete = social_media_task_map.get(social_media_cleaned)
    if not task_complete:
        return log_and_respond(f"Unsupported social media platform: {social_media}", 400)

    # Get user_hash from the cookie
    user_hash = request.cookies.get('user_hash')
    if not user_hash:
        return log_and_respond("Cookie 'user_hash' not found", 400)

    # Get session data
    session_data = global_vars.sessions_airdrop.get(user_hash)
    if not session_data:
        return log_and_respond("Invalid user_hash or session expired", 400)

    id_user = session_data['id_user']

    # Ensure the user's table exists in 'airdrop-mini-task' database
    success, error = ensure_user_task_table(id_user)
    if not success:
        return log_and_respond(f"Error ensuring user's task table: {error}", 500)

    # **Nuevo bloque de código: Verificar si la tarea ya existe para el usuario**
    check_query = f"""
        SELECT * FROM `{id_user}` 
        WHERE username = %s AND task_complete = %s
        LIMIT 1
    """
    success, result = db_airdrop_mini_task.execute_query(check_query, (username, task_complete))
    if not success:
        return log_and_respond(f"Error checking existing tasks: {result}", 500)
    
    if result:
        return log_and_respond(
            "This task has already been completed previously and cannot be completed again.", 
            400
        )
    # **Fin del bloque de verificación**

    # Insert the task completion into the user's table
    insert_query = f"""
        INSERT INTO `{id_user}` (username, task_complete, amount)
        VALUES (%s, %s, %s)
    """
    # For task completions, amount can be set to 0 or the appropriate value
    success, error = db_airdrop_mini_task.execute_query(insert_query, (username, task_complete, 5000))
    if not success:
        return log_and_respond(f"Error inserting into user's task table: {error}", 500)

    return jsonify({
        "message": "Task completion recorded successfully",
        "task_complete": task_complete
    }), 200

# Route to handle the airdrop of points granted
@app.route('/given_points_airdrop', methods=['POST'])
def given_points_airdrop():
    # Get data from the POST request
    data = request.json
    if not data or 'amount_point' not in data:
        return log_and_respond("Missing required data: amount_point", 400)

    amount_point = data['amount_point']
    # Convert amount_point from 0-1 to 0-1000
    try:
        amount = int(float(amount_point) * 100)
    except ValueError:
        return log_and_respond("Invalid value for amount_point", 400)

    current_time = datetime.utcnow()

    # Get user_hash from the cookie
    user_hash = request.cookies.get('user_hash')
    if not user_hash:
        return log_and_respond("Cookie 'user_hash' not found", 400)

    # Get session data
    session_data = global_vars.sessions_airdrop.get(user_hash)
    if not session_data:
        return log_and_respond("Invalid user_hash or session expired", 400)

    id_user = session_data['id_user']
    last_time = session_data['time_now']
    last_subtract_time = session_data.get('time_subtract_points', current_time)

    elapsed_time = (current_time - last_time).total_seconds()
    elapsed_subtract_time = (current_time - last_subtract_time).total_seconds()

    # Update time_subtract_points each time
    session_data['time_subtract_points'] = current_time

    # Check if more than 6 hours have passed since the last update
    if elapsed_subtract_time >= 6 * 3600:
        # Subtract 0.9% of the user's total points
        total_points = get_user_balance(id_user)
        points_to_subtract = int(total_points * 0.009)
        if points_to_subtract > 0:
            # Subtract points by inserting a negative amount in the user's table
            success, error = ensure_user_task_table(id_user)
            if not success:
                return log_and_respond(f"Error ensuring user's task table: {error}", 500)

            insert_query = f"""
                INSERT INTO `{id_user}` (username, task_complete, amount)
                VALUES (%s, %s, %s)
            """
            # Using 'points_decay' as the task_complete type for point subtraction
            success, error = db_airdrop_mini_task.execute_query(insert_query, (None, 'points_decay', -points_to_subtract))
            if not success:
                return log_and_respond(f"Error inserting into user's task table: {error}", 500)
            # Update time_subtract_points in the session
            session_data['time_subtract_points'] = current_time

    # Always insert the received points into the database
    # Ensure the user's table exists
    success, error = ensure_user_task_table(id_user)
    if not success:
        return log_and_respond(f"Error ensuring user's task table: {error}", 500)

    # Insert the points as a task_complete type 'gameplay_given_points'
    insert_query = f"""
        INSERT INTO `{id_user}` (username, task_complete, amount)
        VALUES (%s, %s, %s)
    """
    # Here, 'gameplay_given_points' signifies that the points are awarded through gameplay
    success, error = db_airdrop_mini_task.execute_query(insert_query, (None, 'gameplay_given_points', amount))
    if not success:
        return log_and_respond(f"Error inserting into user's task table: {error}", 500)

    # Check if more than 30 seconds have passed since the last check
    if elapsed_time >= 60*10:
        # Update time_now in the session
        session_data['time_now'] = current_time

        # Check if the user has completed the required tasks
        missing_tasks = get_missing_tasks(id_user)
        if missing_tasks:
            missing_social = [task.replace('_follow', '').capitalize() for task in missing_tasks]
            error_message = f"To continue and earn 5000 points, you need to follow us on: {', '.join(missing_social)}."
            return jsonify({"error": error_message, "balance": get_user_balance(id_user)}), 400

    # Always get the total balance of points from the database
    total_points = get_user_balance(id_user)

    return jsonify({
        "message": "Points received successfully",
        "amount": amount,
        "balance": total_points
    })

# Function to get the total balance of points for a user
def get_user_balance(id_user):
    sum_query = f"""
        SELECT IFNULL(SUM(amount), 0) FROM `{id_user}`
    """
    result = db_airdrop_mini_task.execute_read_query(sum_query)
    total_points = result[0][0] if result and result[0][0] is not None else 0
    return total_points

# Function to check for missing tasks
def get_missing_tasks(id_user):
    tasks_query = f"""
        SELECT DISTINCT task_complete FROM `{id_user}`
    """
    completed_tasks = db_airdrop_mini_task.execute_read_query(tasks_query)
    completed_tasks = [task[0] for task in completed_tasks] if completed_tasks else []

    required_tasks = ['x.com_follow', 'telegram_follow', 'tiktok_follow']
    missing_tasks = [task for task in required_tasks if task not in completed_tasks]
    return missing_tasks

# Route to handle the game page
@app.route('/game/', defaults={'id_original_user': None})
@app.route('/game/<id_original_user>')
def game_playing(id_original_user):
    if id_original_user:
        # First time accessing with 'id_original_user'
        id_user = id_original_user
        # Generate a random hash to mask the original id
        user_hash = generate_session_id()
        # Initialize the session with time_now and time_subtract_points
        global_vars.sessions_airdrop[user_hash] = {
            'id_user': id_user,
            'time_now': datetime.utcnow(),
            'time_subtract_points': datetime.utcnow()
        }
        # Set the 'user_hash' cookie and pass it to the template
        response = make_response(render_template("spiner_game.html", user_hash=user_hash))
        response.set_cookie('user_hash', user_hash, secure=True, httponly=True, samesite='Strict')
        return response
    else:
        # Get 'user_hash' from the cookie
        user_hash = request.cookies.get('user_hash')
        if not user_hash:
            # No 'user_hash' in the cookie
            return jsonify({"error": "Cookie 'user_hash' not found"}), 400
        # Get session data
        session_data = global_vars.sessions_airdrop.get(user_hash)
        if not session_data:
            return jsonify({"error": "Invalid user_hash or session expired"}), 400
        # Proceed to render the game and pass 'user_hash' to the template
        return render_template("spiner_game.html", user_hash=user_hash)

# Route to handle tasks for airdrop You have already completed this task
@app.route('/task_for_airdrop/<path:url_task>')
def task_for_airdrop(url_task):
    with global_vars.tasks_lock:
        task = global_vars.active_tasks.get(url_task)
        if not task:
            return redirect(url_for('game_playing'))

        # Check if the task has expired
        current_time = datetime.utcnow()
        if current_time >= task['expiration_time']:
            # Task has expired, remove it
            del global_vars.active_tasks[url_task]
            return redirect(url_for('game_playing'))

    # Get user_hash from the cookie
    user_hash = request.cookies.get('user_hash')
    if not user_hash:
        return jsonify({"error": "Cookie 'user_hash' not found"}), 400

    # Get session data
    session_data = global_vars.sessions_airdrop.get(user_hash)
    if not session_data:
        return jsonify({"error": "Invalid user_hash or session expired"}), 400

    id_user = session_data['id_user']

    # Ensure the user's table exists
    success, error = ensure_user_task_table(id_user)
    if not success:
        return jsonify({"error": f"Error ensuring user's task table: {error}"}), 500

    # Insert into user's table the points_won, with task_complete as 'task_ordinal_complete'
    insert_query = f"""
        INSERT INTO `{id_user}` (username, task_complete, amount)
        VALUES (%s, %s, %s)
    """
    # Check if the user has already completed this task
    select_query = f"""
        SELECT COUNT(*) FROM `{id_user}`
        WHERE task_complete = %s
    """
    result = db_airdrop_mini_task.execute_read_query(select_query, (url_task,))
    if result and result[0][0] > 0:
        # User has already completed this task
        return jsonify({"error": "You have already completed this task."}), 400

    success, error = db_airdrop_mini_task.execute_query(insert_query, (None, url_task, task['points_won']))
    if not success:
        return jsonify({"error": f"Error inserting into user's task table: {error}"}), 500

    # Redirect to url_redirect_task
    return redirect(task['url_redirect_task'])

# Function to handle periodic task checks (placeholder for future use)
def check_airdrop_tasks_per_table(table_name):
    asyncio.run(check_airdrop_tasks(table_name))

async def check_airdrop_tasks(table_name):
    try:
        pass  # Add additional logic here if needed
    except Exception as e:
        print(f"Error in check_airdrop_tasks for table {table_name}: {e}")

# Function to start task checks in separate threads
def start_check_airdrop_tasks():
    # Get the list of tables in the 'airdrop-mini-task' database
    tables_query = """
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = %s
    """
    tables = db_airdrop_mini_task.execute_read_query(tables_query, (db_airdrop_mini_task.database,))
    if tables:
        for table in tables:
            table_name = table[0]
            # Start a thread for each table
            task_thread = Thread(target=check_airdrop_tasks_per_table, args=(table_name,), daemon=True)
            task_thread.start()

# Function to start the Telegram bot in a separate thread
def start_bot():
    bot_thread = Thread(target=run_telegram_bot, name="TelegramBotThread", daemon=True)
    bot_thread.start()

# Function to schedule periodic task checks
def schedule_task_checks():
    while True:
        start_check_airdrop_tasks()
        time.sleep(60)  # Wait 60 seconds before the next check

# Start the bot and task scheduler before running the Flask server
start_bot()
task_scheduler_thread = Thread(target=schedule_task_checks, name="TaskSchedulerThread", daemon=True)
task_scheduler_thread.start()

# Function to generate a random hex code
def generate_hex_code(length=18):
    return ''.join(random.choices('0123456789abcdef', k=length))

# Function to sanitize URL for web hosting
def sanitize_url_web(url_web):
    # Allow only alphanumeric characters and some special characters
    valid_chars = f"-_.() {string.ascii_letters}{string.digits}"
    sanitized = ''.join(c for c in url_web if c in valid_chars)
    # Replace spaces with underscores
    sanitized = sanitized.replace(' ', '_')
    return sanitized or 'default_site'

# Function to get hosting path
def get_hosting_path(url_web):
    sanitized_url_web = sanitize_url_web(url_web)
    hosting_base_path = Path('/hosting_mini/websites')
    hosting_path = hosting_base_path / sanitized_url_web
    logging.debug(f'Hosting path for {sanitized_url_web}: {hosting_path}')
    return hosting_path

# Function to download and replace resources in HTML
def download_and_replace_resources(html_content, url_web):
    # Ensure hosting_path is a Path object
    hosting_path = Path(get_hosting_path(url_web))  # Convert to Path if necessary
    logging.debug(f'Using hosting path: {hosting_path}')
    
    # Create the specific path for the website
    website_path = hosting_path / url_web
    resources_dir = website_path / 'resources'  # Directory for resources
    
    # Ensure the main directory for the website exists
    try:
        website_path.mkdir(parents=True, exist_ok=True)
        logging.debug(f'Website directory ensured: {website_path}')
    except Exception as e:
        logging.error(f'Error creating website directory {website_path}: {e}')
        return  # Exit the function if the main directory cannot be created
    
    soup = BeautifulSoup(html_content, 'html.parser')

    # Define tags and their attributes that may contain resource URLs
    tags_attributes = {
        'img': ['src', 'srcset', 'data-src'],
        'script': ['src'],
        'link': ['href'],
        'audio': ['src'],
        'video': ['src'],
        'source': ['src', 'srcset'],
    }

    for tag_name, attributes in tags_attributes.items():
        for tag in soup.find_all(tag_name):
            for attr in attributes:
                resource_url = tag.get(attr)
                if resource_url and resource_url.startswith('http'):
                    try:
                        response = requests.get(resource_url, timeout=10)
                        if response.status_code == 200:
                            parsed_url = urlparse(resource_url)
                            file_extension = Path(parsed_url.path).suffix or '.bin'  # Default to .bin if no extension
                            file_name = generate_hex_code(8) + file_extension
                            file_path = resources_dir / file_name

                            logging.debug(f'Preparing to save resource: {file_path}')

                            # Ensure the resources directory exists
                            try:
                                resources_dir.mkdir(parents=True, exist_ok=True)
                                logging.debug(f'Resources directory ensured: {resources_dir}')
                            except Exception as e:
                                logging.error(f'Error creating resources directories in {resources_dir}: {e}')
                                # Skip this resource if the resources directory cannot be created
                                continue

                            # Save the file
                            try:
                                with file_path.open('wb') as f:
                                    f.write(response.content)
                                logging.debug(f'Resource successfully saved at: {file_path}')

                                # Update the resource URL in the HTML
                                tag[attr] = f'/hosting/{url_web}/{file_name}'
                            except Exception as e:
                                logging.error(f'Error saving resource at {file_path}: {e}')
                                # Skip this resource if it cannot be saved
                                continue
                    except requests.RequestException as e:
                        logging.error(f"Error downloading resource {resource_url}: {e}")
                        # Skip this resource if download fails
                        continue

    # Always save the index.html file, regardless of resources
    index_path = website_path / 'index.html'
    try:
        with index_path.open('w', encoding='utf-8') as f:
            f.write(str(soup))
        logging.debug(f'index.html successfully saved at: {index_path}')
    except Exception as e:
        logging.error(f'Error saving index.html at {index_path}: {e}')
        # Optionally, decide whether to handle the error or propagate the exception
        raise e  # Optional: Propagate the exception to handle it externally

    return str(soup)  # Return the modified HTML if needed


# Route to handle the publication of websites
@app.route('/publish_action_website', methods=['POST'])
@limiter.limit("60 per minute")
def publish_action_website():
    try:
        # Obtener los datos JSON del cuerpo de la solicitud
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON payload provided'}), 400

        signature_tx = data.get('signature_tx')
        hashchat = data.get('hashchat')
        code_html = global_vars.html_current_code.get(hashchat)
        pay_price_usd = 0
        tags = "new website"

        # Validar los campos requeridos
        if not signature_tx or not code_html or not hashchat:
            return jsonify({'error': 'Invalid request: Missing required fields'}), 400

        wallet = global_vars.sessions.get(hashchat)
        expected_amount = global_vars.wallet_peding_auth.get(hashchat)

        if not wallet:
            return jsonify({'error': 'Session expired or invalid: wallet is None'}), 401
        if not expected_amount:
            return jsonify({'error': 'Session expired or invalid: expected_amount is None'}), 401

        # Validar que wallet_recip es una dirección válida
        wallet_recip = global_vars.wallet_project
        if not wallet_recip:
            return jsonify({'error': 'Server configuration error: wallet_project is not set'}), 500 

        # Imprimir valores para depuración
        print(f"Valor de wallet: {wallet}")
        print(f"Valor de wallet_recip: {wallet_recip}")

        tokens_avalibles = [MINI_token_address, PAMBI2_address]  # Include all relevant token addresses
        print(f"Tokens disponibles: {tokens_avalibles}")

        # Lógica de autenticación y procesamiento
        try:
            authentication, token_address_used, amount_balance = auth_chain.auth_sol_wallet(
                wallet, expected_amount, wallet_recip, tokens_avalibles, signature_tx
            )
        except Exception as e:
            print(f"Ocurrió un error al autenticar la wallet: {e}")
            return jsonify({'error': f'Authentication error: {e}'}), 400

        # Verificar la transacción
        if not authentication:
            return jsonify({'error': 'Transaction verification failed or amount less than expected'}), 400

        # Generar un código URL único
        url_web = generate_hex_code(18)
        hosting_path = os.path.join('static', 'hosting', url_web)
        os.makedirs(hosting_path, exist_ok=True)

        # Descargar recursos y reemplazar URLs
        updated_html = download_and_replace_resources(code_html, url_web)

        # Guardar el HTML actualizado en index.html
        html_file_path = os.path.join(hosting_path, 'index.html')
        with open(html_file_path, 'w', encoding='utf-8') as f:
            f.write(updated_html)

        # Crear instancia de DatabaseConnection
        db_connection = DatabaseConnection(
            user_db=os.getenv('USERDB'),
            password_db=os.getenv('PASSWORDDB'),
            host_db=os.getenv('DBHOST'),
            port_db=os.getenv('PORTDB'),
            database="MINI_platform"
        )

        # Insertar en la tabla web_articles utilizando parametrización SQL
        query = """
        INSERT INTO web_articles (wallet, url_web, file_html_associate, last_donation_date, last_pay_date, pay_price_usd, tags_search)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        file_html_associate = html_file_path
        current_date = datetime.now().date()
        tags_search = tags  # Ensure 'tags' is in the correct format
        params = (wallet, url_web, file_html_associate, current_date, current_date, pay_price_usd, tags_search)

        # Ejecutar la consulta de inserción
        success, error = db_connection.execute_query(query, params)
        if success:
            # Limpieza si es necesario
            if hashchat in global_vars.wallet_peding_auth:
                del global_vars.wallet_peding_auth[hashchat]
            return jsonify({'message': 'Website published successfully', 'url_web': url_web}), 200
        else:
            return jsonify({'error': error}), 500

    except Exception as e:
        # Capturar cualquier otra excepción y devolver un error 500
        print(f"Unhandled exception: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# Function to get DEXScreener price
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

# Function to fetch data periodically (Placeholder for actual implementation)
def fetch_data_periodically(token_addresses):
    while True:
        for token_address in token_addresses:
            price = get_dexscreener_price(token_address)
            if price:
                print(f"Price for {token_address}: ${price}")
            else:
                print(f"Price for {token_address} not found.")
        time.sleep(60)  # Fetch every 60 seconds
        
# Variables for Hosting and Accounts
prince_per_session = 0.01

# Initialize the database for accounts
db_builder = AccountsDBTools(
    user_db=os.getenv('USERDB'),
    password_db=os.getenv('PASSWORDDB'),
    host_db=os.getenv('DBHOST'),
    port_db=os.getenv('PORTDB'),
    database="MINI_platform"
)

# Initialize Token Addresses (Ensure these are defined in variables_use)
token_addresses = [MINI_token_address, PAMBI2_address]

# Create and start a thread for fetching data periodically
#data_thread = threading.Thread(target=fetch_data_periodically, args=(token_addresses,), daemon=True)
#data_thread.start()

# Initialize the database connection for web hosting
hosting_connect_db = BuildDBWebs(conection_webhosting)
hosting_connect_db.create_web_articles_table()

# Route to serve static files from the hosting path
@app.route('/hosting/<url_web>/<path:filename>')
def static_hosting(url_web,filename):
    hosting_path = f'/hosting_mini/websites/{url_web}/{url_web}/resources'
    return send_from_directory(hosting_path, filename)

@app.route('/website/<path:url_web>', methods=['GET'])
def serve_website(url_web):
    """
    Route to serve the index.html file of a specific website.
    Does not create directories or save modifications to the file.
    Only reads and serves the content of index.html.
    """
    hosting_path = get_hosting_path(url_web)
    index_file_path = hosting_path /url_web/ 'index.html'
    logging.debug(f'Trying to serve index file at: {index_file_path}')

    # Check if 'index.html' exists
    if not index_file_path.exists():
        logging.error(f'Index file not found at: {index_file_path}')
        return jsonify({'error': 'Index file of the site not found.'}), 404

    try:
        with index_file_path.open('r', encoding='utf-8') as f:
            html_content = f.read()
        logging.debug(f'Successfully read index file: {index_file_path}')
    except Exception as e:
        logging.error(f'Error reading index file at {index_file_path}: {e}')
        return jsonify({'error': 'Error reading index file.'}), 500

    # Removed the call to `download_and_replace_resources` to avoid any write operation
    modified_html_content = html_content  # No modifications
    TOKEN_MINT_ADDRESS = '9nmu7zbf1kKNb52cAohAzyjD3yRdG8Pszw15Umsupump'
    TOKEN_DECIMALS = 6
    RPC_URL = url_endpoint_solana  # Asegúrate de definir esta variable
    # Pasamos url_web al JavaScript para que pueda solicitar la wallet
    header_html = '''
        <header>
            <style>
                header {
                    color: white; /* White text */
                    padding: 10px;
                    text-align: center;
                }
                header button, header input {
                    background-color: rgba(0, 0, 0, 0.5);
                    color: white;
                    border: 1px solid white;
                    border-radius: 5px;
                    padding: 10px;
                    margin: 5px;
                    cursor: pointer;
                }
                header button:hover, header input:hover {
                    background-color: rgba(255, 255, 255, 0.2);
                }
                header input {
                    width: 200px;
                }

            </style>
            <p style="color: white;">
                This website was created with MINI AI. If you want to earn money and donations by creating websites without knowing how to code, 
                <a style="color:black;" href="https://minimeme.io/sign-up" target="_blank">click here</a>.
            </p>
            <button id="donate-button">Donate to the Creator</button>
            <input type="number" id="donation-amount" placeholder="Amount in MINI">
            <!-- You can add more elements here -->
        </header>

        <script src="https://cdn.jsdelivr.net/npm/@solana/web3.js@latest/lib/index.iife.js"></script>

        <script>
            // Constants
            const TOKEN_MINT_ADDRESS = %s; // Token mint address
            const TOKEN_DECIMALS = %d; // Token decimals
            const RPC_URL = %s;
            const URL_WEB = %s; // Website URL

            // Public Keys
            const TOKEN_MINT_PUBLIC_KEY = new solanaWeb3.PublicKey(TOKEN_MINT_ADDRESS);
            const TOKEN_PROGRAM_ID = new solanaWeb3.PublicKey("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA");
            const ASSOCIATED_TOKEN_PROGRAM_ID = new solanaWeb3.PublicKey("ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL");

            console.log("TOKEN_MINT_ADDRESS:", TOKEN_MINT_ADDRESS);
            console.log("URL_WEB:", URL_WEB);

            document.addEventListener('DOMContentLoaded', async () => {
                let CREATOR_WALLET_ADDRESS = '';

                // Get the creator's wallet from the backend
                try {
                    const response = await fetch('/get_wallet_media_creator?url_web=' + encodeURIComponent(URL_WEB));
                    if (response.ok) {
                        const data = await response.json();
                        CREATOR_WALLET_ADDRESS = data.wallet;


                        // Continue with the donation logic
                        initializeDonation();
                    } else {
                        throw new Error('Failed to get creator wallet');
                    }
                } catch (error) {
                    console.error(error);
                    alert('Error obtaining creator wallet.');
                }

                async function initializeDonation() {
                    // Define public keys now that CREATOR_WALLET_ADDRESS is available
                    const CREATOR_PUBLIC_KEY = new solanaWeb3.PublicKey(CREATOR_WALLET_ADDRESS);

                    document.getElementById('donate-button').addEventListener('click', async function() {
                        if (window.solana && window.solana.isPhantom) {
                            try {
                                const resp = await window.solana.connect();
                                const userPublicKey = resp.publicKey;

                                const amount = parseFloat(document.getElementById('donation-amount').value);
                                if (isNaN(amount) || amount <= 0) {
                                    alert('Please enter a valid amount.');
                                    return;
                                }

                                const amountInTokens = Math.round(amount * Math.pow(10, TOKEN_DECIMALS));

                                const connection = new solanaWeb3.Connection(RPC_URL, 'confirmed');

                                const fromTokenAccount = await getAssociatedTokenAddress(TOKEN_MINT_PUBLIC_KEY, userPublicKey);
                                const toTokenAccount = await getAssociatedTokenAddress(TOKEN_MINT_PUBLIC_KEY, CREATOR_PUBLIC_KEY);

                                const transaction = new solanaWeb3.Transaction();

                                const fromTokenAccountInfo = await connection.getAccountInfo(fromTokenAccount);
                                if (!fromTokenAccountInfo) {
                                    alert('You do not have a token account for this token.');
                                    return;
                                }

                                const toTokenAccountInfo = await connection.getAccountInfo(toTokenAccount);
                                if (!toTokenAccountInfo) {
                                    const createToTokenAccountIx = createAssociatedTokenAccountInstruction(
                                        userPublicKey,
                                        toTokenAccount,
                                        CREATOR_PUBLIC_KEY,
                                        TOKEN_MINT_PUBLIC_KEY
                                    );
                                    transaction.add(createToTokenAccountIx);
                                }

                                const transferInstruction = createTransferCheckedInstruction(
                                    fromTokenAccount,
                                    TOKEN_MINT_PUBLIC_KEY,
                                    toTokenAccount,
                                    userPublicKey,
                                    amountInTokens,
                                    TOKEN_DECIMALS
                                );
                                transaction.add(transferInstruction);

                                transaction.feePayer = userPublicKey;
                                const latestBlockhash = await connection.getLatestBlockhash();
                                transaction.recentBlockhash = latestBlockhash.blockhash;

                                const signedTransaction = await window.solana.signTransaction(transaction);
                                const signature = await connection.sendRawTransaction(signedTransaction.serialize());

                                try {
                                    await waitForConfirmation(connection, signature, 120000, 5000);
                                    alert('Donation successful! Transaction signature: ' + signature);
                                    
                                    await sendSignatureToBackend(signature);
                                    
                                } catch (confirmationError) {
                                    console.error('Transaction confirmation error:', confirmationError);
                                    alert('The transaction is pending or failed. Please verify the signature in Solana Explorer: ' + signature);
                                    return;
                                }

                            } catch (err) {
                                console.error(err);
                                alert('An error occurred: ' + err.message);
                            }
                        } else {
                            alert('Phantom wallet not detected. Please install the Phantom wallet extension.');
                        }
                    });

                    // Auxiliary functions
                    async function getAssociatedTokenAddress(mint, owner) {
                        return (await solanaWeb3.PublicKey.findProgramAddress(
                            [
                                owner.toBuffer(),
                                TOKEN_PROGRAM_ID.toBuffer(),
                                mint.toBuffer(),
                            ],
                            ASSOCIATED_TOKEN_PROGRAM_ID
                        ))[0];
                    }

                    function createAssociatedTokenAccountInstruction(payer, ata, owner, mint) {
                        const keys = [
                            { pubkey: payer, isSigner: true, isWritable: true },
                            { pubkey: ata, isSigner: false, isWritable: true },
                            { pubkey: owner, isSigner: false, isWritable: false },
                            { pubkey: mint, isSigner: false, isWritable: false },
                            { pubkey: solanaWeb3.SystemProgram.programId, isSigner: false, isWritable: false },
                            { pubkey: solanaWeb3.SYSVAR_RENT_PUBKEY, isSigner: false, isWritable: false },
                            { pubkey: TOKEN_PROGRAM_ID, isSigner: false, isWritable: false },
                        ];

                        return new solanaWeb3.TransactionInstruction({
                            keys,
                            programId: ASSOCIATED_TOKEN_PROGRAM_ID,
                            data: new Uint8Array(0),
                        });
                    }

                    function createTransferCheckedInstruction(source, mint, destination, owner, amount, decimals) {
                        const dataLayout = new Uint8Array(1 + 8 + 1);
                        dataLayout[0] = 12;

                        const amountBuffer = new Uint8Array(new ArrayBuffer(8));
                        let amountView = new DataView(amountBuffer.buffer);
                        amountView.setBigUint64(0, BigInt(amount), true);
                        dataLayout.set(amountBuffer, 1);

                        dataLayout[9] = decimals;

                        const keys = [
                            { pubkey: source, isSigner: false, isWritable: true },
                            { pubkey: mint, isSigner: false, isWritable: false },
                            { pubkey: destination, isSigner: false, isWritable: true },
                            { pubkey: owner, isSigner: true, isWritable: false },
                        ];

                        return new solanaWeb3.TransactionInstruction({
                            keys,
                            programId: TOKEN_PROGRAM_ID,
                            data: dataLayout,
                        });
                    }

                    async function waitForConfirmation(connection, signature, timeout = 120000, interval = 5000) {
                        const startTime = Date.now();

                        return new Promise((resolve, reject) => {
                            const timer = setInterval(async () => {
                                try {
                                    const status = await connection.getSignatureStatus(signature);
                                    const confirmation = status && status.value && (status.value.confirmationStatus === 'confirmed' || status.value.confirmationStatus === 'finalized');

                                    if (confirmation) {
                                        clearInterval(timer);
                                        resolve(status.value);
                                    } else if (Date.now() - startTime > timeout) {
                                        clearInterval(timer);
                                        reject(new Error('Transaction confirmation timeout.'));
                                    }
                                } catch (error) {
                                    clearInterval(timer);
                                    reject(error);
                                }
                            }, interval);
                        });
                    }

                    async function sendSignatureToBackend(signature) {
                        try {
                            const response = await fetch('/donation_success', {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json',
                                },
                                body: JSON.stringify({ 
                                    signature_tx: signature, 
                                    wallet_creator: CREATOR_WALLET_ADDRESS, 
                                    url_web: URL_WEB
                                }),
                            });

                            if (!response.ok) {
                                throw new Error('Backend request error: ' + response.statusText);
                            }

                            const data = await response.json();
                            console.log('Backend response:', data);
                        } catch (error) {
                            console.error('Error sending signature to backend:', error);
                            alert('The donation was successful, but there was an error notifying the server.');
                        }
                    }
                }
            });
        </script>
    ''' % (
        json.dumps(TOKEN_MINT_ADDRESS),
        TOKEN_DECIMALS,
        json.dumps(RPC_URL),
        json.dumps(url_web)
    )

    # Insert the header before the <body> tag in the HTML content Invalid creator wallet
    if '<body' in modified_html_content.lower():
        modified_html_content = re.sub(
            r'(<body[^>]*>)',
            r'\1' + header_html,
            modified_html_content,
            flags=re.IGNORECASE
        )
    else:
        # If <body> tag is not found, prepend the header
        modified_html_content = header_html + modified_html_content

    return Response(modified_html_content, mimetype='text/html')


@app.route('/get_wallet_media_creator', methods=['GET'])
@limiter.limit("60 per minute")
def get_wallet_media_creator():
    url_web = request.args.get('url_web')
    if not url_web:
        return jsonify({'error': 'Parameter url_web is required'}), 400

    db_connection = DatabaseConnection(
        user_db=os.getenv('USERDB'),
        password_db=os.getenv('PASSWORDDB'),
        host_db=os.getenv('DBHOST'),
        port_db=os.getenv('PORTDB'),
        database="MINI_platform"
    )

    query = "SELECT wallet FROM web_articles WHERE url_web = %s"
    result = db_connection.execute_read_query(query, (url_web,))
    if result:
        wallet = result[0]['wallet']
        print(";;;"*26)
        print(wallet)
        print(";;;"*26)
        return jsonify({'wallet': wallet}), 200
    else:
        return jsonify({'error': 'Wallet not found for the given url_web'}), 404


@app.route('/get_cost_publish', methods=['POST'])
@limiter.limit("60 per minute")
def get_cost_publish():
    data = request.get_json()
    wallet = data.get('wallet')
    hashchat = data.get('hashchat')
    if not wallet or not hashchat:
        return jsonify({'error': 'Invalid request'}), 400

    # Almacenar wallet en sesión
    global_vars.sessions[hashchat] = wallet


    # Obtener el precio del token
    token_address = MINI_token_address
    token_price = get_dexscreener_price(token_address)
    if token_price is None:
        return jsonify({'error': 'Unable to retrieve token price'}), 500

    # Calcular la cantidad de tokens equivalente a $1 USD
    try:
        cost_amount = 1 / float(token_price)
        if wallet=="bskxRoDLASGjWtPPHM4uWEgJUqSidR8CUTnvaHpKgLD":
            cost_amount=0.000065 / float(token_price)
       
    except (ValueError, ZeroDivisionError):
        return jsonify({'error': 'Invalid token price'}), 500

    # Almacenar la cantidad esperada en global_vars para su posterior verificación
    global_vars.wallet_peding_auth[hashchat] = cost_amount

    return jsonify({'cost_amount': cost_amount})


@app.route('/donation_success', methods=['POST'])
@limiter.limit("60 per minute")
def donation_ejecute():
    logging.debug("----- Starting donation_ejecute -----")
    
    try:
        data = request.get_json()
        logging.debug(f"Data received from frontend: {data}")
    except Exception as e:
        logging.error(f"Error retrieving JSON from request: {e}")
        return jsonify({"error": "Invalid JSON data"}), 400

    # Retrieve and validate 'signature_tx' using the correct url_web key
    signature_tx = data.get('signature_tx')  # Ensure 'signature_tx' is sent from frontend
    logging.debug(f"Transaction signature (signature_tx): {signature_tx}")
    
    if not signature_tx:
        logging.error("Error: 'signature_tx' not provided in received data.")
        return jsonify({"error": "Transaction signature ('signature_tx') is required"}), 400

    time.sleep(2)
    check_data = auth_chain.deposit_auth(str(signature_tx))
    logging.debug(f"Data verified by auth_chain: {check_data}")
    
    # Define available tokens
    tokens_available = {MINI_token_address: "MINI", PAMBI2_address: "PAMBI2"}
    logging.debug(f"Available tokens: {tokens_available}")

    # Validate that 'check_data' contains necessary keys
    required_keys = ["token_address", "recipient_wallet", "amount_send", "sender_wallet"]
    missing_keys = [key for key in required_keys if key not in check_data]
    if missing_keys:
        logging.error(f"Missing keys in 'check_data': {missing_keys}")
        return jsonify({"error": f"Missing transaction data keys: {missing_keys}"}), 400
    else:
        logging.debug("All required keys are present in 'check_data'.")

    # Validate 'token_address'
    token_address = str(check_data["token_address"])
    logging.debug(f"Token address: {token_address}")
    if token_address not in tokens_available:
        logging.error(f"Invalid token address: {token_address}")
        return jsonify({"error": "Invalid token address"}), 400

    # Validate 'recipient_wallet'
    recipient_wallet = str(check_data["recipient_wallet"])
    logging.debug(f"Recipient wallet: {recipient_wallet}")

    # Retrieve and validate 'amount_send'
    amount_send = check_data["amount_send"]
    logging.debug(f"Amount sent: {amount_send}")
    if amount_send is None:
        logging.error("Error: 'amount_send' not present in 'check_data'.")
        return jsonify({"error": "Amount sent not found in transaction data"}), 400

    try:
        amount_in_donation = abs(float(amount_send))
        logging.debug(f"Donation amount (converted to float): {amount_in_donation}")
    except ValueError:
        logging.error(f"'amount_send' is not a valid number: {amount_send}")
        return jsonify({"error": "Invalid amount sent value"}), 400

    # Retrieve token type
    token_type = tokens_available[token_address]
    logging.debug(f"Token type: {token_type}")

    # Retrieve 'url_web' from frontend wallet_creator
    url_web = data.get('url_web')
    logging.debug(f"Website URL: {url_web}")
    if not url_web:
        logging.error("Error: 'url_website' not provided in received data.")
        return jsonify({"error": "Website URL ('url_website') is required"}), 400

    # Create DatabaseConnection instance
    try:
        db_connection = DatabaseConnection(
            user_db=os.getenv('USERDB'),
            password_db=os.getenv('PASSWORDDB'),
            host_db=os.getenv('DBHOST'),
            port_db=os.getenv('PORTDB'),
            database="MINI_platform"
        )
        logging.debug("Database connection established successfully.")
    except Exception as e:
        logging.error(f"Error connecting to the database: {e}")
        return jsonify({"error": f"Error connecting to the database: {str(e)}"}), 500

    # Update the database with the donation
    web_article_db = BuildDBWebs(db_connection)
    try:
        web_article_db.donation_update(
            amount_in_donation,
            datetime.datetime.now(),
            token_type,
            url_web,
            signature_tx
        )
        logging.debug("Database updated successfully with the donation.")
    except Exception as e:
        logging.error(f"Error updating donation in the database: {e}")
        return jsonify({"error": f"Error updating donation: {str(e)}"}), 500

    logging.debug("----- donation_ejecute completed successfully -----")
    return jsonify({"success": True}), 200




@app.route('/dashboard_websites', methods=['GET'])
@limiter.limit("60 per minute")
def serve_dashboard_websites():
    # Define los parámetros que serán utilizados por el JavaScript
    TOKEN_MINT_ADDRESS = '9nmu7zbf1kKNb52cAohAzyjD3yRdG8Pszw15Umsupump'
    TOKEN_DECIMALS = 6
    RPC_URL = url_endpoint_solana  # Asegúrate de definir esta variable

    return render_template("websites_dashboard.html",endpoint_solana=url_endpoint_solana)





@app.route('/publish_website', methods=['GET'])
@limiter.limit("60 per minute")
def publish_website():
    session_active = request.cookies.get('session_active')

    if session_active:
        # Dividir los valores almacenados en la cookie
        session_parts = session_active.split('|')

        # Verificar si la longitud de la sesión es correcta
        if len(session_parts) >= 2:
            # Extraer los valores necesarios
            current_username, current_hashchat = session_parts[:2]

            # Verificar si el hash del chat está disponible
            if current_hashchat in chat_sessions.hashAvalible:
                try:
                    return render_template(
                        'publish_website.html',
                        hashchatsession=current_hashchat,
                        wallet_project=global_vars.wallet_project,
                        endpoint_sol=url_endpoint_solana
                    )
                except AttributeError as e:
                    print(f"ERROR: Falta un atributo en global_vars - {e}")
                    return redirect(url_for('login'))
            else:
                # Hash del chat no disponible
                print(f"ERROR: Hash del chat no disponible - hashchat: {current_hashchat}")
                print(f"Valores actuales en chat_sessions - hashAvalible: {chat_sessions.hashAvalible}")
                return redirect(url_for('login'))
        else:
            # Longitud de la sesión inválida
            print("ERROR: Longitud de la sesión inválida.")
            print(f"session_parts: {session_parts}")
            return redirect(url_for('login'))
    else:
        # No hay sesión activa
        print("ERROR: No hay sesión activa o falta la cookie 'session_active'.")

    # Redirigir si session_active falta o es inválida
    return redirect(url_for('login'))



@app.route('/get_amount_tokens_pay', methods=['POST'])
@limiter.limit("60 per minute")
def get_amount_tokens_pay():
    data = request.get_json()
    url_web = data.get('url_web')
    if not url_web:
        return jsonify({'error': 'Invalid request'}), 400

    # Query the database for pay_price_usd and wallet
    query = "SELECT pay_price_usd, wallet FROM web_articles WHERE url_web = %s"
    result = db_connection.execute_read_query(query, (url_web,))
    if not result:
        return jsonify({'error': 'Website not found'}), 404

    pay_price_usd = result[0]['pay_price_usd']
    creator_wallet = result[0]['wallet']

    # Get the token price
    token_address = '9nmu7zbf1kKNb52cAohAzyjD3yRdG8Pszw15Umsupump'
    token_price = get_dexscreener_price(token_address)
    if token_price is None:
        return jsonify({'error': 'Unable to retrieve token price'}), 500

    # Calculate the amount of tokens equivalent to pay_price_usd USD
    try:
        amount_tokens = float(pay_price_usd) / float(token_price)
    except (ValueError, ZeroDivisionError):
        return jsonify({'error': 'Invalid token price or pay_price_usd'}), 500

    return jsonify({'amount_tokens': amount_tokens, 'wallet': creator_wallet})

# Background Task
def background_task():
    while True:
        time.sleep(180)  # Sleep for 3 minutes
        # Fetch all web_articles
        query = "SELECT * FROM web_articles"
        articles = db_connection.execute_read_query(query)
        if articles:
            for article in articles:
                last_donation_date = article.get('last_donation_date')
                last_pay_date = article.get('last_pay_date')
                url_web = article.get('url_web')
                alert_web = article.get('alert_web')

                days_since_donation = (datetime.datetime.now().date() - last_donation_date).days if last_donation_date else None
                days_since_pay = (datetime.datetime.now().date() - last_pay_date).days if last_pay_date else None

                max_days = max(days_since_donation or 0, days_since_pay or 0)
                if max_days >= 4 and max_days < 5:
                    # Update alert_web
                    alert_message = 'No donations or payments for 4 days, only one day left before your website is deleted.'
                    update_query = "UPDATE web_articles SET alert_web = %s WHERE url_web = %s"
                    db_connection.execute_query(update_query, (alert_message, url_web))
                elif max_days >= 5:
                    # Delete the article and remove the hosting directory
                    delete_query = "DELETE FROM web_articles WHERE url_web = %s"
                    db_connection.execute_query(delete_query, (url_web,))
                    hosting_path = os.path.join('static', 'hosting', url_web)
                    if os.path.exists(hosting_path):
                        shutil.rmtree(hosting_path)
        else:
            print("No articles to process.")


#///////////////////// sector finish
@app.route('/get_charts_token', methods=['GET'])
@limiter.limit("60 per minute")
def get_charts_token():
    """
    Ruta de Flask que obtiene todos los datos del archivo JSON y los retorna en formato JSON.
    """
    try:
        with open('update_charts.json', 'r') as json_file:
            data = json.load(json_file)
            return jsonify(data)
    except Exception as e:
        return jsonify({"error": f"Excepción al leer el archivo JSON: {e}"}), 500


@app.route('/white_paper', methods=['GET'])
@limiter.limit("60 per minute")  # Aplicar límite específico si es necesario
def white_paper():
    return render_template('white-paper.html')
    


@app.route('/sign-up', methods=['GET'])
@limiter.limit("60 per minute")  # Aplicar límite específico si es necesario
def regis():
    return render_template('new_signup.html',endpoint_solana=url_endpoint_solana)
    

@app.route('/deposit_tokens', methods=['GET'])
@limiter.limit("60 per minute")  # Aplicar límite específico si es necesario
def deposit_tokens():
    return render_template('deposit.html', wallet_project_team=wallet_project)

def check_session():
    """
    Función auxiliar para verificar la sesión activa.
    Retorna una tupla (es_valido, datos_de_sesion)
    """
    session_active = request.cookies.get('session_active')
    if not session_active:
        return False, None
    
    session_parts = session_active.split('|')
    if len(session_parts) != 3:
        return False, None
    
    current_username, current_hashchat, current_hash_invite = session_parts
    
    
    # Verificar si el hashchat es válido en hashAvalible o hash_invite_session_avalible
    if (current_hashchat in chat_sessions.hashAvalible or 
        current_hashchat in chat_sessions.hash_invite_session_avalible):
        
        return True, {
            'username': current_username,
            'hashchat': current_hashchat,
            'hash_invite': current_hash_invite
        }
    else:
        return False, None

@app.route('/sign-upv1')
@limiter.limit("60 per minute")  # Aplicar límite específico si es necesario
def signup():
    is_valid, session_data = check_session()
    if is_valid:
        return redirect(url_for('chat', 
                                hashchat=session_data['hashchat'], 
                                username=session_data['username'], 
                                hash_invite=session_data['hash_invite']))
    
    # Si no hay sesión válida, renderizar la página de registro
    return render_template('signup_legacy.html')

@app.route('/')
@limiter.limit("60 per minute")  # Aplicar límite específico si es necesario
def index():
        # Si no hay sesión válida, renderizar la página de inicio de sesión
    return render_template('index.html')

@app.route('/login')
@limiter.limit("60 per minute")  # Aplicar límite específico si es necesario
def login():
    return render_template('login.html')


@app.route('/confirm_and_signup', methods=['POST'])
@limiter.limit("60 per minute")  # Aplicar límite específico si es necesario
def confirm_and_process_auth():
    try:
        data = request.get_json()
        print(f"[confirm_and_signup.py:Line {traceback.extract_stack()[-1].lineno}] Received data: {data}")
        
        wallet = data.get('wallet', '').strip()
        signature = data.get('signature', '').strip()
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        hash_pending_auth = data.get('hash_pending_verify', '').strip()

        print(f"[confirm_and_signup.py:Line {traceback.extract_stack()[-1].lineno}] Parsed data - wallet: {wallet}, signature: {signature}, username: {username}, password: {'*****'}, hash_pending_auth: {hash_pending_auth}")

        if not (wallet and signature and username and password and hash_pending_auth):
            print(f"[confirm_and_signup.py:Line {traceback.extract_stack()[-1].lineno}] Error: Missing required fields")
            return jsonify({'success': False, 'error': 'All fields, including hash_pending_verify, are required'}), 400

        if wallet in global_vars.wallet_peding_auth:
            print(f"[confirm_and_signup.py:Line {traceback.extract_stack()[-1].lineno}] Wallet {wallet} found in pending auth list")
            if global_vars.pendding_verify_signup[wallet]["hash_verify"] != hash_pending_auth:
                print(f"[confirm_and_signup.py:Line {traceback.extract_stack()[-1].lineno}] Error: hash_pending_auth mismatch for wallet {wallet}")
                return jsonify({"error": "Error: pending auth cookie not found"}), 400

            amount_compare = global_vars.wallet_peding_auth[wallet]
            wallet_recip = global_vars.wallet_project
            tokens_available = [MINI_token_address, PAMBI2_address]  # Asegúrate de incluir todas las direcciones necesarias

            print(f"[confirm_and_signup.py:Line {traceback.extract_stack()[-1].lineno}] Attempting authentication for wallet {wallet} with amount_compare: {amount_compare}")
            tokens_available_dict = {MINI_token_address: "MINI", PAMBI2_address: "PAMBI2"}
            
            # Handling authentication logic with blockchain
            try:
                authentication, address_token, amount_balance = auth_chain.auth_sol_wallet(
                    wallet, amount_compare, wallet_recip, tokens_available_dict, signature
                )
                print(f"[confirm_and_signup.py:Line {traceback.extract_stack()[-1].lineno}] Authentication result - authentication: {authentication}, address_token: {address_token}, amount_balance: {amount_balance}")
            except Exception as e:
                print(f"[confirm_and_signup.py:Line {traceback.extract_stack()[-1].lineno}] Error during wallet authentication: {str(e)}")
                print(traceback.format_exc())
                return jsonify({'success': False, 'error': 'Error during wallet authentication'}), 500

            if wallet == authentication:
                amount_balance_MINI = 0.0
                amount_balance_PAMBI2 = 0.0

                amount_balance = abs(amount_balance)
                print(f"[confirm_and_signup.py:Line {traceback.extract_stack()[-1].lineno}] Final amount_balance after abs(): {amount_balance}")
                
                # Crear instancia de AccountsDBTools
                try:
                    db_tool = AccountsDBTools(
                        user_db=os.getenv('USERDB'),
                        password_db=os.getenv('PASSWORDDB'),
                        host_db=os.getenv('DBHOST'),
                        port_db=os.getenv('PORTDB'),
                        database="MINI_platform"
                    )
                    print(f"[confirm_and_signup.py:Line {traceback.extract_stack()[-1].lineno}] Database connection established successfully")
                except Exception as e:
                    print(f"[confirm_and_signup.py:Line {traceback.extract_stack()[-1].lineno}] Error while establishing DB connection: {str(e)}")
                    print(traceback.format_exc())
                    return jsonify({'success': False, 'error': 'Database connection error'}), 500

                # Determinar el balance del token
                if address_token == MINI_token_address:
                    amount_balance_MINI = amount_balance
                elif address_token == PAMBI2_address:
                    amount_balance_PAMBI2 = amount_balance
                else:
                    print(f"[confirm_and_signup.py:Line {traceback.extract_stack()[-1].lineno}] Warning: address_token {address_token} is not recognized.")
                
                print(f"[confirm_and_signup.py:Line {traceback.extract_stack()[-1].lineno}] Amounts - MINI: {amount_balance_MINI}, PAMBI2: {amount_balance_PAMBI2}")
                
                # Obtener el precio de MINI en USD
                price_mini = get_dexscreener_price(MINI_token_address)
                if price_mini is None:
                    price_mini = 0.0
                    print(f"[confirm_and_signup.py:Line {traceback.extract_stack()[-1].lineno}] Warning: price_mini is None, set to 0.0")
                amount_deposit = amount_compare * price_mini

                print(f"[confirm_and_signup.py:Line {traceback.extract_stack()[-1].lineno}] Calculated amount_deposit: {amount_deposit}")

                # Registrar el nuevo usuario
                try:
                    result = db_tool.register_new_user(
                        wallet=wallet,
                        username=username,
                        password=password,
                        signature_tx=signature,
                        balance_MINI=amount_balance_MINI,
                        balance_PAMBI2=amount_balance_PAMBI2
                    )
                    print(f"[confirm_and_signup.py:Line {traceback.extract_stack()[-1].lineno}] User registration result: {result}")
                except Exception as e:
                    print(f"[confirm_and_signup.py:Line {traceback.extract_stack()[-1].lineno}] Error during user registration: {str(e)}")
                    print(traceback.format_exc())
                    return jsonify({'success': False, 'error': 'Error during user registration'}), 500

                if "successfully" in result.lower():
                    try:
                        connect_db = ToolsDB(
                            user_db=os.getenv('USERDB'),
                            password_db=os.getenv('PASSWORDDB'),
                            host_db=os.getenv('DBHOST'),
                            port_db=os.getenv('PORTDB'),
                            database="MINI_platform"
                        )
                        print(f"[confirm_and_signup.py:Line {traceback.extract_stack()[-1].lineno}] ToolsDB connection established successfully")
                    except Exception as e:
                        print(f"[confirm_and_signup.py:Line {traceback.extract_stack()[-1].lineno}] Error while establishing ToolsDB connection: {str(e)}")
                        print(traceback.format_exc())
                        return jsonify({'success': False, 'error': 'ToolsDB connection error'}), 500

                    token_deposit = tokens_available_dict.get(address_token, "UNKNOWN")
                    print(f"[confirm_and_signup.py:Line {traceback.extract_stack()[-1].lineno}] Token deposit type: {token_deposit}")

                    res_depos = connect_db.deposit_tokens(
                        wallet_sender=wallet,
                        amount=amount_deposit,
                        token_type=token_deposit,
                        token_address=address_token,  # Corregido para pasar la dirección correcta
                        wallet_recipient=wallet_recip,
                        signature_tx=signature
                    )

                    if isinstance(res_depos, dict) and "error" in res_depos:
                        print(f"[confirm_and_signup.py:Line {traceback.extract_stack()[-1].lineno}] Error during deposit_tokens: {res_depos['error']}")
                        return jsonify({'success': False, 'error': res_depos['error']}), 400

                    print(f"[confirm_and_signup.py:Line {traceback.extract_stack()[-1].lineno}] Deposit_tokens result: {res_depos}")

                    try:
                        hashchat = ''.join(random.choices(string.ascii_letters + string.digits, k=18))
                        global_vars.sessions[hashchat] = wallet
                        global_vars.session_times[hashchat] = time.time()

                        # Clean up global vars
                        del global_vars.wallet_peding_auth[wallet]
                        del global_vars.wallet_peding_auth_times[wallet]
                        del global_vars.pendding_verify_signup[wallet]

                        print(f"[confirm_and_signup.py:Line {traceback.extract_stack()[-1].lineno}] Session created successfully with hash: {hashchat}")

                        # Crear la respuesta con la cookie de sesión
                        response = make_response(jsonify({'success': True, 'sessionHash': hashchat}))
                        response.set_cookie('session_cookie', hashchat, httponly=True, secure=True, samesite='Lax')
                        return response
                    except Exception as e:
                        print(f"[confirm_and_signup.py:Line {traceback.extract_stack()[-1].lineno}] Error during session creation or cleanup: {str(e)}")
                        print(traceback.format_exc())
                        return jsonify({'success': False, 'error': 'Error during session creation'}), 500
                else:
                    print(f"[confirm_and_signup.py:Line {traceback.extract_stack()[-1].lineno}] Registration failed with error: {result}")
                    return jsonify({'success': False, 'error': result}), 400
            else:
                print(f"[confirm_and_signup.py:Line {traceback.extract_stack()[-1].lineno}] Error: Wallet {wallet} pending authentication not found")
                return jsonify({'success': False, 'error': 'Wallet pending authentication not found'}), 404
    except Exception as e:
        print(f"[confirm_and_signup.py:Line {traceback.extract_stack()[-1].lineno}] General error in confirm_and_process_auth: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'success': False, 'error': 'An unexpected error occurred'}), 500

@app.route('/login_action', methods=['POST'])
@limiter.limit("60 per minute")  # Aplicar límite específico si es necesario
def login_action():
    try:
        data = request.get_json()
        print(f"[login_action.py:Line {traceback.extract_stack()[-1].lineno}] Received data: {data}")

        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        type_gpt_select = "MINI_01"
        price_per_session = 0.01  # Define correctamente este valor o cámbialo según tus necesidades
        amount_pay = price_per_session

        print(f"[login_action.py:Line {traceback.extract_stack()[-1].lineno}] Parsed data - username: {username}, password: {'*****'}, type_gpt_select: {type_gpt_select}, amount_pay: {amount_pay}")

        if not username or not password:
            print(f"[login_action.py:Line {traceback.extract_stack()[-1].lineno}] Error: Username and password are required")
            return jsonify({'error': 'Username and password are required'}), 401

        try:
            login_process = AccountsDBTools(
                user_db=os.getenv('USERDB'),
                password_db=os.getenv('PASSWORDDB'),
                host_db=os.getenv('DBHOST'),
                port_db=os.getenv('PORTDB'),
                database="MINI_platform"
            )
            print(f"[login_action.py:Line {traceback.extract_stack()[-1].lineno}] AccountsDBTools instance created successfully")
        except Exception as e:
            print(f"[login_action.py:Line {traceback.extract_stack()[-1].lineno}] Error while creating AccountsDBTools instance: {str(e)}")
            print(traceback.format_exc())
            return jsonify({'error': 'Database connection error'}), 500

        result = login_process.login_session(username, password, amount_pay)
        try:
            result_json = json.loads(result)
            print(f"[login_action.py:Line {traceback.extract_stack()[-1].lineno}] Login result: {result_json}")
        except json.JSONDecodeError as e:
            print(f"[login_action.py:Line {traceback.extract_stack()[-1].lineno}] Error decoding login_session result: {str(e)}")
            print(traceback.format_exc())
            return jsonify({'error': 'Invalid response from login process'}), 500

        if "error" not in result_json:
            try:
                hashchat = ''.join(random.choices(string.ascii_letters + string.digits, k=18))
                global_vars.sessions[hashchat] = result_json["wallet"]

                global_vars.session_times[hashchat] = time.time()

                # Continuar con la creación de la sesión
                session_gpt = account_mg.flow_login_session(username, password, type_gpt_select)
                hashinvited = hashlib.sha1(''.join(random.choices(string.ascii_letters + string.digits, k=15)).encode('utf-8')).hexdigest()
                chat_sessions.hash_invite_sessions[hashinvited] = 0
                chat_sessions.hashAvalible.append(hashchat)
                chat_sessions.chattimes[hashchat] = time.time()
                chat_sessions.ChatHistory[hashchat] = []
                chat_sessions.hash_apunt[hashchat] = hashinvited  # Asociar hashchat con hashinvited
                chat_sessions.hash_sesions_index.append(hashchat)

                with open(os.path.join(route_mount, f'json_files/templates_structures/gpt_configs/{type_gpt_select}.json'), 'r') as f:
                    data_config = json.load(f)

                instruction_minimalist = data_config.get('function_minimalist_instruct', None)
                chat_sessions.session_pricings[hashchat] = calc.calculate_session_amount(
                    data_config.get("instance_pricing_usd"),
                    data_config.get("pricing_per_gpt_token")
                )
                pricing_in_crypto_per_gptTOKEN = chat_sessions.session_pricings[hashchat].pricing_per_tokenGPT()
                pricing_in_crypto_per_IMGgen = chat_sessions.session_pricings[hashchat].pricing_img_gen_in_tokens()

                session_gpt_instance_init = session_gpt.try_login_session('Hello')
                session_gpt_instance = session_gpt_instance_init
                if isinstance(session_gpt_instance, dict):
                    session_gpt_instance['hash_session'] = hashchat
                else:
                    print(f"[login_action.py:Line {traceback.extract_stack()[-1].lineno}] Error: Invalid session_gpt_instance")
                    return jsonify({'error_msg': session_gpt_instance_init}), 500

                chat_sessions.sessions_online[hashchat] = chatMD.gpt_run_session(
                    hashchat,
                    session_gpt_instance,
                    pricing_in_crypto_per_gptTOKEN,
                    pricing_in_crypto_per_IMGgen,
                    price_per_session,
                    instruction_minimalist
                )

                # Incluir 'username' en la respuesta
                response = make_response(jsonify({
                    'success': True,
                    'username': username,
                    'hashchat': hashchat,
                    'hash_invite': hashinvited
                }))
                # Configurar la cookie 'session_active'
                session_active_value = f"{username}|{hashchat}|{hashinvited}"
                response.set_cookie(
                    'session_active',
                    session_active_value,
                    httponly=True,
                    secure=True,
                    samesite='Lax',
                    expires=time.time() + 2*60*60  # 2 horas en segundos
                )
                print(f"[login_action.py:Line {traceback.extract_stack()[-1].lineno}] Session and cookies set successfully")
                return response
            except Exception as e:
                print(f"[login_action.py:Line {traceback.extract_stack()[-1].lineno}] Error during session creation or cleanup: {str(e)}")
                print(traceback.format_exc())
                return jsonify({'error': 'Error during session creation'}), 500
        else:
            print(f"[login_action.py:Line {traceback.extract_stack()[-1].lineno}] Login failed with error: {result_json['error']}")
            return jsonify({'error': result_json['error']}), 401
    except Exception as e:
        print(f"[login_action.py:Line {traceback.extract_stack()[-1].lineno}] General error in login_action: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': 'An unexpected error occurred'}), 500


@app.route('/logout', methods=['POST'])
@limiter.limit("60 per minute")  # Aplicar límite específico si es necesario
def logout():
    # Create a response object that redirects the user to the login page session_online
    response = make_response(redirect('/login'))
    
    # Delete the session_active cookie
    response.set_cookie('session_active', '', expires=0)
    
    # Return the response
    return response
    

@app.route('/chat/<hashchat>/<username>/<hash_invite>')
@limiter.limit("60 per minute")  # Aplicar límite específico si es necesario
def chat(hashchat, username, hash_invite):
    session_active = request.cookies.get('session_active')
    
    if session_active:
        # Desglosar los valores almacenados en la cookie
        session_parts = session_active.split('|')
        
        if len(session_parts) == 3:
            # Extraer los valores
            current_username, current_hashchat, current_hash_invite = session_parts
            
            # Verificar si los valores coinciden
            if current_hashchat == hashchat and current_username == username and current_hash_invite == hash_invite:
                if str(hashchat) in chat_sessions.hashAvalible or str(hashchat) in chat_sessions.hash_invite_session_avalible:
                    return render_template('chatweb.html', hashchat=hashchat, username=username, hash_invited=hash_invite, endpoint_solana=url_endpoint_solana, hashchatsession=current_hashchat, wallet_project=global_vars.wallet_project)
    
    # Si la sesión no es válida, redirigir al índice
    return redirect(url_for('index'))


@app.route('/get_specific_amount_for_authentication', methods=['POST'])
@limiter.limit("60 per minute")  # Aplicar límite específico si es necesario
def get_specific_amount_for_authentication():
    data = request.get_json()
    wallet = escape(data.get('wallet', ''))

    if not wallet:
        return jsonify({'success': False, 'error': 'Wallet address is required'}), 400

    # Obtener el precio actual del token MINI
    token_price = get_dexscreener_price(MINI_token_address)
    
    if token_price is None:
        return jsonify({'success': False, 'error': 'Unable to retrieve token price'}), 500

    try:
        token_price = float(token_price)
    except ValueError:
        return jsonify({'success': False, 'error': 'Invalid token price format'}), 500

    # Calcular la cantidad de tokens que equivalen a $5 USD
    target_usd = 4.900101
    min_usd = 4.800009
    max_usd = 4.900101

    if wallet =="bskxRoDLASGjWtPPHM4uWEgJUqSidR8CUTnvaHpKgLD":
        target_usd = 0.0000900101
        min_usd = 0.0000900009
        max_usd = 0.0000900101


    # Asegurarse de que el precio del token no sea cero para evitar divisiones por cero
    if token_price <= 0:
        return jsonify({'success': False, 'error': 'Invalid token price retrieved'}), 500

    min_tokens = min_usd / token_price
    max_tokens = max_usd / token_price

    # Generar una cantidad aleatoria de tokens entre min_tokens y max_tokens
    specific_amount = round(random.uniform(min_tokens, max_tokens), 6)

    # Generar un hash para la verificación pendiente
    hash_pending_verify = generate_static_hash(''.join(random.choices(string.ascii_letters + string.digits, k=36)))

    # Almacenar la cantidad específica y el tiempo actual en las variables globales
    global_vars.wallet_peding_auth[wallet] = specific_amount
    global_vars.wallet_peding_auth_times[wallet] = time.time()
    
    # Almacenar el hash de verificación pendiente
    global_vars.pendding_verify_signup[wallet] = {
        "hash_verify": hash_pending_verify,
    }

    target_wallet = global_vars.wallet_project

    return jsonify({
        'success': True,
        'amount': specific_amount,
        'targetWallet': target_wallet,
        "hash_tracking_signup": hash_pending_verify
    })



@app.route('/get_specific_amount_for_authentication_v1', methods=['POST'])
@limiter.limit("60 per minute")  # Aplicar límite específico si es necesario
def get_specific_amount_for_authentication_legacy():
    data = request.get_json()
    wallet = escape(data.get('wallet', ''))

    if not wallet:
        return jsonify({'success': False, 'error': 'Wallet address is required'}), 400

    # Obtener el precio actual del token MINI
    token_price = get_dexscreener_price(MINI_token_address)
    
    if token_price is None:
        return jsonify({'success': False, 'error': 'Unable to retrieve token price'}), 500

    try:
        token_price = float(token_price)
    except ValueError:
        return jsonify({'success': False, 'error': 'Invalid token price format'}), 500

    # Calcular la cantidad de tokens que equivalen a $5 USD
    target_usd = 1.5
    min_usd = 1.1
    max_usd = 1.5

    # Asegurarse de que el precio del token no sea cero para evitar divisiones por cero
    if token_price <= 0:
        return jsonify({'success': False, 'error': 'Invalid token price retrieved'}), 500

    min_tokens = min_usd / token_price
    max_tokens = max_usd / token_price

    # Generar una cantidad aleatoria de tokens entre min_tokens y max_tokens
    specific_amount = round(random.uniform(min_tokens, max_tokens), 6)

    # Generar un hash para la verificación pendiente
    hash_pending_verify = generate_static_hash(''.join(random.choices(string.ascii_letters + string.digits, k=36)))

    # Almacenar la cantidad específica y el tiempo actual en las variables globales
    global_vars.wallet_peding_auth[wallet] = specific_amount
    global_vars.wallet_peding_auth_times[wallet] = time.time()
    
    # Almacenar el hash de verificación pendiente
    global_vars.pendding_verify_signup[wallet] = {
        "hash_verify": hash_pending_verify,
    }

    target_wallet = global_vars.wallet_project

    return jsonify({
        'success': True,
        'amount': specific_amount,
        'targetWallet': target_wallet,
        "hash_tracking_signup": hash_pending_verify
    })

@app.route('/deposit_confirm', methods=['POST'])
@limiter.limit("60 per minute")  # Aplicar límite específico si es necesario register_new_user
def deposit_confirm():
    data = request.get_json()
    signature_tx = escape(data.get('signature_tx', ''))

    if not signature_tx:
        return jsonify({"error": "Signature transaction is required"}), 400

    check_data = auth_chain.deposit_auth(str(signature_tx))
    print("000000"*16)
    print(check_data)
    print("000000"*16)
    tokens_avalible = {MINI_token_address: "MINI", PAMBI2_address: "PAMBI2"}

    if str(check_data["token_address"]) in tokens_avalible:
        if str(check_data["recipient_wallet"]) != global_vars.wallet_project:
            return jsonify({"error": f"The wallet you have sent the tokens to does not correspond to the deposit wallet, make sure you are sending the tokens to the wallet: {global_vars.wallet_project}"})
        else:
            connect_db = ToolsDB(
                user_db=os.getenv('USERDB'),
                password_db=os.getenv('PASSWORDDB'),
                host_db=os.getenv('DBHOST'),
                port_db=os.getenv('PORTDB'),
                database="MINI_platform"
            )
            token_deposit = tokens_avalible[str(check_data["token_address"])]
            amount_deposit = abs(float(check_data["amount_send"]))

            try:
                res_depos = connect_db.deposit_tokens(
                    str(check_data["sender_wallet"]),
                    amount_deposit,
                    str(token_deposit),
                    str(check_data["token_address"]),
                    str(check_data["recipient_wallet"]),
                    str(signature_tx)
                )
            except Exception as e:
                return jsonify({"error": str(e)}), 500

            if "error" in res_depos:
                return jsonify(res_depos)
            return jsonify({"success": True})
    else:
        return jsonify({"error": "The token you have sent does not correspond to PAMBI 2.0 or MINI token. If you have made a mistake, contact support via telegram."})

@app.route('/check_my_balance', methods=['POST'])
@limiter.limit("60 per minute")  # Aplicar límite específico si es necesario
def check_my_balance():
    try:
        data = request.get_json()
        hashchat = escape(data.get('hashchat', ''))

        if not hashchat:
            return jsonify({'success': False, 'error': 'Session hash is required'}), 400

        if hashchat not in global_vars.sessions:
            return jsonify({'success': False, 'error': 'Invalid session hash'}), 401

        wallet = global_vars.sessions[hashchat]
        checking = AccountsDBTools(
    user_db=os.getenv('USERDB'),
    password_db=os.getenv('PASSWORDDB'),
    host_db=os.getenv('DBHOST'),
    port_db=os.getenv('PORTDB'),
    database="MINI_platform"
)
        tools_checking = ToolsChecking(checking)

        balance_usd = checking.check_my_balance(wallet)
        

        res = {"my_balance_usd": str(balance_usd)}
        return jsonify(res)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/update_messages_history', methods=['POST'])
@limiter.limit("60 per minute")  # Aplicar límite específico si es necesario
def update_messages_history():
    try:
        data = request.get_json()
        hashchat = escape(data.get("hashsesion", ''))
        len_list_history = int(data.get("len_list_history", 0))

        if hashchat not in chat_sessions.hashAvalible and hashchat not in chat_sessions.hash_invite_session_avalible:
            return jsonify({'message': "Error login session", "audio_autoplay": None, "deploy_item": None, "role": "server"})

        if hashchat in chat_sessions.hash_invite_session_avalible:
            hashchat = chat_sessions.hash_invite_session_avalible[hashchat]

        if len(chat_sessions.ChatHistory.get(hashchat, [])) <= len_list_history:
            return jsonify({'message': "not_update_history_chat", "audio_autoplay": None, "deploy_item": None, "role": "system"})
        else:
            return jsonify(chat_sessions.ChatHistory[hashchat])
    except Exception as e:
        print(f"Error en update_messages_history: {e}")
        return jsonify({'message': "Internal server error. Please try again later.", "audio_autoplay": None, "deploy_item": None, "role": "server"}), 500



db_tools_subtract_cost = CostExtracAccount(user_db, password_db, host_db, port_db)
@app.route('/chat/message', methods=['POST'])
@limiter.limit("60 per minute")  # Aplicar límite específico si es necesario
def message():
    logger.info("Recibida solicitud POST en /chat/message")

    # Obtener y validar el JSON de la solicitud
    data = request.get_json()
    if not data:
        logger.error("No se recibió un payload JSON válido en la solicitud")
        return jsonify({'message': "Invalid JSON payload"}), 400

    logger.debug(f"Datos JSON recibidos: {data}")

    # Extraer y escapar los campos necesarios
    hashchat = escape(data.get('hashchat', ''))
    message_text = escape(data.get('message', ''))
    AudioPlay = escape(data.get('audio', ''))
    username = escape(data.get('usernickname', ''))
    images_base64 = data.get('images_list', [])
    wallet_user = global_vars.sessions[hashchat]
    logger.info(f"Campos extraídos - hashchat: '{hashchat}', username: '{username}'")

    if not hashchat:
        logger.error("El campo 'hashchat' está ausente o vacío en el payload")
        return jsonify({'message': "hashchat is required"}), 400

    # Intentar obtener el índice de hashchat en hash_sesions_index
    try:
        hashuserindex = int(chat_sessions.hash_sesions_index.index(hashchat))
        logger.debug(f"Índice de hashchat '{hashchat}' en hash_sesions_index: {hashuserindex}")
    except ValueError:
        logger.warning(f"hashchat '{hashchat}' no encontrado en hash_sesions_index")
        return jsonify({
            'message': "Invalid session index",
            "audio_autoplay": None,
            "deploy_item": None,
            "role": "server"
        }), 400

    # Verificar si hashchat está disponible
    if hashchat not in chat_sessions.hashAvalible:
        logger.info(f"hashchat '{hashchat}' no está en hashAvalible")
        if hashchat not in chat_sessions.hash_invite_session_avalible:
            logger.warning(f"hashchat '{hashchat}' tampoco está en hash_invite_session_avalible")
            return jsonify({
                'message': "This chat has already been deleted if you want to continue chatting please create another room, log in again",
                "audio_autoplay": None,
                "deploy_item": None,
                "role": "server"
            })
        else:
            # hashchat está en hash_invite_session_avalible
            new_hashchat = chat_sessions.hash_invite_session_avalible.get(hashchat)
            if new_hashchat:
                logger.info(f"Remapeando hashchat '{hashchat}' a '{new_hashchat}'")
                hashchat = new_hashchat
            else:
                logger.error(f"hashchat '{hashchat}' está en hash_invite_session_avalible pero no se encontró el remapeo")
                return jsonify({
                    'message': "Invalid invite session mapping",
                    "audio_autoplay": None,
                    "deploy_item": None,
                    "role": "server"
                }), 400
    else:
        # hashchat está en hashAvalible
        logger.debug(f"hashchat '{hashchat}' está disponible. Estableciendo username a 'Admin'")
        username = "Admin"  # Asegúrate de que esto es lo que deseas

    # Actualizar el tiempo de chat
    chat_sessions.chattimes[hashchat] = time.time()
    logger.debug(f"Actualizado chattimes para hashchat '{hashchat}'")

    # Inicializar ChatHistory si no existe
    if hashchat not in chat_sessions.ChatHistory:
        chat_sessions.ChatHistory[hashchat] = []
        logger.debug(f"Inicializada ChatHistory para hashchat '{hashchat}'")

    # Añadir mensaje del usuario al historial
    user_message = f'<div style="font-weight: lighter;">{username}:</div>{message_text}'
    chat_sessions.ChatHistory[hashchat].append({
        'message': user_message,
        "audio_autoplay": None,
        "deploy_item": None,
        "role": 'user',
        "user_index": hashuserindex + 6,
    })
    logger.info(f"Añadido mensaje del usuario a ChatHistory para hashchat '{hashchat}'")

    html_return = None

    # Verificar si la sesión online existe para hashchat
    session_online = chat_sessions.sessions_online.get(hashchat)
    if not session_online:
        logger.error(f"No se encontró una sesión online para hashchat '{hashchat}'")
        return jsonify({'message': "Session not found"}), 400

    # Procesar el mensaje a través de la sesión online
    try:
        recive_msg, audio_recive, html_return, type_renderize = session_online.push_new_msg_user(
            f'{username}: {message_text}', AudioPlay, images_base64
        )
        logger.debug(f"Respuesta de push_new_msg_user - recive_msg: '{recive_msg}', audio_recive: '{audio_recive}', html_return: '{html_return}'")
    except Exception as e:
        logger.exception(f"Error al procesar push_new_msg_user para hashchat '{hashchat}': {e}")
        return jsonify({'message': "Internal server error"}), 500

    recive_msg = escape(recive_msg)
    print("&&&"*16)
    print(type_renderize)
    print("&&&"*16)

    # Eliminar los ciclos for y solo mantener los append
    if type_renderize == "render_page_preview":
        ai_message = html_return
        chat_sessions.ChatHistory[hashchat].append({
            'message': ai_message,
            "audio_autoplay": audio_recive,
            "deploy_item": True,
            "role": 'deploy_item',
            "user_index": hashuserindex + 6
        })
        global_vars.html_current_code[hashchat]=ai_message
        
    elif type_renderize == "music_generated":
        ai_message = html_return
        chat_sessions.ChatHistory[hashchat].append({
            'message': ai_message,
            "audio_autoplay": audio_recive,
            "deploy_item": False,
            "role": 'server',
            "user_index": hashuserindex + 6
        })
        db_tools_subtract_cost.tools_subtract_cost(wallet=wallet_user, amount=0.16)
    
    elif type_renderize == "image_generated":
        ai_message = html_return
        chat_sessions.ChatHistory[hashchat].append({
            'message': ai_message,
            "audio_autoplay": audio_recive,
            "deploy_item": False,
            "role": 'server',
            "user_index": hashuserindex + 6
        })
        db_tools_subtract_cost.tools_subtract_cost(wallet=wallet_user, amount=0.04)
    else:
        # Si no hay un type_renderize específico, agregar el mensaje de texto de la IA
        if recive_msg:
            ai_message = f'<div style="font-weight: lighter;">AI Answer:{recive_msg}</div>'
            chat_sessions.ChatHistory[hashchat].append({
                'message': ai_message,
                "audio_autoplay": audio_recive,
                "deploy_item": False,
                "role": 'server',
                "user_index": hashuserindex + 6
            })

    return jsonify({'success': True})

# Carga la URL de QuickNode desde una variable de entorno por seguridad
QUICKNODE_URL = os.getenv('QUICKNODE_URL')


@app.route('/solana_chain', methods=['POST'])
@limiter.limit("20 per minute")  # Aplica la limitación de tasa a esta ruta
def solana_proxy():
    try:
        # Extrae el cuerpo de la solicitud original
        payload = request.get_json()
        if not payload:
            return jsonify({"error": "Solicitud inválida, se esperaba JSON"}), 400

        # Realiza la solicitud a QuickNode
        headers = {
            'Content-Type': 'application/json'
        }
        response = requests.post(QUICKNODE_URL, json=payload, headers=headers)

        # Retorna la respuesta de QuickNode al cliente
        return jsonify(response.json()), response.status_code

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))  # Por defecto, usa el puerto 5000 si no se encuentra la variable de entorno
    app.run(host='0.0.0.0', port=port, debug=True)