from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from src.utils.graph_builder import graph
from src.database.mongo_client import db_client
from src.config.settings import settings

SINGLE_SESSION_ID = "telegram"
user_sessions = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler"""
    user_id = update.effective_user.id
    
    existing_conversation = db_client.load_conversation(SINGLE_SESSION_ID)
    if existing_conversation and existing_conversation.get("messages"):
        user_sessions[user_id] = {
            "messages": [
                {"role": msg["role"], "content": msg["content"]} 
                for msg in existing_conversation["messages"]
            ],
            "message_type": None
        }
        await update.message.reply_text(
            "Welcome back! 👋\n\n"
            "I've loaded your previous conversation history.\n"
            "I can provide both emotional support and logical assistance based on your needs."
        )
    else:
        user_sessions[user_id] = {
            "messages": [],
            "message_type": None
        }
        await update.message.reply_text(
            "Hello! 👋 I'm your AI assistant with dual capabilities:\n\n"
            "🧠 Logical assistance for facts and information\n"
            "❤️ Emotional support as a compassionate therapist\n\n"
            "Just send me a message and I'll respond appropriately!\n\n"
            "Commands:\n"
            "/start - Start conversation\n"
            "/clear - Clear history\n"
            "/stats - View statistics\n"
            "/help - Show help"
        )

async def clear_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear conversation history"""
    user_id = update.effective_user.id
    
    db_client.clear_conversation(SINGLE_SESSION_ID)
    
    user_sessions[user_id] = {
        "messages": [],
        "message_type": None
    }
    
    await update.message.reply_text("✅ Your conversation history has been cleared!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming messages"""
    user_id = update.effective_user.id
    user_message = update.message.text
    
    if user_id not in user_sessions:
        user_sessions[user_id] = {
            "messages": [],
            "message_type": None
        }
    
    state = user_sessions[user_id]
    state["messages"].append({"role": "user", "content": user_message})
    
    await update.message.chat.send_action(action="typing")
    
    try:
        result = graph.invoke(state)
        user_sessions[user_id] = result
        db_client.save_conversation(result, SINGLE_SESSION_ID)
        
        if result.get("messages") and len(result["messages"]) > 0:
            last_message = result["messages"][-1]
            
            if isinstance(last_message, dict):
                response_content = last_message.get("content")
            else:
                response_content = last_message.content
            
            message_type = result.get("message_type", "logical")
            emoji = "❤️" if message_type == "emotional" else "🧠"
            
            await update.message.reply_text(f"{emoji} {response_content}")
        else:
            await update.message.reply_text("Sorry, I couldn't process your message.")
    
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        await update.message.reply_text("Sorry, something went wrong. Please try again.")

async def get_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get conversation statistics"""
    stats = db_client.get_conversation_stats(SINGLE_SESSION_ID)
    
    if stats:
        stats_text = (
            "📊 **Conversation Statistics**\n\n"
            f"Total Messages: {stats['total_messages']}\n"
            f"Your Messages: {stats['user_messages']}\n"
            f"My Responses: {stats['assistant_messages']}"
        )
        await update.message.reply_text(stats_text, parse_mode='Markdown')
    else:
        await update.message.reply_text("No conversation history found. Start chatting with me!")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command"""
    help_text = (
        "🤖 **AI Assistant Help**\n\n"
        "I automatically detect if you need:\n"
        "❤️ Emotional support (therapist mode)\n"
        "🧠 Logical assistance (facts & information)\n\n"
        "**Commands:**\n"
        "/start - Start/restart conversation\n"
        "/clear - Clear conversation history\n"
        "/stats - View conversation statistics\n"
        "/help - Show this help message\n\n"
        "Just send me any message and I'll respond appropriately!"
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

def main():
    """Start the Telegram bot"""
    token = settings.TELEGRAM_BOT_TOKEN
    
    if not token:
        print("❌ Error: TELEGRAM_BOT_TOKEN not found in .env file")
        return
    
    application = Application.builder().token(token).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("clear", clear_history))
    application.add_handler(CommandHandler("stats", get_stats))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("✅ Telegram Bot is running... Press Ctrl+C to stop.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()