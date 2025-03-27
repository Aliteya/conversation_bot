from .start_state import start
from .rate_state import rate
from .bargaining import bargaining
from .finish_state import finish
from .refuse_state import refuse


from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain.prompts import PromptTemplate
from typing import TypedDict, List

class State(TypedDict):
    text: str
    solution: str
    price: float
    format: str
    cpm: float
    views: List[int]

workflow = StateGraph(state_schema=State)

workflow.add_node("start", start)
workflow.add_node("rate", rate)
workflow.add_node("bargaining", bargaining)
workflow.add_node("finish", finish)
workflow.add_node("refuse", refuse)

workflow.set_entry_point("start")
workflow.add_edge("start", "rate")
workflow.add_edge("rate", "bargaining")
workflow.add_conditional_edges("bargaining", lambda state: "finish")
workflow.add_edge("finish", END)
workflow.add_edge("refuse", END)

memory = MemorySaver()
app = workflow.compile(checkpointer=memory)