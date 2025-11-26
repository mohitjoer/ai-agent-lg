from pymongo import MongoClient
from datetime import datetime, UTC
from src.config.settings import settings

class MongoDBClient:
    """MongoDB client for conversation storage"""
    
    def __init__(self):
        self.client = MongoClient(settings.MONGODB_URI)
        self.db = self.client[settings.DATABASE_NAME]
        self.conversations = self.db[settings.CONVERSATIONS_COLLECTION]
        self.messages = self.db[settings.MESSAGES_COLLECTION]
    
    def save_conversation(self, state, session_id: str):
        """Save conversation state to MongoDB"""
        conversation_data = {
            "session_id": session_id,
            "message_type": state.get("message_type"),
            "timestamp": datetime.now(UTC),
            "messages": []
        }
        
        for msg in state["messages"]:
            if isinstance(msg, dict):
                message_entry = {
                    "role": msg.get("role", "user"),
                    "content": msg.get("content"),
                    "timestamp": datetime.now(UTC)
                }
            else:
                role = "assistant" if msg.type == "ai" else "user"
                message_entry = {
                    "role": role,
                    "content": msg.content,
                    "timestamp": datetime.now(UTC)
                }
            conversation_data["messages"].append(message_entry)
        
        self.conversations.update_one(
            {"session_id": session_id},
            {"$set": conversation_data},
            upsert=True
        )
    
    def load_conversation(self, session_id: str):
        """Load conversation from MongoDB"""
        return self.conversations.find_one({"session_id": session_id})
    
    def clear_conversation(self, session_id: str):
        """Clear conversation history"""
        self.conversations.delete_one({"session_id": session_id})
    
    def get_conversation_stats(self, session_id: str):
        """Get conversation statistics"""
        conversation = self.conversations.find_one({"session_id": session_id})
        
        if conversation and conversation.get("messages"):
            total_messages = len(conversation["messages"])
            user_messages = sum(1 for msg in conversation["messages"] if msg["role"] == "user")
            assistant_messages = sum(1 for msg in conversation["messages"] if msg["role"] == "assistant")
            
            return {
                "total_messages": total_messages,
                "user_messages": user_messages,
                "assistant_messages": assistant_messages,
                "session_id": session_id
            }
        return None

db_client = MongoDBClient()