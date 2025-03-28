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
import json

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
    logger.info(f"Added message to context: {text}")
    logger.info(f"Now message context: {list(state["messages"])}")
    return state

async def start(state):
    logger.info("state start")
    state = await add_message(state, "Введите входные данные: желаемая клиентом цена за 1000 просмотров, количество просмотров у блогера. Точное число либо рендж: 100 000, 5 000 - 10 000")
    return state

async def rate(state):
    logger.info("state rate")
    last_message = state["messages"][-1]
    logger.info(f"Последнее сообщение: {last_message}")

    prompt = PromptTemplate(
        input_variables=["text"],
        template="""
        Извлеки следующие данные из текста:
        - Цена за 1000 просмотров (CPM) в долларах (только число)
        - Количество просмотров (только число или два числа через дефис)

        Текст: {text}

        Ответ ДОЛЖЕН быть строго в формате JSON БЕЗ каких-либо обратных кавычек или markdown:
        {{
            "cpm": число,
            "views": число | [число, число]
        }}

        Пример правильного ответа:
        {{"cpm": 100, "views": [120000]}}
        """
    )

    message = HumanMessage(content=prompt.format(text=last_message))
    response = await llm.ainvoke([message])
    
    try:
        response_text = response.content.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:-3].strip()
        
        data = json.loads(response_text)
        cpm = data["cpm"]
        views = data["views"]

        state["cpm"] = cpm
        state["views"] = views if isinstance(views, list) else [views]
        state = await add_message(state,"Hey, please, provide your desired rate")
        
        logger.debug(f"State in rate node: {state}")
        return state

    except (json.JSONDecodeError, KeyError) as e:
        logger.error(f"Ошибка парсинга ответа LLM. Получено: {response.content}")
        await add_message(state, f"Ошибка обработки. Получен ответ: {response.content[:100]}...")
        raise ValueError("Invalid LLM response format")

async def bargaining(state):
    logger.info("state barg")
    logger.debug(f'State in bargaining node: {state}')
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

app = workflow.compile(checkpointer=memory, interrupt_after="*")