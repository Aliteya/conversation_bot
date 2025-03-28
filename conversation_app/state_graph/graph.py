# from .start_state import start
# from .rate_state import rate
# from .bargaining import bargaining
# from .finish_state import finish
# from .refuse_state import refuse
from ..core import llm

from ..logging import logger
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain.prompts import PromptTemplate
from typing import TypedDict, List, Annotated, Literal, Optional
from langchain.schema import HumanMessage
import re

class State(TypedDict):
    messages: List[str]
    solution: Optional[Literal["accepted", "rejected"]]
    price: Optional[float]
    format: Optional[str]
    cpm: Optional[float]
    views: Optional[List[int]]

def init_state() -> State:
    return {
        "messages": [],
        "solution": None,
        "price": None,
        "format": None,
        "cpm": None,
        "views": None
    }

async def add_message(state: State, text: str) -> State:
    state["messages"].append(text)
    return state

async def start(state):
    logger.info("state start")
    state = await add_message(state, "Введите входные данные: желаемая клиентом цена за 1000 просмотров, количество просмотров у блогера. Точное число либо рендж: 100 000, 5 000 - 10 000")
    return state

async def rate(state):
    logger.info("state start")
    prompt = PromptTemplate(
        input_variables=["text"],
        template="get cpm and views from the following text. Return in (cpm_value, views_value or views_min_value-views_max_value) strict format."
    )
    message = HumanMessage(content=prompt.format(text=state["messages"][-1]))
    response = await llm.ainvoke([message])
    state = await add_message(state,"Hey, please, provide your desired rate")

    pattern = r"\((\d+),\s*(\d+)(?:-(\d+))?\)"
    
    match = re.match(pattern, response.content.strip())
    if not match:
        raise ValueError("Invalid input format. Expected: (cpm_value, views_value or views_min_value-views_max_value)")
    
    cpm = int(match.group(1)) 
    views_min_value = match.group(2)  
    views_max_value = match.group(3)
    if views_max_value:
        views = [int(views_min_value), int(views_max_value)]  
    else:
        views = [int(views_min_value)] 
    state["cpm"] = cpm
    state["views"] = views
    return state


async def bargaining(state):
    logger.info("state barg")
    pass

async def finish(state):
    pass

async def refuse(state):
    pass

memory = MemorySaver()

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

app = workflow.compile(checkpointer=memory)