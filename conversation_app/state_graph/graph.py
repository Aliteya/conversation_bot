from .start_state import start
from .rate_state import rate
# from .bargaining import bargaining
# from .finish_state import finish
# from .refuse_state import refuse
from .util import add_message
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
    format: Optional[Literal["fix", "cpm"]]
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


async def bargaining(state: State):
    logger.info("state barg")
    logger.debug(f'State in bargaining node: {state}')
    last_message = state["messages"][-1]
    prompt = PromptTemplate(
        input_variables=["text"],
        template="""
        Извлеки следующие данные из текста:
        - Желаемый прайс по которому будет работать клиент. 
        Стоимость бери обязательно в долларах, если не в них то переводи по курсу нац. банка.
        Если в ответе нет стоимости, то оставляй ее 0.
        
        Текст: {text}
        Ответ ДОЛЖЕН быть строго в формате JSON БЕЗ каких-либо обратных кавычек или markdown:
        {{
            "price": число,
        }}

        Пример правильного ответа:
        {{"price": 100}}
        """
    )
    message = HumanMessage(content=prompt.format(text=last_message))
    response = await llm.ainvoke([message])
    try:
        response_text = response.content.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7: -3].strip()

        data = json.loads(response_text)
        price = data["price"]

        state["price"] = price
        logger.debug(f"Price adding to state {price}")

        client_a_price = ((state["cpm"] * (((state["views"][0] + state["views"][-1]) / 2) + state["views"][-1]) / 2) / 1000)
        client_x_price = float(state["cpm"] * state["views"][0]) / 1000
        
        if 0 < state["price"] and state["price"] <= client_x_price:
            state.update({
                "solution": "accepted",
                "format": "fix",
                "price": state["price"]
            })
            state["format"] = "fix"
        else: 
            state["price"] = client_a_price

        return state

    except (json.JSONDecodeError, KeyError) as e:
        logger.error(f"Ошибка парсинга ответа LLM. Получено: {response.content}")
        await add_message(state, f"Ошибка обработки. Получен ответ: {response.content[:100]}...")
        raise ValueError("Invalid LLM response format")


async def finish(state):
    pass

async def refuse(state):
    pass

def decide_next_state(state):
    if state["solution"] == "accepted":
        return "finish"
    elif state["solution"] == "rejected":
        return "refuse"
    else:
        return "bargaining"
    

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
workflow.add_conditional_edges("bargaining", decide_next_state, {"finish" : "finish", "refuse": "refuse", "bargaining": "bargaining"})
workflow.add_edge("finish", END)
workflow.add_edge("refuse", END)

app = workflow.compile(checkpointer=memory, interrupt_after="*")