from langchain.chat_models import init_chat_model
from src.models.schemas import State
from src.config.settings import settings
import google.generativeai as genai

if settings.USE_GEMINI:
    genai.configure(api_key=settings.GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel(settings.GEMINI_MODEL)
else:
    llm = init_chat_model(settings.LLM_MODEL)

def therapist_agent(state: State):
    """Emotional support agent"""
    system_prompt = """You are a compassionate therapist. Focus on the emotional aspect of the user's message.
    Show empathy, validate their feelings, and help them process their emotions.
    Ask thoughtful questions to help them explore their feelings more deeply.
    Avoid giving logical solutions unless explicitly asked."""
    
    if settings.USE_GEMINI:
        conversation = []
        for msg in state["messages"]:
            if isinstance(msg, dict):
                role = msg.get("role", "user")
                content = msg.get("content")
            else:
                role = "assistant" if msg.type == "ai" else "user"
                content = msg.content
            
            if role == "user":
                conversation.append(f"User: {content}")
            else:
                conversation.append(f"Assistant: {content}")
        
        full_prompt = f"{system_prompt}\n\n" + "\n".join(conversation)
        
        response = gemini_model.generate_content(full_prompt)
        return {"messages": [{"role": "assistant", "content": response.text}]}
    
    else:
        messages = [{"role": "system", "content": system_prompt}]
        
        for msg in state["messages"]:
            if isinstance(msg, dict):
                messages.append({"role": msg.get("role", "user"), "content": msg.get("content")})
            else:
                role = "assistant" if msg.type == "ai" else "user"
                messages.append({"role": role, "content": msg.content})
        
        reply = llm.invoke(messages)
        return {"messages": [{"role": "assistant", "content": reply.content}]}