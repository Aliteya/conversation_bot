from ..logging import logger
from ..core import llm
from .util import State

from langchain.prompts import PromptTemplate
from langchain.schema import HumanMessage

async def bargaining_cpm(state: State):
    logger.info("State bargaining fix with sale")
    logger.debug(f'State in bargaining fix node: {state}')
    last_message = state.messages[-1]
    
    prompt_template = """
    Проанализируй сообщение блогера и определи, согласен ли он на предложенную сделку.
    Ответь СТРОГО ТОЛЬКО одно слово: "True" или "False".

    Примеры:
        - "Хорошо" → True
        - "Не хочу" → False
        - "Согласен, но ставка низкая" → True
    
    Текст: {text}
    """
    try:
        prompt = PromptTemplate(input_variables=["text"], template=prompt_template)
        message = HumanMessage(content=prompt.format(text=last_message))
        response = await llm.ainvoke([message])
        response_text = response.content.strip().lower()
        
        logger.debug(f"Согласие на CPM сделку: {response_text}")

        if response_text == "false":
            state.solution = "rejected"
            await state.add_message(f"Предложите свою цену. Я поговорю с клиентов о предоставлении большего бюджета на рекламу.") 
            return state
        else:
            conditions_template = """
            Проанализируй сообщение блогера и определи его реакцию на условия CPM.
            Ответь СТРОГО ТОЛЬКО одним словом:
            - "price_ok" - согласен с ценой и ставкой сpm
            - "cpm_low" - не устраивает ставка CPM
            - "reject_cpm" - против системы CPM
            
            Примеры:
            - "Цена низкая" → cpm_low
            - "Не хочу CPM" → reject_cpm
            
            Текст: {text}
            """
            
            prompt = PromptTemplate(input_variables=["text"], template=conditions_template)
            message = HumanMessage(content=prompt.format(text=last_message))
            response = await llm.ainvoke([message])
            conditions_response = response.content.strip().lower()

            logger.debug(f"Ответ на условия CPM: {conditions_response}")

            if conditions_response == "price_ok":
                state.solution = "accepted"
                await state.add_message("Сделка подтверждена!")

            elif conditions_response == "cpm_low":
                state.cpm *= 1.15
                state.price *= 1.15
                await state.add_message(f"CPM +15% → {state.cpm}$,  → {state.price}$.")
            
            else:
                logger.error(f"Неподдерживаемый ответ: {conditions_response}")
                raise ValueError("Invalid CPM conditions response")

            return state

    except Exception as e:
        logger.error(f"Ошибка: {str(e)}")
        await state.add_message("Ошибка обработки. Пожалуйста, уточните запрос.")
        state.solution = "error"
        return state