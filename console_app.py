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
    
    print("=" * 60)
    print("🤖 AI Assistant Console")
    print("=" * 60)
    print("\n📌 **Capabilities:**")
    print("  👤 GitHub User Analysis - Send profile URL")
    print("  🔍 GitHub Repo Analysis - Send repo URL")
    print("  🧠 Logical Assistant - Ask any question\n")
  
    
    while True:
        user_input = input("You: ").strip()
        
        if not user_input:
            continue
        
        if user_input.lower() == "exit":
            print("\n👋 Goodbye! Have a great day!\n")
            break
        
        if user_input.lower() == "clear":
            db_client.clear_conversation(session_id)
            state = {"messages": [], "message_type": None}
            print("✅ Conversation history cleared!\n")
            continue
        
        if user_input.lower() == "stats":
            stats = db_client.get_conversation_stats(session_id)
            if stats:
                print("\n" + "=" * 40)
                print("📊 Conversation Statistics")
                print("=" * 40)
                print(f"  Total Messages: {stats['total_messages']}")
                print(f"  Your Messages: {stats['user_messages']}")
                print(f"  Assistant Messages: {stats['assistant_messages']}")
                print("=" * 40 + "\n")
            else:
                print("❌ No conversation history found.\n")
            continue
        
        
        state["messages"].append({"role": "user", "content": user_input})
        
        print("\n⏳ Processing...\n")
        
        try:
            # Invoke the graph
            state = graph.invoke(state)
            
            # Save to database
            db_client.save_conversation(state, session_id)
            
            # Display response
            if state.get("messages") and len(state["messages"]) > 0:
                last_message = state["messages"][-1]
                message_type = state.get("message_type", "logical")
                
                # Select emoji based on message type
                if message_type == "Github_user":
                    emoji = "👤"
                    type_label = "User Analysis"
                elif message_type == "Github":
                    emoji = "🔍"
                    type_label = "Repo Analysis"
                else:
                    emoji = "🧠"
                    type_label = "Logical"
                
                print("-" * 60)
                print(f"{emoji} Assistant ({type_label}):")
                print("-" * 60)
                
                # Get content
                if isinstance(last_message, dict):
                    content = last_message.get("content")
                else:
                    content = last_message.content
                
                print(f"\n{content}\n")
                print("-" * 60 + "\n")
            else:
                print("❌ Sorry, I couldn't process your message.\n")
        
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("Please try again or type 'help' for examples.\n")

if __name__ == "__main__":
    run_chatbot()