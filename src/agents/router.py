from src.models.schemas import State

def router(state: State):
    """Route to appropriate agent based on message type"""
    message_type = state.get("message_type", "logical")
    if message_type == "Github":  
        return {"next": "github"}  
    return {"next": "logical"}