import logging
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext
from config import telegram_token, database
from db_manager import DB_Manager
import sqlite3
import time

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize the database
db_manager = DB_Manager(database)
db_manager.create_tables()

# Retry mechanism decorator
def with_retries(max_retries=3, delay=1):
    def decorator(func):
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except sqlite3.Error as e:
                    retries += 1
                    logger.error(f"Database error: {e}, retrying {retries}/{max_retries}")
                    time.sleep(delay)
            return None
        return wrapper
    return decorator

# Define command handlers
def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text('Hello! I am your bot.')

@with_retries()
def add_car(update: Update, context: CallbackContext) -> None:
    if len(context.args) < 3:
        update.message.reply_text('Usage: /add_car <car_brand> <color> <year>')
        return

    try:
        car_brand = context.args[0]
        color = context.args[1]
        year = int(context.args[2])
        
        with sqlite3.connect(database) as con:
            con.execute('INSERT INTO Car (car_brand, color, year) VALUES (?, ?, ?)', (car_brand, color, year))
        update.message.reply_text(f'Car added: {car_brand}, {color}, {year}')
    except ValueError:
        update.message.reply_text('Year must be an integer.')
    except sqlite3.Error as e:
        logger.error(f"Failed to add car: {e}")
        update.message.reply_text('An error occurred while adding the car.')

@with_retries()
def delete_car(update: Update, context: CallbackContext) -> None:
    if len(context.args) < 1:
        update.message.reply_text('Usage: /delete_car <car_id>')
        return

    try:
        car_id = int(context.args[0])
        
        with sqlite3.connect(database) as con:
            result = con.execute('DELETE FROM Car WHERE car_id = ?', (car_id,))
            if result.rowcount == 0:
                update.message.reply_text(f'No car found with car_id: {car_id}')
            else:
                update.message.reply_text(f'Car with car_id {car_id} has been deleted.')
    except ValueError:
        update.message.reply_text('Car ID must be an integer.')
    except sqlite3.Error as e:
        logger.error(f"Failed to delete car: {e}")
        update.message.reply_text('An error occurred while deleting the car.')

@with_retries()
def view_cars(update: Update, context: CallbackContext) -> None:
    try:
        with sqlite3.connect(database) as con:
            con.row_factory = sqlite3.Row
            cursor = con.execute('SELECT car_id, car_brand, color, year FROM Car')
            rows = cursor.fetchall()

        if rows:
            message = "Here are the cars in the database:\n\n"
            for row in rows:
                message += f"ID: {row['car_id']}, Brand: {row['car_brand']}, Color: {row['color']}, Year: {row['year']}\n"
        else:
            message = "No cars found in the database."

        update.message.reply_text(message)
    except sqlite3.Error as e:
        logger.error(f"Failed to retrieve cars: {e}")
        update.message.reply_text('An error occurred while retrieving the cars.')

def main() -> None:
    # Create the Updater and pass it your bot's token
    updater = Updater(telegram_token)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # Register command handlers
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("add_car", add_car))
    dispatcher.add_handler(CommandHandler("delete_car", delete_car))
    dispatcher.add_handler(CommandHandler("view_cars", view_cars))

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT, SIGTERM, or SIGABRT
    updater.idle()

if __name__ == '__main__':
    main()
