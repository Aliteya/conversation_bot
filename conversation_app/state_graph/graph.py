from .start_state import start
from .rate_state import rate
from .bargaining import bargaining
from .bargaining_fix import bargaining_fix
from .bargaining_cpm import bargaining_cpm
from .finish_state import finish
from .refuse_state import refuse
from .util import State


from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver


def decide_next_state(state: State):
    if state.solution == "accepted":
        return "finish"
    elif state.solution == "rejected":
        return "refuse"
    else:
        if state.format == "fix":
            return "bargaining_fix"
        elif state.format == "cpm":
            return "bargaining_cpm"
        else:
            return "bargaining"
    

memory = MemorySaver()

workflow = StateGraph(state_schema=State)

workflow.add_node("start", start)
workflow.add_node("rate", rate)

workflow.add_node("bargaining", bargaining)
workflow.add_node("bargaining_fix", bargaining_fix)
workflow.add_node("bargaining_cpm", bargaining_cpm)

workflow.add_node("finish", finish)
workflow.add_node("refuse", refuse)

workflow.set_entry_point("start")
workflow.add_edge("start", "rate")
workflow.add_edge("rate", "bargaining")
workflow.add_conditional_edges(
    "bargaining",
    decide_next_state,
    {
        "finish" : "finish", 
        "bargaining": "bargaining", 
        "bargaining_fix" : "bargaining_fix", 
        "bargaining_cpm": "bargaining_cpm"
    }
)
workflow.add_conditional_edges(
    "bargaining_fix",
    decide_next_state,
    {
        "finish": "finish",
        "bargaining_fix": "bargaining_fix",
        "bargaining_cpm": "bargaining_cpm"
    }
)

workflow.add_conditional_edges(
    "bargaining_cpm",
    decide_next_state,
    {
        "finish": "finish",
        "refuse": "refuse",
        "bargaining_cpm": "bargaining_cpm",
    }
)

workflow.add_edge("finish", END)
workflow.add_edge("refuse", END)

app = workflow.compile(checkpointer=memory, interrupt_before=["rate", "bargaining", "bargaining_fix", "bargaining_cpm", "refuse"])