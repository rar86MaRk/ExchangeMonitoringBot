import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery

from database import Database

logger = logging.getLogger("exchange_monitor.middlewares.access")


class AccessMiddleware(BaseMiddleware):
    """
    Middleware для проверки доступа пользователя.
    - Если пользователь не зарегистрирован — просит ввести ключ
    - Если забанен — блокирует доступ
    - Пропускает команды /start, /help, /register без проверки
    """

    # Команды, которые доступны без регистрации
    PUBLIC_COMMANDS = {"start", "help", "register"}

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        db: Database = data["bot"].db
        user_id = event.from_user.id

        # Разрешаем публичные команды
        if event.text:
            cmd = event.text.split()[0].lstrip("/").lower()
            if cmd in self.PUBLIC_COMMANDS:
                return await handler(event, data)

        # Проверяем пользователя
        user = await db.get_user(user_id)

        if not user:
            await event.answer(
                "🔒 <b>Доступ запрещён.</b>\n"
                "Введите ключ доступа командой:\n"
                "<code>/register &lt;ваш_ключ&gt;</code>\n\n"
                "Если у вас нет ключа, обратитесь к администратору.",
                parse_mode="HTML"
            )
            return

        if user["is_banned"]:
            await event.answer("🚫 Вы заблокированы. Обратитесь к администратору.")
            return

        # Добавляем пользователя в data для удобства
        data["current_user"] = user
        return await handler(event, data)