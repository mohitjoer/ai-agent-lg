from pydantic import BaseModel, Field
from typing import Literal
from typing_extensions import TypedDict
from typing import Annotated
from langgraph.graph.message import add_messages

class MessageClassifier(BaseModel):
    """Schema for message classification"""
    message_type: Literal["emotional", "logical"] = Field(
        ...,
        description="Classify if the message requires an emotional (therapist) or logical response"
    )

class State(TypedDict):
    """State schema for the graph"""
    messages: Annotated[list, add_messages]
    message_type: str | None