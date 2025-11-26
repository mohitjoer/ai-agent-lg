from langchain.chat_models import init_chat_model
from src.models.schemas import MessageClassifier, State
from src.config.settings import settings
import google.generativeai as genai
import json

if settings.USE_GEMINI:
    genai.configure(api_key=settings.GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel(settings.GEMINI_MODEL)
else:
    llm = init_chat_model(settings.LLM_MODEL)

def classify_message_with_gemini(state: State):
    """Classify the user message using Gemini AI"""
    last_message = state["messages"][-1]
    
    if isinstance(last_message, dict):
        content = last_message.get("content")
    else:
        content = last_message.content
    
    prompt = f"""Classify the following user message as either 'emotional' or 'logical'.

Rules:
- 'emotional': if it asks for emotional support, therapy, deals with feelings, personal problems
- 'logical': if it asks for facts, information, logical analysis, or practical advice

User message: {content}

Respond ONLY with a JSON object in this exact format:
{{"message_type": "emotional"}} or {{"message_type": "logical"}}"""

    try:
        response = gemini_model.generate_content(prompt)
        response_text = response.text.strip()
        
        if '```json' in response_text:
            response_text = response_text.split('```json')[1].split('```')[0].strip()
        elif '```' in response_text:
            response_text = response_text.split('```')[1].split('```')[0].strip()
        
        result = json.loads(response_text)
        message_type = result.get("message_type", "logical")
        
        if message_type not in ["emotional", "logical"]:
            message_type = "logical"
        
        return {"message_type": message_type}
    
    except Exception as e:
        print(f"Error in Gemini classification: {e}")
        return {"message_type": "logical"}

def classify_message_with_openai(state: State):
    """Classify the user message using OpenAI"""
    last_message = state["messages"][-1]
    classifier_llm = llm.with_structured_output(MessageClassifier)
    
    result = classifier_llm.invoke([
        {
            "role": 'system',
            "content": """Classify the user message as either:
            - 'emotional': if it asks for emotional support, therapy, deals with feelings
            - 'logical': if it asks for facts, information, logical analysis, or practical advice
            """
        },
        {"role": "user", "content": last_message.content}
    ])
    return {"message_type": result.message_type}

def classify_message(state: State):
    """Classify the user message using configured AI provider"""
    if settings.USE_GEMINI:
        return classify_message_with_gemini(state)
    else:
        return classify_message_with_openai(state)