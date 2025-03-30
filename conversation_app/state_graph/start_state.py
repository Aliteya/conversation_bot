from ..logging import logger
from .util import State

async def start(state: State) -> State:
    logger.info("state start")
    state = await state.add_message("Введите входные данные: желаемая клиентом цена за 1000 просмотров, количество просмотров у блогера. Точное число либо рендж: 100 000, 5 000 - 10 000. Также если хотите укажите фиксированную цену рекламы.")
    return state