from dotenv import load_dotenv
import os

load_dotenv()

class Settings:
    """Application settings"""
    MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    LLM_MODEL = "gpt-4o"
    GEMINI_MODEL = "gemini-1.5-pro" 
    DATABASE_NAME = "chatbot_db"
    CONVERSATIONS_COLLECTION = "conversations"
    MESSAGES_COLLECTION = "messages"
    USE_GEMINI = True 

settings = Settings()