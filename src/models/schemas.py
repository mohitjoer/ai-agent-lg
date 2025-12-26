from pydantic import BaseModel, Field
from typing import Literal
from typing_extensions import TypedDict
from typing import Annotated
from langgraph.graph.message import add_messages

class MessageClassifier(BaseModel):
    """Schema for message classification and extraction"""
    message_type: Literal["Github","Github_user", "logical"] = Field(
        ...,
        description="Classify if the message requires GitHub analysis or logical response",
    )
    username: str | None = Field(
        default=None,
        description="GitHub username (owner). For 'Github_user' this is the user; for 'Github' this is the repo owner.",
    )
    repo_name: str | None = Field(
        default=None,
        description="GitHub repository name when message_type is 'Github'",
    )

class State(TypedDict):
    """State schema for the graph"""
    messages: Annotated[list, add_messages]
    message_type: str | None
    username: str | None
    repo_name: str | None