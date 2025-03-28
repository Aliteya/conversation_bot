from ..logging import logger

async def rate(state):
    logger.info("state rate")
    return {"text": "Hey, please, provide your desired rate"}