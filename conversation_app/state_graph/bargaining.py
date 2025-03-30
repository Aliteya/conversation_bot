from ..logging import logger
from ..core import llm
from .util import State

from langchain.prompts import PromptTemplate
from langchain.schema import HumanMessage
import json

async def bargaining(state: State):
    logger.info("state barg")
    logger.debug(f'State in bargaining node: {state}')
    last_message = state.messages[-1]
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
            state.blogger_price = blogger_price
        logger.debug(f"Price adding to state {blogger_price}")
        if state.fixprice is None:
            state.fixprice = await state.get_average_price()
        client_a_price = state.fixprice
        state.price = await state.get_min_price()
        logger.debug(f"Средняя цена {client_a_price}, Минимальная цена {state.price}")
        
        if blogger_price is None: 
            blogger_price = client_a_price
            state.blogger_price = client_a_price

        if blogger_price <= state.price:
            state.price = state.blogger_price
            state.solution = "accepted"
            state.format = "fix"
            await state.add_message("Мы согласны.") 
            # ВОТ ТУТ ПЕРЕХОД НА ФИНАЛ
        else: 
            state.solution = "negotiating"
            state.format = "fix"
            state.price = client_a_price
            await state.add_message(f"Предлагаю Вам {client_a_price} за рекламную интеграцию.") 
            # ПЕРЕХОД НА ДРУГУЮ ФИКСИРОВАННУЮ СТАВКУ
        return state

    except (json.JSONDecodeError, KeyError) as e:
        logger.error(f"Ошибка парсинга ответа LLM. Получено: {response.content}")
        await state.add_message(f"Ошибка обработки. Получен ответ: {response.content[:100]}...")
        raise ValueError("Invalid LLM response format")