from ..logging import logger
from ..core import llm
from .util import State

from langchain.prompts import PromptTemplate
from langchain.schema import HumanMessage
import json

async def refuse(state: State):
    logger.debug("Refuse state")

    last_message = state.messages[-1]
    prompt = PromptTemplate(
        input_variables=["text"],
        template="""
        Проанализируй текст и извлеки из него сумму в долларах.
        Сумму записывай в ответ без значка $.

        Примеры:
        Ответ в формате JSON:
        {{
            "blogger_price": число | null
        }}
        Текст: {text}
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
        state.blogger_price = response_data["blogger_price"]
        await state.add_message(f"Решение: {state.solution}. Цена от блогера: {state.blogger_price}. Последний наш прайc: {state.price}. Причина отказа - не сошлись в цене.")
        return state
    except Exception as e:
        logger.error(f"Ошибка парсинга ответа LLM. Получено: {response.content}")
        await state.add_message(f"Ошибка обработки. Получен ответ: {response.content[:100]}...")
        raise ValueError("Invalid LLM response format")