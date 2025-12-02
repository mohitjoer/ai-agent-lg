from langchain.chat_models import init_chat_model
from src.models.schemas import MessageClassifier, State
from src.config.settings import settings

llm = init_chat_model(settings.LLM_MODEL)

def classify_message(state: State):
    """Classify the user message using OpenAI"""
    last_message = state["messages"][-1]
    classifier_llm = llm.with_structured_output(MessageClassifier)
    
    result = classifier_llm.invoke([
        {
            "role": 'system',
            "content": """Classify the user message as either:
            - 'Github': if it asks for github repo standards, grades, deals with code quality, code analysis, or contains a GitHub URL
            - 'logical': if it asks for facts, information, logical analysis, or practical advice
            """
        },
        {"role": "user", "content": last_message.content if hasattr(last_message, 'content') else last_message.get("content")}
    ])
    return {"message_type": result.message_type}