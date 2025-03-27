from ..state_graph import app

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

conversation_router = Router()


@conversation_router.message(Command("start"))
async def start_handler(message: Message):
    user_id = message.from_user.id
    state = {"text": "start"}
    result = await app.ainvoke(state, {"configurable": {"thread_id": str(user_id)}})
    await message.answer(result.get("text", "Ошибка: отсутствует сообщение"))