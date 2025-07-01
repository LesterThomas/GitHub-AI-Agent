"""
LangGraph State Logging Examples

This file demonstrates various approaches to logging state changes in LangGraph.
"""

import logging
from typing import Annotated, List, Dict, Any, TypedDict
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class StateWithLogging(TypedDict):
    """State that includes logging-friendly fields."""

    messages: Annotated[List[BaseMessage], add_messages]
    current_step: str
    step_count: int
    data: Dict[str, Any]
    errors: List[str]


def log_state_change(state: StateWithLogging, node_name: str, phase: str):
    """Log detailed state changes."""
    logger.info(f"[{node_name}:{phase}] State Update")
    logger.info(f"  Step: {state.get('current_step', 'unknown')}")
    logger.info(f"  Count: {state.get('step_count', 0)}")
    logger.info(f"  Messages: {len(state.get('messages', []))}")
    logger.info(f"  Data keys: {list(state.get('data', {}).keys())}")
    logger.info(f"  Errors: {len(state.get('errors', []))}")


def create_logging_wrapper(node_func, node_name: str):
    """Create a wrapper that logs state changes for any node."""

    def wrapped_node(state: StateWithLogging) -> StateWithLogging:
        logger.info(f"🔄 Entering node: {node_name}")
        log_state_change(state, node_name, "entry")

        # Execute the original node function
        result = node_func(state)

        log_state_change(result, node_name, "exit")
        logger.info(f"✅ Exiting node: {node_name}")

        return result

    wrapped_node.__name__ = f"logged_{node_name}"
    return wrapped_node


# Example nodes with built-in logging
def analysis_node(state: StateWithLogging) -> StateWithLogging:
    """Node that performs analysis with state logging."""
    logger.info("🔍 Starting analysis...")

    new_state = {
        **state,
        "current_step": "analysis",
        "step_count": state.get("step_count", 0) + 1,
        "data": {
            **state.get("data", {}),
            "analysis_result": "completed",
            "analysis_time": "2024-01-01T00:00:00Z",
        },
    }

    logger.info(f"📊 Analysis completed. Data: {new_state['data']}")
    return new_state


def processing_node(state: StateWithLogging) -> StateWithLogging:
    """Node that processes data with state logging."""
    logger.info("⚙️ Starting processing...")

    # Simulate some processing logic
    errors = state.get("errors", [])
    if not state.get("data", {}).get("analysis_result"):
        errors.append("No analysis result found")

    new_state = {
        **state,
        "current_step": "processing",
        "step_count": state.get("step_count", 0) + 1,
        "data": {
            **state.get("data", {}),
            "processing_result": "success" if not errors else "failed",
            "processed_items": 42,
        },
        "errors": errors,
    }

    status = "✅" if not errors else "❌"
    logger.info(
        f"{status} Processing completed. Result: {new_state['data'].get('processing_result')}"
    )
    return new_state


def create_comprehensive_logging_graph():
    """Create a LangGraph with comprehensive state logging."""

    # Create the graph
    workflow = StateGraph(StateWithLogging)

    # Add nodes with logging wrappers
    workflow.add_node("analysis", create_logging_wrapper(analysis_node, "analysis"))
    workflow.add_node(
        "processing", create_logging_wrapper(processing_node, "processing")
    )

    # Set up the graph structure
    workflow.set_entry_point("analysis")
    workflow.add_edge("analysis", "processing")
    workflow.add_edge("processing", END)

    # Compile with memory checkpointer for state persistence
    app = workflow.compile(checkpointer=MemorySaver())

    return app


def run_with_stream_logging(app, initial_state, config):
    """Run the graph with streaming to capture all state changes."""
    logger.info("🚀 Starting graph execution with stream logging")

    final_state = None
    step_count = 0

    # Use multiple stream modes for comprehensive logging
    for chunk in app.stream(
        initial_state, config, stream_mode=["values", "updates", "debug"], debug=True
    ):
        step_count += 1

        if isinstance(chunk, tuple) and len(chunk) == 2:
            mode, data = chunk

            if mode == "values":
                # Complete state after each step
                logger.info(f"📝 Step {step_count} - Complete State:")
                if isinstance(data, dict):
                    for key, value in data.items():
                        if key == "messages":
                            logger.info(f"  {key}: {len(value)} messages")
                        elif isinstance(value, (list, dict)):
                            logger.info(
                                f"  {key}: {type(value).__name__} with {len(value)} items"
                            )
                        else:
                            logger.info(f"  {key}: {value}")
                final_state = data

            elif mode == "updates":
                # Individual node updates
                logger.info(f"🔄 Step {step_count} - Node Updates:")
                if isinstance(data, dict):
                    for node_name, update in data.items():
                        if node_name != "__end__":
                            logger.info(f"  Node '{node_name}' produced update")
                            if hasattr(update, "content"):
                                logger.info(
                                    f"    Content: {str(update.content)[:100]}..."
                                )

            elif mode == "debug":
                logger.info(f"🐛 Step {step_count} - Debug: {str(data)[:100]}...")

        elif isinstance(chunk, dict):
            # Direct state update
            logger.info(f"📦 Step {step_count} - Direct state update")
            final_state = chunk

    logger.info(f"🏁 Graph execution completed after {step_count} steps")
    return final_state


def example_usage():
    """Example of how to use the logging functionality."""

    # Create the graph
    app = create_comprehensive_logging_graph()

    # Initial state
    initial_state = StateWithLogging(
        messages=[
            SystemMessage(content="System initialized"),
            HumanMessage(content="Please analyze and process the data"),
        ],
        current_step="start",
        step_count=0,
        data={},
        errors=[],
    )

    # Configuration
    config = {"configurable": {"thread_id": "example-thread"}, "recursion_limit": 10}

    # Run with comprehensive logging
    logger.info("=" * 50)
    logger.info("STARTING EXAMPLE EXECUTION")
    logger.info("=" * 50)

    final_state = run_with_stream_logging(app, initial_state, config)

    logger.info("=" * 50)
    logger.info("FINAL RESULTS")
    logger.info("=" * 50)
    logger.info(f"Final step: {final_state.get('current_step')}")
    logger.info(f"Total steps: {final_state.get('step_count')}")
    logger.info(f"Data: {final_state.get('data')}")
    logger.info(f"Errors: {final_state.get('errors')}")


if __name__ == "__main__":
    example_usage()
