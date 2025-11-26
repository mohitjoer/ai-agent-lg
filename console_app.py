from src.utils.graph_builder import graph
from src.database.mongo_client import db_client

def run_chatbot():
    """Run the console chatbot"""
    state = {"messages": [], "message_type": None}
    session_id = "console_session"
    
    # Load existing conversation
    existing_conversation = db_client.load_conversation(session_id)
    if existing_conversation and existing_conversation.get("messages"):
        state["messages"] = [
            {"role": msg["role"], "content": msg["content"]} 
            for msg in existing_conversation["messages"]
        ]
        print("✅ Loaded previous conversation history.\n")
    
    print("🤖 AI Assistant Console")
    print("Type 'exit' to quit, 'clear' to clear history, 'stats' for statistics\n")
    
    while True:
        user_input = input("You: ")
        
        if user_input.lower() == "exit":
            print("👋 Goodbye!")
            break
        
        if user_input.lower() == "clear":
            db_client.clear_conversation(session_id)
            state = {"messages": [], "message_type": None}
            print("✅ Conversation history cleared!\n")
            continue
        
        if user_input.lower() == "stats":
            stats = db_client.get_conversation_stats(session_id)
            if stats:
                print(f"\n📊 Statistics:")
                print(f"Total Messages: {stats['total_messages']}")
                print(f"Your Messages: {stats['user_messages']}")
                print(f"Assistant Messages: {stats['assistant_messages']}\n")
            else:
                print("No conversation history found.\n")
            continue
        
        state["messages"].append({"role": "user", "content": user_input})
        
        # Invoke the graph
        state = graph.invoke(state)
        
        # Save to database
        db_client.save_conversation(state, session_id)
        
        # Display response
        if state.get("messages") and len(state["messages"]) > 0:
            last_message = state["messages"][-1]
            message_type = state.get("message_type", "logical")
            emoji = "❤️" if message_type == "emotional" else "🧠"
            print(f"{emoji} Assistant: {last_message.content}\n")

if __name__ == "__main__":
    run_chatbot()