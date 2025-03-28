from ..state_graph import app, init_state
from ..logging import logger

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
conversation_router = Router()


@conversation_router.message(Command("start"))
async def start_command(message: Message):
    checkpoint = {
        "configurable": {"thread_id": message.chat.id},
        "values": init_state()
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
       
        print("current_state",current_state)
        if not current_state:
            await message.answer("Пожалуйста, начните с команды /start")
            return
            
        updated_state = current_state.values.copy()
        updated_state["messages"].append(message.text)

        new_checkpoint = await app.aupdate_state(
            config=checkpoint,
            values={"messages": updated_state["messages"]} 
        )
        
        async for step in app.astream(None, new_checkpoint):
            if step.get("messages"):
                await message.answer(step["messages"][-1])
                break
                
    except Exception as e:
        logger.error(f"Message handling error: {e}", exc_info=True)
        await message.answer("Ошибка обработки. Попробуйте еще раз или /start")