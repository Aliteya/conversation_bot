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
        Проанализируй сообщение блогера и извлеки:
        1. Предложенную цену (если есть)
        Если цена не в долларах - конвертируй по курсу.
        Если данных нет - верни null.
        
        Текст: {text}
        Ответ в формате JSON:
        {{
            "price": число|null
        }}
        """
    )
    try:
        message = HumanMessage(content=prompt.format(text=last_message))
        response = await llm.ainvoke([message])
        response_text = response.content.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7: -3].strip()

        response_data = json.loads(response_text)
        logger.debug(f"Response data: {response_data}")
        blogger_price = response_data.get("price")

        if blogger_price is not None:
            state["blogger_price"] = blogger_price
        logger.debug(f"Price adding to state {blogger_price}")

        client_a_price = ((state["cpm"] * (((state["views"][0] + state["views"][-1]) / 2) + state["views"][-1]) / 2) / 1000)
        client_x_price = float(state["cpm"] * state["views"][0]) / 1000
        logger.debug(f"Средняя цена {client_a_price}, Минимальная цена {client_x_price}")
        
        if blogger_price is None: 
            blogger_price = client_a_price
            state["blogger_price"] = client_a_price

        if blogger_price <= client_x_price:
            state.update({
                "solution": "accepted",
                "format": "fix",
                "price": blogger_price
            })
            await add_message(state, "Мы согласны.") 
            # ВОТ ТУТ ПЕРЕХОД НА ФИНАЛ
        else: 
            state.update({
                "format": "fix",
                "price": client_a_price
            })
            await add_message(state, f"Предлагаю Вам {client_a_price} за рекламную интеграцию.") 
        return state

    except (json.JSONDecodeError, KeyError) as e:
        logger.error(f"Ошибка парсинга ответа LLM. Получено: {response.content}")
        await add_message(state, f"Ошибка обработки. Получен ответ: {response.content[:100]}...")
        raise ValueError("Invalid LLM response format")

async def bargaining_fix(state: State):
    logger.info("state bargaining fix with cap")
    logger.debug(f'State in bargaining node: {state}')
    last_message = state["messages"][-1]
    prompt = PromptTemplate(
        input_variables=["text"],
        template="""
        Проанализируй сообщение блогера {text}. Если он согласен на сделку тогда верни строку True,
        иначе False
        
        Текст: {text}
        Ответ в формате str:
        'True'
        """
    )
    try:
        message = HumanMessage(content=prompt.format(text=last_message))
        response = await llm.ainvoke([message])
        response_text = response.content.strip()
        logger.debug(f"Подходит ли новая сделка: {response_text}")
        state["blogger_price"] = state["price"]
        if response_text == 'True':
            state["solution"] = "accepted"
            state["price"] = state["blogger_price"]
            # await add_message(state, f"Прекрасно, тогда скоро отправим Вам материалы. Решение: {state["solution"]}. Итоговый формат сделки: {state.get("format", "Заключение сделки не удалось")}, Стоимость сделки: {state.get("price", "Заключение сделки не удалось")}")
            # ПЕРЕХОД НА ФИНАЛ
        else:
            if "sale" not in state:
                state["sale"] = 20
                state["blogger_price"] *= 1.2
                await add_message(state, "Предлагаю Вам скидку в 20% от первоначальной суммы")
                # БЕРЁМ СКИДКУ И КРУТИМСЯ НА ЭТОМ УЗЛЕ
            elif state["sale"] == 20: 
                state["sale"] += 10
                state["blogger_price"] = state["price"] * 1.3
                await add_message(state, "Предлагаю Вам скидку в 30% от первоначальной суммы")
                # БЕРЁМ СКИДКУ И КРУТИМСЯ НА ЭТОМ УЗЛЕ
            else: 
                state["format"] = "cpm"
                await add_message(state, "Предлагаю перейти на другой формат сделки")
                # МЕНЯЕМ КОНЕЙ НА ПЕРЕПРАВЕ
    except Exception as e:
        logger.error(f"Ошибка парсинга ответа LLM. Получено: {response.content}")
        await add_message(state, f"Ошибка обработки. Получен ответ: {response.content[:100]}...")
        raise ValueError("Invalid LLM response format")

async def bargaining_cpm(state):
    pass

async def finish(state):
    logger.debug("finish state")
    await add_message(state, f"Прекрасно, тогда скоро отправим Вам материалы. Решение: {state["solution"]}. Итоговый формат сделки: {state.get("format", "Заключение сделки не удалось")}, Стоимость сделки: {state.get("price", "Заключение сделки не удалось")}")
    return state

async def refuse(state):
    pass

def decide_next_state(state):
    if state["solution"] == "accepted":
        return "finish"
    elif state["solution"] == "rejected":
        return "refuse"
    else:
        if state["format"] == "fix":
            return "bargaining_fix"
        elif state["format"] == "cpm":
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
workflow.add_conditional_edges("bargaining", decide_next_state, {"finish" : "finish", "refuse": "refuse", "bargaining": "bargaining", "bargaining_fix" : "bargaining_fix", "bargaining_cpm": "bargaining_cpm"})
workflow.add_edge("finish", END)
workflow.add_edge("refuse", END)

app = workflow.compile(checkpointer=memory, interrupt_before=["rate", "bargaining", "bargaining_fix", "bargaining_cpm"])