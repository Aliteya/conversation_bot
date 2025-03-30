from .start_state import start
from .rate_state import rate
from .bargaining import bargaining
# from .finish_state import finish
# from .refuse_state import refuse
from .util import State
from ..core import llm
from ..logging import logger


from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain.prompts import PromptTemplate

from langchain.schema import HumanMessage
import json

async def bargaining_fix(state: State):
    logger.info("State bargaining fix with sale")
    logger.debug(f'State in bargaining fix node: {state}')
    last_message = state.messages[-1]
    prompt = PromptTemplate(
        input_variables=["text"],
        template="""
        Проанализируй сообщение блогера и определи, согласен ли он на предложенную сделку.
        Ответь СТРОГО ТОЛЬКО одно слово: "True" или "False".
        
        Примеры:
        - "Да, согласен" → True
        - "Нет, не устраивает" → False
        
        Текст: {text}
        """
    )
    try:
        message = HumanMessage(content=prompt.format(text=last_message))
        response = await llm.ainvoke([message])
        response_text = response.content.strip().lower()
        logger.debug(f"Подходит ли новая сделка: {response_text}, {type(response_text)}")
        
        if response_text == "true":
            state.solution = "accepted"
            # state.blogger_price = state.price
            # ПЕРЕХОД НА ФИНАЛ
        else:
            if not state.sale:
                state.sale = 20
                state.price *= 1.2
                await state.add_message(f"Предлагаю Вам на 20% больше от первоначальной суммы, {state.price}")
                # БЕРЁМ СКИДКУ И КРУТИМСЯ НА ЭТОМ УЗЛЕ
            elif state.sale == 20: 
                state.sale = 30
                state.price = 1.3 * (await state.get_average_price()) 
                await state.add_message(f"Предлагаю Вам на 30% больше от первоначальной суммы, {state.price}")
                # БЕРЁМ СКИДКУ И КРУТИМСЯ НА ЭТОМ УЗЛЕ
            else: 
                state.format = "cpm"
                await state.add_message("Предлагаю перейти на другой формат сделки")
                # МЕНЯЕМ КОНЕЙ НА ПЕРЕПРАВЕ
        return state
    except Exception as e:
        logger.error(f"Ошибка парсинга ответа LLM. Получено: {response.content}")
        await state.add_message(f"Ошибка обработки. Получен ответ: {response.content[:100]}...")
        raise ValueError("Invalid LLM response format")

async def bargaining_cpm(state: State):
    logger.info("State bargaining fix with sale")
    logger.debug(f'State in bargaining fix node: {state}')
    return state

async def finish(state: State):
    logger.debug("finish state")
    state.blogger_price = state.price
    await state.add_message(f"Прекрасно, тогда скоро отправим Вам материалы. Решение: {state.solution}. Итоговый формат сделки: {state.format}, Стоимость сделки: {state.price}")
    return state

async def refuse(state):
    pass

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
        "refuse": "refuse", 
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
        "refuse": "refuse",
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
        "bargaining_fix": "bargaining_fix"
    }
)
workflow.add_edge("finish", END)
workflow.add_edge("refuse", END)

app = workflow.compile(checkpointer=memory, interrupt_before=["rate", "bargaining", "bargaining_fix", "bargaining_cpm"])