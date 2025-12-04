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
            "content": """Classify the user message into ONE of these categories:

            1. 'Github_user': Use this when:
            - The message asks about a GitHub USER profile, developer, or person
            - Contains a GitHub profile URL like "https://github.com/username" (NO repo name after username)
            - Mentions fetching user data, user info, user profile
            - Contains phrases like "this user", "developer profile", "user's repos"
            - Example: "https://github.com/torvalds" or "tell me about @octocat"

            2. 'Github': Use this when:
            - The message asks about a specific GitHub REPOSITORY
            - Contains a GitHub repo URL like "https://github.com/owner/repo" (HAS repo name)
            - Mentions code quality, repo analysis, repo standards, grading a repo
            - Example: "https://github.com/facebook/react" or "analyze this repo"

            3. 'logical': Use this when:
            - The message is a general question
            - Asks for facts, information, explanations
            - No GitHub URLs or usernames mentioned
            - Example: "What is Python?" or "How do databases work?"

            IMPORTANT: 
            - If URL has ONLY username (github.com/username) → 'Github_user'
            - If URL has username AND repo (github.com/username/repo) → 'Github'
            """
        },
        {"role": "user", "content": last_message.content if hasattr(last_message, 'content') else last_message.get("content")}
    ])
    return {"message_type": result.message_type}