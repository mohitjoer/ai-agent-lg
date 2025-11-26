from langchain.chat_models import init_chat_model
from src.models.schemas import State
from src.config.settings import settings

llm = init_chat_model(settings.LLM_MODEL)

def logical_agent(state: State):
    """Logical assistance agent"""
    messages = [
        {
            "role": "system",
            "content": """You are a purely logical assistant. Focus only on facts and information.
            Provide clear, concise answers based on logic and evidence.
            Do not address emotions or provide emotional support.
            Be direct and straightforward in your responses."""
        }
    ]

    for msg in state["messages"]:
        if isinstance(msg, dict):
            messages.append({"role": msg.get("role", "user"), "content": msg.get("content")})
        else:
            role = "assistant" if msg.type == "ai" else "user"
            messages.append({"role": role, "content": msg.content})
    
    reply = llm.invoke(messages)
    return {"messages": [{"role": "assistant", "content": reply.content}]}