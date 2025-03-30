from ..logging import logger
from ..core import llm
from .util import State

from langchain.prompts import PromptTemplate
from langchain.schema import HumanMessage

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
            # ПЕРЕХОД НА ФИНАЛ
        else:
            if state.price <= state.blogger_price and  state.blogger_price < state.price*1.2:
                state.solution = "accepted"
                state.price = state.blogger_price
                await state.add_message(f"Принимаем ваше предложение {state.blogger_price}$")
                return state
            if not state.sale:
                state.sale = 20
                state.price = state.fixprice * 1.2
                await state.add_message(f"Предлагаю Вам на 20% больше от первоначальной суммы, {state.price}$")
                # БЕРЁМ СКИДКУ И КРУТИМСЯ НА ЭТОМ УЗЛЕ
            elif state.sale == 20: 
                state.price = state.fixprice * 1.3
                if state.blogger_price < state.price:
                    state.solution = "accepted"
                    state.price = state.blogger_price
                    await state.add_message(f"Принимаем ваше предложение {state.blogger_price}$")
                    return state
                state.sale = 30
                await state.add_message(f"Предлагаю Вам на 30% больше от первоначальной суммы, {state.price}$")
                # БЕРЁМ СКИДКУ И КРУТИМСЯ НА ЭТОМ УЗЛЕ
            else: 
                state.price = await state.get_average_price()
                state.format = "cpm"
                await state.add_message(f"Предлагаю перейти на другой формат сделки. Оплата за каждую 1000 просмотров: {state.cpm}, цена: {state.price}.")
                # МЕНЯЕМ КОНЕЙ НА ПЕРЕПРАВЕ
        return state
    except Exception as e:
        logger.error(f"Ошибка парсинга ответа LLM. Получено: {response.content}")
        await state.add_message(f"Ошибка обработки. Получен ответ: {response.content[:100]}...")
        raise ValueError("Invalid LLM response format")