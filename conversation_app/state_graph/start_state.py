from ..logging import logger
from .util import add_message

async def start(state):
    logger.info("state start")
    state = await add_message(state, "Введите входные данные: желаемая клиентом цена за 1000 просмотров, количество просмотров у блогера. Точное число либо рендж: 100 000, 5 000 - 10 000")
    return state