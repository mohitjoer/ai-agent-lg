from langgraph.graph import StateGraph, START, END
from src.models.schemas import State
from src.agents.classifier import classify_message
from src.agents.router import router
from src.agents.therapist import therapist_agent
from src.agents.logical import logical_agent

def build_graph():
    """Build and compile the agent graph"""
    graph_builder = StateGraph(State)
    
    # nodes
    graph_builder.add_node("classifier", classify_message)
    graph_builder.add_node("router", router)
    graph_builder.add_node("therapist", therapist_agent)
    graph_builder.add_node("logical", logical_agent)
    
    # edges
    graph_builder.add_edge(start_key=START, end_key="classifier")
    graph_builder.add_edge(start_key="classifier", end_key="router")
    
    # Conditional
    graph_builder.add_conditional_edges(
        "router",
        lambda state: state.get("next"),
        path_map={"therapist": "therapist", "logical": "logical"}
    )
    
    graph_builder.add_edge(start_key="therapist", end_key=END)
    graph_builder.add_edge(start_key="logical", end_key=END)
    
    return graph_builder.compile()

graph = build_graph()