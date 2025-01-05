from dotenv import load_dotenv
import os

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

USERS_BASE_DIR = os.getenv("USERS_BASE_DIR")
DATA_BASE_DIR = os.getenv("DATA_BASE_DIR")