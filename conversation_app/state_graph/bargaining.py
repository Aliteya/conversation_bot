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
        1.Вид сделки по которой готов работать блогер(если есть)
        2. Предложенную цену (если есть)
        3. Если блогера пишет что не хочет общаться, то добавь поле "solution": "rejected"
        Если цена не в долларах - конвертируй по курсу.
        Если данных нет - верни null.

        
        Текст: {text}
        Ответ в формате JSON:
        {{
            "format": строка|null,
            "price": число|null,
            "solution": "rejected"|null
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
        if response_data.get("solution") is not None:
            state.solution = "rejected"
            await state.add_message(f"Предложите свою цену. Я поговорю с клиентов о предоставлении большего бюджета на рекламу.") 
            return state

        blogger_price = response_data.get("price")
        state.format = response_data.get("format")

        if blogger_price is not None:
            state.blogger_price = blogger_price
        logger.debug(f"Price adding to state {blogger_price}")
        if state.fixprice is None:
            state.fixprice = await state.get_average_price()
        client_a_price = state.fixprice
        state.price = await state.get_min_price()
        logger.debug(f"Средняя цена {client_a_price}, Минимальная цена {state.price}")
        
        if blogger_price is None and state.blogger_price is None: 
            state.blogger_price = client_a_price

        if state.blogger_price <= state.price:
            state.price = state.blogger_price
            state.solution = "accepted"
            state.format = "fix"
            await state.add_message("Мы согласны.") 
            # ВОТ ТУТ ПЕРЕХОД НА ФИНАЛ
        else: 
            state.solution = "negotiating"
            if state.format == "cpm":
                state.price = await state.get_average_price()
                await state.add_message(f"Предлагаю перейти на другой формат сделки. Оплата за каждую 1000 просмотров: {state.cpm}, цена: {state.price}. Напишите, согласны ли вы на такой вид сделки, и если да, выскажите свое мнение насчет ставки по cpm.")
            else:
                state.price = client_a_price
                state.format = "fix"
                await state.add_message(f"Предлагаю Вам {client_a_price} за рекламную интеграцию.") 
            # ПЕРЕХОД НА ДРУГУЮ ФИКСИРОВАННУЮ СТАВКУ
        return state

    except (json.JSONDecodeError, KeyError) as e:
        logger.error(f"Ошибка парсинга ответа LLM. Получено: {response.content}")
        await state.add_message(f"Ошибка обработки. Получен ответ: {response.content[:100]}...")
        raise ValueError("Invalid LLM response format")