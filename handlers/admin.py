from aiogram import Router, types
from aiogram.filters import Command

from database import Database

router = Router()


def admin_only(func):
    """Декоратор для проверки админских прав."""
    async def wrapper(message: types.Message, *args, **kwargs):
        db: Database = message.bot.db
        user_id = message.from_user.id
        if not await db.is_admin(user_id):
            await message.answer("🚫 <b>Доступ запрещён. Только для администраторов.</b>", parse_mode="HTML")
            return
        return await func(message, *args, **kwargs)
    return wrapper


@router.message(Command("admin"))
@admin_only
async def cmd_admin(message: types.Message, **kwargs) -> None:
    """Главное меню админа."""
    text = (
        "👑 <b>Панель администратора</b>\n\n"
        "<b>Команды:</b>\n"
        "/users — список всех пользователей\n"
        "/ban <code>&lt;user_id&gt;</code> — забанить пользователя\n"
        "/unban <code>&lt;user_id&gt;</code> — разбанить пользователя\n"
        "/create_key [admin|user] — создать ключ доступа\n"
        "/keys — список всех ключей\n"
        "/revoke_key <code>&lt;key_id&gt;</code> — отозвать ключ\n"
        "/stats — статистика бота"
    )
    await message.answer(text, parse_mode="HTML")


@router.message(Command("users"))
@admin_only
async def cmd_users(message: types.Message, **kwargs) -> None:
    """Список всех пользователей."""
    db: Database = message.bot.db
    users = await db.list_users()

    if not users:
        await message.answer("📭 Пользователей нет.")
        return

    lines = ["👥 <b>Список пользователей:</b>\n"]
    for u in users:
        role_emoji = "👑" if u["role"] == "admin" else "👤"
        ban_emoji = " 🚫" if u["is_banned"] else ""
        username = f"@{u['username']}" if u['username'] else "без username"
        lines.append(
            f"{role_emoji} <code>{u['user_id']}</code> — {username}{ban_emoji}\n"
            f"   Роль: {u['role']} | Ключ ID: {u['access_key_id']} | Рег: {u['registered_at']}"
        )

    # Разбиваем на части если слишком длинное
    text = "\n".join(lines)
    if len(text) > 4000:
        parts = [text[i:i+4000] for i in range(0, len(text), 4000)]
        for part in parts:
            await message.answer(part, parse_mode="HTML")
    else:
        await message.answer(text, parse_mode="HTML")


@router.message(Command("ban"))
@admin_only
async def cmd_ban(message: types.Message, **kwargs) -> None:
    """Бан пользователя. /ban &lt;user_id&gt;"""
    db: Database = message.bot.db
    admin_id = message.from_user.id

    if not message.text or len(message.text.split()) < 2:
        await message.answer("Использование: <code>/ban &lt;user_id&gt;</code>", parse_mode="HTML")
        return

    try:
        target_id = int(message.text.split()[1])
    except ValueError:
        await message.answer("❌ user_id должен быть числом.", parse_mode="HTML")
        return

    if target_id == admin_id:
        await message.answer("❌ Нельзя забанить самого себя.", parse_mode="HTML")
        return

    success = await db.ban_user(admin_id, target_id)
    if success:
        await message.answer(f"✅ Пользователь <code>{target_id}</code> забанен.", parse_mode="HTML")
    else:
        await message.answer("❌ Не удалось забанить. Проверьте права или user_id.", parse_mode="HTML")


@router.message(Command("unban"))
@admin_only
async def cmd_unban(message: types.Message, **kwargs) -> None:
    """Разбан пользователя. /unban &lt;user_id&gt;"""
    db: Database = message.bot.db
    admin_id = message.from_user.id

    if not message.text or len(message.text.split()) < 2:
        await message.answer("Использование: <code>/unban &lt;user_id&gt;</code>", parse_mode="HTML")
        return

    try:
        target_id = int(message.text.split()[1])
    except ValueError:
        await message.answer("❌ user_id должен быть числом.", parse_mode="HTML")
        return

    success = await db.unban_user(admin_id, target_id)
    if success:
        await message.answer(f"✅ Пользователь <code>{target_id}</code> разбанен.", parse_mode="HTML")
    else:
        await message.answer("❌ Не удалось разбанить.", parse_mode="HTML")


