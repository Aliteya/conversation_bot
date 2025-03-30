from ..logging import logger
from .util import State

async def finish(state: State):
    logger.debug("finish state")
    state.blogger_price = state.price
    await state.add_message(f"Решение: {state.solution}. Итоговый формат сделки: {state.format}, Стоимость сделки: {state.price}")
    return state