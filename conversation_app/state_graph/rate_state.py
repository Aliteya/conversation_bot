from ..logging import logger
from ..core import llm
from .util import State

from langchain.prompts import PromptTemplate
from langchain.schema import HumanMessage
import json

async def rate(state: State):
    logger.info("state rate")
    last_message = state.messages[-1]
    logger.info(f"Последнее сообщение: {last_message}")

    prompt = PromptTemplate(
        input_variables=["text"],
        template="""
        Извлеки следующие данные из текста:
        - Цена за 1000 просмотров (CPM) в долларах (только число) если не в долларах, то посмотри по нынешнему курсу нац. банка
        - Количество просмотров (только число или два числа через дефис)
        - Если есть фиксированная ставка в долларах (только число) которую хочет отдать клиент за рекламу, то выгрузи и ее

        Текст: {text}

        Ответ ДОЛЖЕН быть строго в формате JSON БЕЗ каких-либо обратных кавычек или markdown:
        {{
            "cpm": число,
            "views": [число] | [число, число]
            "fixprice": число | null
        }}

        Пример правильного ответа:
        {{"cpm": 100, "views": [120000], "fixprice": 500}}
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
        fixprice = data["fixprice"]

        state.cpm = cpm
        state.views = views if isinstance(views, list) else [views]
        state.fixprice = fixprice
        await state.add_message("Подскажите цену рекламной интеграции. Также Вы можете указать желаемый формат сделки(фиксированная или cpm)")
        
        logger.debug(f"State in rate node: {state}")
        return state

    except (json.JSONDecodeError, KeyError) as e:
        logger.error(f"Ошибка парсинга ответа LLM. Получено: {response.content}")
        await state.add_message(f"Ошибка обработки. Получен ответ: {response.content[:100]}...")
        raise ValueError("Invalid LLM response format")