from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.config import BotSettings
from bot.keyboards import webapp_keyboard
from bot.messages import help_reply, shopping_text_reply, start_reply


def build_router(settings: BotSettings) -> Router:
    router = Router()

    @router.message(Command("start"))
    async def handle_start(message: Message) -> None:
        reply = start_reply(settings)
        await message.answer(reply.text, reply_markup=webapp_keyboard(reply.webapp_url))

    @router.message(Command("help"))
    async def handle_help(message: Message) -> None:
        reply = help_reply(settings)
        await message.answer(reply.text, reply_markup=webapp_keyboard(reply.webapp_url))

    @router.message(F.text)
    async def handle_text(message: Message) -> None:
        reply = shopping_text_reply(settings, message.text or "")
        await message.answer(reply.text, reply_markup=webapp_keyboard(reply.webapp_url))

    return router
