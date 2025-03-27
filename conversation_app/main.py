from .core import settings
from .logging import logger

import asyncio
from aiogram import Bot, Dispatcher

async def main() -> None:
    logger.info("Starting bot")
    bot = Bot(token=settings.get_bot_token())
    dp = Dispatcher()
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


asyncio.run(main())