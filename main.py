from dotenv import load_dotenv
from typing import Annotated , Literal
from langgraph.graph import StateGraph , START , END
from langgraph.graph.message import add_messages
from langchain.chat_models import init_chat_model
from pydantic import BaseModel , Field
from typing_extensions import TypedDict

load_dotenv()

llm =  init_chat_model("gpt-4")

class State(TypedDict):
    messages: Annotated[list, add_messages]

graph_builder = StateGraph(State)

def chatbot(state: State):
    return {"messages":[llm.invoke(state["messages"])]}



graph_builder.add_node("chatbot",chatbot)
graph_builder.add_edge( start_key=START , end_key="chatbot" )
graph_builder.add_edge( start_key="chatbot", end_key=END)

graph = graph_builder.compile()

user_input = input("Enter A Message:")
state = graph.invoke({"messages":[{"role":"user","content":user_input}]})

print(state["messages"][-1].content)