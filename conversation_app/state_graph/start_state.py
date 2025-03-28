from ..logging import logger

async def start(state):
    logger.info("state start")
    return {"text": "Введите входные данные: желаемая клиентом цена за 1000 просмотров, количество просмотров у блогера. Точное число либо рендж: 100 000, 5 000 - 10 000"}