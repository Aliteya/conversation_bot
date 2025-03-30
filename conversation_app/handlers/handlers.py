from ..state_graph import app, State
from ..logging import logger

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

conversation_router = Router()


@conversation_router.message(Command("start"))
async def start_command(message: Message):
    state = State()
    checkpoint = {
        "configurable": {"thread_id": message.chat.id},
        "values": state.init_state()
    }
    try:
        result = await app.ainvoke(input={"messages": ["/start"]}, config=checkpoint)
        await message.answer(result["messages"][-1])
    except Exception as e:
        logger.error(f"Message handling error: {e}", exc_info=True)
        await message.answer("Произошла ошибка. Пожалуйста, попробуйте снова.")



@conversation_router.message()
async def handle_message(message: Message):
    try:
        checkpoint = {
            "configurable": {"thread_id": message.chat.id}
        }
        current_state = await app.aget_state(checkpoint)
       
        logger.debug(f"current_state: {current_state}")
        if not current_state:
            await message.answer("Пожалуйста, начните с команды /start")
            return
            
        updated_state = current_state.values.copy()
        updated_state["messages"].append(message.text)
        
        logger.debug(f"updated_state: {updated_state}")

        new_checkpoint = await app.aupdate_state(
            config=checkpoint,
            values={"messages": updated_state["messages"]} 
        )
        logger.debug(f"astream cycle")
        async for step in app.astream(None, new_checkpoint):
            logger.debug(f"app astream step: {step}")
            for node_name, node_data in step.items():
                if isinstance(node_data, dict) and "messages" in node_data:
                    messages = node_data["messages"]
                    if messages:
                        last_message = messages[-1]
                        logger.debug(f"Found message in node {node_name}: {last_message}")
                        await message.answer(last_message)
                        break
                
    except Exception as e:
        logger.error(f"Message handling error: {e}", exc_info=True)
        await message.answer("Ошибка обработки. Попробуйте еще раз или /start")