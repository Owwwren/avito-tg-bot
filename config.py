import os
from dotenv import load_dotenv

load_dotenv()

AVITO_CLIENT_ID = os.getenv("AVITO_CLIENT_ID")
AVITO_CLIENT_SECRET = os.getenv("AVITO_CLIENT_SECRET")
AVITO_USER_ID = int(os.getenv("AVITO_USER_ID"))
BOT_TOKEN = str(os.getenv("BOT_TOKEN"))
ALLOWED_USER_IDS = list(map(int, os.getenv("ALLOWED_USER_IDS", "").split(",")))
GIGACHAT_CREDENTIALS = os.getenv("GIGACHAT_CREDENTIALS")