@router.message(Command("create_key"))
@admin_only
async def cmd_create_key(message: types.Message, **kwargs) -> None:
    """Создание ключа. /create_key [admin|user]"""
    db: Database = message.bot.db
    admin_id = message.from_user.id

    if not message.text or len(message.text.split()) < 2:
        await message.answer(
            "Использование: <code>/create_key admin</code> или <code>/create_key user</code>",
            parse_mode="HTML"
        )
        return

    key_type = message.text.split()[1].lower()
    if key_type not in ("admin", "user"):
        await message.answer("❌ Тип должен быть: <code>admin</code> или <code>user</code>", parse_mode="HTML")
        return

    is_admin = (key_type == "admin")
    key = await db.create_access_key(is_admin, admin_id)

    role_text = "👑 <b>АДМИНСКИЙ</b>" if is_admin else "👤 <b>ПОЛЬЗОВАТЕЛЬСКИЙ</b>"
    await message.answer(
        f"✅ <b>Ключ создан!</b>\n"
        f"Тип: {role_text}\n"
        f"Ключ: <code>{key}</code>\n\n"
        f"⚠️ <b>Сохраните ключ!</b> Он показан только один раз.\n"
        f"Перешлите его пользователю для регистрации через /register",
        parse_mode="HTML"
    )


@router.message(Command("keys"))
@admin_only
async def cmd_keys(message: types.Message, **kwargs) -> None:
    """Список всех ключей."""
    db: Database = message.bot.db
    keys = await db.list_keys()

    if not keys:
        await message.answer("📭 Ключей нет.")
        return

    lines = ["🔑 <b>Список ключей доступа:</b>\n"]
    for k in keys:
        role_emoji = "👑" if k["is_admin"] else "👤"
        status = "✅" if k["is_active"] else "❌"
        lines.append(
            f"{status} {role_emoji} ID: <code>{k['id']}</code> | Префикс: <code>{k['prefix']}***</code>\n"
            f"   Создал: {k['created_by']} | Время: {k['created_at']}"
        )

    text = "\n".join(lines)
    if len(text) > 4000:
        parts = [text[i:i+4000] for i in range(0, len(text), 4000)]
        for part in parts:
            await message.answer(part, parse_mode="HTML")
    else:
        await message.answer(text, parse_mode="HTML")


@router.message(Command("revoke_key"))
@admin_only
async def cmd_revoke_key(message: types.Message, **kwargs) -> None:
    """Отозвать ключ. /revoke_key &lt;key_id&gt;"""
    db: Database = message.bot.db

    if not message.text or len(message.text.split()) < 2:
        await message.answer("Использование: <code>/revoke_key &lt;key_id&gt;</code>", parse_mode="HTML")
        return

    try:
        key_id = int(message.text.split()[1])
    except ValueError:
        await message.answer("❌ key_id должен быть числом.", parse_mode="HTML")
        return

    await db.deactivate_key(key_id)
    await message.answer(f"✅ Ключ <code>{key_id}</code> отозван.", parse_mode="HTML")


@router.message(Command("stats"))
@admin_only
async def cmd_stats(message: types.Message, **kwargs) -> None:
    """Статистика бота."""
    db: Database = message.bot.db
    users = await db.list_users()
    keys = await db.list_keys()
    alerts = await db.get_all_active_alerts()

    total_users = len(users)
    admin_count = sum(1 for u in users if u["role"] == "admin")
    user_count = sum(1 for u in users if u["role"] == "user")
    banned_count = sum(1 for u in users if u["is_banned"])
    active_keys = sum(1 for k in keys if k["is_active"])
    admin_keys = sum(1 for k in keys if k["is_admin"] and k["is_active"])

    text = (
        f"📊 <b>Статистика бота</b>\n\n"
        f"👥 Пользователей: {total_users}\n"
        f"   👑 Админов: {admin_count}\n"
        f"   👤 Пользователей: {user_count}\n"
        f"   🚫 Забанено: {banned_count}\n\n"
        f"🔑 Ключей: {len(keys)}\n"
        f"   ✅ Активных: {active_keys}\n"
        f"   👑 Админских: {admin_keys}\n\n"
        f"📈 Активных алертов: {len(alerts)}"
    )
    await message.answer(text, parse_mode="HTML")