from dotenv import load_dotenv
from typing import Annotated , Literal
from langgraph.graph import StateGraph , START , END
from langgraph.graph.message import add_messages
from langchain.chat_models import init_chat_model
from pydantic import BaseModel , Field
from typing_extensions import TypedDict
from pymongo import MongoClient
from datetime import datetime, UTC
import os

load_dotenv()

llm =  init_chat_model("gpt-4o") 

mongo_client = MongoClient(os.getenv("MONGODB_URI"))
db = mongo_client["chatbot_db"]
conversations_collection = db["conversations"]
messages_collection = db["messages"]

class MessageClassifier(BaseModel):
    message_type : Literal["emotional","logical"] = Field(
        ...,
        description="Classify if the message requires an emotional (therpaist) or logical response"
    )

class State(TypedDict):
    messages: Annotated[list, add_messages]
    message_type: str | None

def classify_message(state : State):
    last_message = state["messages"][-1]
    classifier_llm = llm.with_structured_output(MessageClassifier)
    
    result=classifier_llm.invoke([
        {
            "role":'system',
            "content":"""classify the user message as either:
            -'emotional': if itt askes for emotional support , therapy, deals with feelings,
            -'logical': if it asks for facts, inforation, logical analysis, or practical
            """
        },
        {"role": "user", "content": last_message.content}
    ])
    return {"message_type": result.message_type}


def router(state : State):
    message_type= state.get("message_type","logical")
    if message_type == "emotional":
        return {"next":"therapist"}
    return {"next":"logical"}


def therapist_agent(state : State):
    messages = [
        {"role":"system",
         "content":"""you are a compassionate therapist. Focus on the emotional asoect of the user's message.
         show empathy, validate their feelings, and help them process their emotions.
         ask thoughful questions to help them explore their fellings more deeply.
         avoid giving logical solutions unless explicitly asked."""
        }
    ]
    
    # Handle both dict and LangChain message objects
    for msg in state["messages"]:
        if isinstance(msg, dict):
            messages.append({"role": msg.get("role", "user"), "content": msg.get("content")})
        else:
            # LangChain message object
            role = "assistant" if msg.type == "ai" else "user"
            messages.append({"role": role, "content": msg.content})
    
    reply = llm.invoke(messages)
    return {"messages":[{"role":"assistant","content": reply.content}]}

def logical_agent(state : State):
    messages = [
        {"role":"system",
         "content":"""you are a pureely logical assistant. Focus only on facts and information. 
            provide clear, concise answers based on logic and evidence.
            do not address emotions or provide emotional support .
            be direct and straightforward in your responses."""
        }
    ]

    for msg in state["messages"]:
        if isinstance(msg, dict):
            messages.append({"role": msg.get("role", "user"), "content": msg.get("content")})
        else:
            role = "assistant" if msg.type == "ai" else "user"
            messages.append({"role": role, "content": msg.content})
    
    reply = llm.invoke(messages)
    return {"messages":[{"role":"assistant","content": reply.content}]}

graph_builder = StateGraph(State)


graph_builder.add_node("classifier" , classify_message)
graph_builder.add_node("router" , router)
graph_builder.add_node("therapist" , therapist_agent)
graph_builder.add_node("logical" , logical_agent)

graph_builder.add_edge( start_key=START , end_key="classifier" )
graph_builder.add_edge( start_key="classifier", end_key="router")

graph_builder.add_conditional_edges(
    "router",
    lambda state: state.get("next"),
    path_map={"therapist":"therapist","logical":"logical"}
)

graph_builder.add_edge(start_key="therapist", end_key=END)
graph_builder.add_edge(start_key="logical", end_key=END)

graph = graph_builder.compile()

def save_conversation_to_db(state: State, session_id: str):
    """Save conversation state to MongoDB"""
    conversation_data = {
        "session_id": session_id,
        "message_type": state.get("message_type"),
        "timestamp": datetime.now(UTC),  
        "messages": []
    }
    
    for msg in state["messages"]:
        if isinstance(msg, dict):
            message_entry = {
                "role": msg.get("role", "user"),
                "content": msg.get("content"),
                "timestamp": datetime.now(UTC)  
            }
        else:
            role = "assistant" if msg.type == "ai" else "user"
            message_entry = {
                "role": role,
                "content": msg.content,
                "timestamp": datetime.now(UTC)  
            }
        conversation_data["messages"].append(message_entry)
    
    conversations_collection.update_one(
        {"session_id": session_id},
        {"$set": conversation_data},
        upsert=True
    )

def run_chatbot():
    state = {"messages":[],"message_type":None}
    existing_conversation = conversations_collection.find_one({"session_id": "single_session"})
    if existing_conversation and existing_conversation.get("messages"):
        state["messages"] = [
            {"role": msg["role"], "content": msg["content"]} 
            for msg in existing_conversation["messages"]
        ]
        print("Loaded previous conversation history.")
    
    session_id = "single_session"
    while True :
        user_input = input("Enter A Message:")
        if user_input == "exit":
            print("bye")
            break
        
        state["messages"].append({"role":"user","content":user_input})

        state = graph.invoke(state)
        
    
        save_conversation_to_db(state, session_id)
        
        if state.get("messages") and len(state["messages"]) > 0 :
            last_message=state["messages"][-1]
            print(f"Assistant: {last_message.content}")
    
if __name__ == "__main__":
    run_chatbot()