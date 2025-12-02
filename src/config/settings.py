from dotenv import load_dotenv
import os

load_dotenv()

class Settings:
    """Application settings"""
    MONGODB_URI = os.getenv("MONGODB_URI")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    LLM_MODEL = "gpt-4o"
    DATABASE_NAME = "chatbot_db"
    CONVERSATIONS_COLLECTION = "conversations"
    MESSAGES_COLLECTION = "messages"

settings = Settings()