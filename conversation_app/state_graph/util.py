from ..logging import logger 

async def add_message(state, text: str):
    state["messages"].append(text)
    logger.info(f"Added message to context: {text}")
    logger.info(f"Now message context: {list(state["messages"])}")
    return state