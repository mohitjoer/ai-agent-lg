from src.models.schemas import State

def router(state: State):
    """Route to appropriate agent based on message type"""
    message_type = state.get("message_type", "logical")
    if message_type == "emotional":
        return {"next": "therapist"}
    return {"next": "logical"}