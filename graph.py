
"""LangGraph workflow for Incident Zero."""

from langgraph.graph import END, START, StateGraph

from diagnose import diagnose_incident
from state import IncidentState


def build_graph():
    """Build and compile the initial diagnosis workflow."""
    workflow = StateGraph(IncidentState)

    # Run the evidence-based diagnosis.
    workflow.add_node("diagnose", diagnose_incident)

    # Start with diagnosis using the evidence already in the state.
    workflow.add_edge(START, "diagnose")

    # Stop after diagnosis or escalation.
    workflow.add_edge("diagnose", END)

    return workflow.compile()


def run_incident(initial_state: IncidentState) -> dict:
    """Run the workflow using the supplied incident state."""
    app = build_graph()
    return app.invoke(initial_state)
