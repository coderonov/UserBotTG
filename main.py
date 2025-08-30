import asyncio
import time
import random
import re
from telethon import TelegramClient, events, types
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.functions.photos import GetUserPhotosRequest
from telethon.tl.functions.messages import GetCommonChatsRequest
from telethon.tl.functions.contacts import GetBlockedRequest
from telethon.tl.types import DocumentAttributeAudio
from telethon.utils import get_display_name
from telethon.errors import RPCError
import os
import uuid
import yt_dlp
from urllib.parse import urlparse

API_ID = YOUR_API_ID #my.telegram.org
API_HASH = 'YOUR_API_HASH'
PHONE_NUMBER = 'YOUR PHONE NUMBER'
SESSION_NAME = 'user.session'

OWNER_ID = None
client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

active_tasks = {}
DOWNLOADS_DIR = "./downloads/"
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

async def main():
    global OWNER_ID
    await client.start(phone=PHONE_NUMBER, password=lambda: input("🔐 Введите 2FA пароль: "))
    me = await client.get_me()
    OWNER_ID = me.id

    @client.on(events.NewMessage(pattern=r'^\.stats$', outgoing=True))
    async def handler(event):
        msg = await event.edit("🔍 Начинаю сбор статистики...")
        await asyncio.sleep(1.5)
        dialogs = await client.get_dialogs(limit=None)
        total = len(dialogs)
        users = sum(1 for d in dialogs if d.is_user and not d.entity.is_self)
        bots = sum(1 for d in dialogs if d.is_user and getattr(d.entity, 'bot', False))
        groups = sum(1 for d in dialogs if d.is_group)
        channels = sum(1 for d in dialogs if d.is_channel)
        pinned = sum(1 for d in dialogs if d.pinned)

        groups_public = 0
        channels_public = 0
        for d in dialogs:
            if d.is_group and hasattr(d.entity, 'username') and d.entity.username:
                groups_public += 1
            elif d.is_channel and hasattr(d.entity, 'username') and d.entity.username:
                channels_public += 1
        groups_private = groups - groups_public
        channels_private = channels - channels_public

        user_online = sum(1 for d in dialogs if d.is_user and d.entity.status and hasattr(d.entity.status, 'online'))
        user_offline = users - user_online

        blocked = 0
        try:
            result = await client(GetBlockedRequest(offset=0, limit=1))
            blocked = result.count
        except Exception:
            blocked = "N/A"

        text = (
            "📊 **Расширенная статистика аккаунта**\n"
            "────────────────────────────\n"
            f"📬 Всего чатов: `{total}`\n"
            f"📌 Закреплено: `{pinned}`\n"
            "👤 **Личные чаты:**\n"
            f" ├─ Всего: `{users}`\n"
            f" ├─ Онлайн: `{user_online}`\n"
            f" └─ Офлайн: `{user_offline}`\n"
            f"🤖 Ботов: `{bots}`\n"
            "👥 **Группы:**\n"
            f" ├─ Всего: `{groups}`\n"
            f" ├─ Публичные: `{groups_public}`\n"
            f" └─ Приватные: `{groups_private}`\n"
            "📢 **Каналы:**\n"
            f" ├─ Всего: `{channels}`\n"
            f" ├─ Публичные: `{channels_public}`\n"
            f" └─ Приватные: `{channels_private}`\n"
            f"⛔ Заблокировано пользователей: `{blocked}`\n"
            "────────────────────────────\n"
            f"ℹ️ Завершено за `{time.time() - event.date.timestamp():.2f}` сек."
        )
        await msg.edit(text)

    @client.on(events.NewMessage(pattern=r'^\.ping$', outgoing=True))
    async def handler(event):
        start = time.time()
        await event.edit("🏓 Pong! `...`")
        ping = (time.time() - start) * 1000
        await event.edit(f"🏓 Pong! `{ping:.2f} мс`")

    @client.on(events.NewMessage(pattern=r'^\.id$', outgoing=True))
    async def handler(event):
        user = await event.get_sender()
        username = f"@{user.username}" if user.username else "нет"
        first_name = user.first_name or "Неизвестно"
        text = (
            "🆔 **Информация**\n"
            "────────────────\n"
            f"🧑‍💻 Пользователь: {first_name}\n"
            f"🔗 Юзернейм: {username}\n"
            f"🔢 ID: `{user.id}`\n"
            f"🔢 Чат ID: `{event.chat_id}`"
        )
        await event.edit(text)

    @client.on(events.NewMessage(pattern=r'^\.time$', outgoing=True))
    async def handler(event):
        t = time.strftime("%H:%M:%S %d.%m.%Y")
        await event.edit(f"🕒 Текущее время: `{t}`")

    @client.on(events.NewMessage(pattern=r'^\.help$', outgoing=True))
    async def handler(event):
        text = (
            "🤖 **Команды**\n"
            "────────────────\n"
            "`.stats` — расширенная статистика\n"
            "`.ping` — задержка\n"
            "`.id` — мой ID\n"
            "`.time` — время\n"
            "`.help` — помощь\n"
            "`.echo <текст>` — повтор\n"
            "`.delete` — удалить\n"
            "`.spam <n> <текст>` — спам\n"
            "`.spam <n> <delay> <текст>` — с задержкой\n"
            "`.love` — анимация сердца\n"
            "`.doge` — добрые слова\n"
            "`.flip` — монетка\n"
            "`.stopall` — остановить всё\n"
            "`.you` — инфа о собеседнике/чате\n"
            "`.calc <выражение>` — калькулятор\n"
            "`.random <n>` — случайное число от 1 до n\n"
            "`.info` — информация о боте\n"
            "`.clear` — очистить 5 последних сообщений\n"
            "`.quote` — цитата дня\n"
            "`.roll <n>` — бросить кубик от 1 до n\n"
            "`.online` — проверить, в сети ли собеседник\n"
            "`.bio <@ или реплай>` — показать био пользователя\n"
            "`.clown <текст>` — отправить слова по одному\n"
            "`.download <ссылка>` — скачать видео с YouTube, TikTok и других платформ"
        )
        await event.edit(text)

    @client.on(events.NewMessage(pattern=r'^\.echo (.+)$', outgoing=True))
    async def handler(event):
        text = event.pattern_match.group(1)
        await event.edit(f" {text}")

    @client.on(events.NewMessage(pattern=r'^\.delete$', outgoing=True))
    async def handler(event):
        reply = await event.get_reply_message()
        await event.delete()
        if reply:
            await reply.delete()

    @client.on(events.NewMessage(pattern=r'^\.spam (\d+) (\d+\.?\d*) (.+)$', outgoing=True))
    async def handler(event):
        task_key = f"spam_{event.chat_id}_{event.id}"
        count = min(int(event.pattern_match.group(1)), 100)
        delay = float(event.pattern_match.group(2))
        msg = event.pattern_match.group(3)
        await event.edit(f"🚀 Отправляю {count} сообщений...")
        await asyncio.sleep(1)
        active_tasks[task_key] = True
        for _ in range(count):
            if not active_tasks.get(task_key, False):
                break
            await client.send_message(event.chat_id, msg)
            await asyncio.sleep(delay)
        await event.delete()
        active_tasks.pop(task_key, None)

    @client.on(events.NewMessage(pattern=r'^\.spam (\d+) (.+)$', outgoing=True))
    async def handler(event):
        task_key = f"spam_{event.chat_id}_{event.id}"
        count = min(int(event.pattern_match.group(1)), 100)
        msg = event.pattern_match.group(2)
        await event.edit(f"🚀 Отправляю {count} сообщений...")
        await asyncio.sleep(1)
        active_tasks[task_key] = True
        for _ in range(count):
            if not active_tasks.get(task_key, False):
                break
            await client.send_message(event.chat_id, msg)
            await asyncio.sleep(0.3)
        await event.delete()
        active_tasks.pop(task_key, None)

    @client.on(events.NewMessage(pattern=r'^\.love$', outgoing=True))
    async def handler(event):
        task_key = f"love_{event.chat_id}_{event.id}"
        animation = [
            "❤", "❤️", "💗", "💖", "💞", "💕", "💘", "💓",
            "💓💗", "💗💞", "💞💕", "💕💘", "💘💓", "💓💞💗",
            "💗💕💞", "💞💘💓", "💘💗💞", "💌", "💘💘💘", "❤️‍🔥", "❤️‍🩹", "You are loved <3"
        ]
        active_tasks[task_key] = True
        for frame in animation:
            if not active_tasks.get(task_key, False):
                break
            try:
                await event.edit(f"💞 {frame}")
                await asyncio.sleep(0.4)
            except:
                break
        active_tasks.pop(task_key, None)

    @client.on(events.NewMessage(pattern=r'^\.doge$', outgoing=True))
    async def handler(event):
        task_key = f"doge_{event.chat_id}_{event.id}"
        quotes = [
            "Сегодня ты сделал мир чуточку лучше 🌼",
            "Ты — как солнце в пасмурный день 🌞",
            "Ошибаться — нормально. Продолжай идти 🛤️",
            "Ты важен. Не забывай об этом 💖",
            "Усталость — не враг, а сигнал отдохнуть 🛌",
            "Ты уже преодолел столько — вперёд! 🚀",
            "Доброта — твой суперспособность 🤍"
        ]
        active_tasks[task_key] = True
        await event.edit(f"🐶 {random.choice(quotes)}")
        await asyncio.sleep(0.1)
        active_tasks.pop(task_key, None)

    @client.on(events.NewMessage(pattern=r'^\.flip$', outgoing=True))
    async def handler(event):
        task_key = f"flip_{event.chat_id}_{event.id}"
        result = random.choice(["Орёл 🪙", "Решка 🔙"])
        active_tasks[task_key] = True
        await event.edit(f"🎲 {result}")
        await asyncio.sleep(0.1)
        active_tasks.pop(task_key, None)

    @client.on(events.NewMessage(pattern=r'^\.stopall$', outgoing=True))
    async def handler(event):
        await event.edit("🛑 Останавливаю все активные процессы...")
        for key in list(active_tasks.keys()):
            active_tasks[key] = False
        await asyncio.sleep(0.5)
        await event.edit("✅ Все активные команды остановлены.")
        await asyncio.sleep(2)
        await event.delete()

    @client.on(events.NewMessage(pattern=r'^\.calc (.+)$', outgoing=True))
    async def handler(event):
        expr = event.pattern_match.group(1).strip()
        try:
            result = eval(expr, {"__builtins__": {}}, {})
            await event.edit(f"🧮 Результат: `{result}`")
        except:
            await event.edit("❌ Ошибка вычисления")

    @client.on(events.NewMessage(pattern=r'^\.random (\d+)$', outgoing=True))
    async def handler(event):
        n = int(event.pattern_match.group(1))
        if n < 1:
            await event.edit("❌ Число должно быть больше 0")
            return
        result = random.randint(1, n)
        await event.edit(f"🎲 Случайное число от 1 до {n}: `{result}`")

    @client.on(events.NewMessage(pattern=r'^\.info$', outgoing=True))
    async def handler(event):
        text = (
            "🤖 **Информация о боте**\n"
            "────────────────────\n"
            "📝 Версия: `0.1`\n"
            "👨‍💻 Автор: `@coderonov`\n"
            "🔧 На базе: `Telethon`\n"
            "🔒 Безопасность: `высокая`\n"
            "💡 Назначение: `Юзербот для телеграм аккаунта`\n"
            "🌐 Поддержка: `ты и есть поддежрка`\n"
            "────────────────────\n"
        )
        await event.edit(text)

    @client.on(events.NewMessage(pattern=r'^\.clear$', outgoing=True))
    async def handler(event):
        messages = await client.get_messages(event.chat_id, limit=6)
        await client.delete_messages(event.chat_id, messages)
        await event.respond("🧹 Последние 5 сообщений очищены.", delete_after=2)

    @client.on(events.NewMessage(pattern=r'^\.quote$', outgoing=True))
    async def handler(event):
        quotes = [
            "«Будь тем, кем хочешь быть — ты владеешь всей вселенной.» — Платон",
            "«Делай маленькие вещи с большой любовью.» — Мать Тереза",
            "«Успех — это движение от неудачи к неудаче без потери энтузиазма.» — Черчилль",
            "«Мечтать — не вредно, особенно если действовать.» — аноним",
            "«Каждый день — новая возможность.» — аноним"
        ]
        await event.edit(f"📜 {random.choice(quotes)}")

    @client.on(events.NewMessage(pattern=r'^\.roll (\d+)$', outgoing=True))
    async def handler(event):
        n = int(event.pattern_match.group(1))
        if n < 1:
            await event.edit("❌ Число должно быть больше 0")
            return
        result = random.randint(1, n)
        await event.edit(f"🎲 Бросаю кубик (1-{n})... `{result}`")

    @client.on(events.NewMessage(pattern=r'^\.you$', outgoing=True))
    async def handler(event):
        reply = await event.get_reply_message()
        target = None
        if reply:
            target = await reply.get_sender()
        else:
            target = await event.get_chat()

        if isinstance(target, types.User):
            user = target
            full = await client(GetFullUserRequest(user))
            photo_count = (await client(GetUserPhotosRequest(user.id, offset=0, max_id=0, limit=1))).count
            username = f"@{user.username}" if user.username else "нет"
            first_name = user.first_name or "Неизвестно"
            last_name = user.last_name or ""
            full_name = f"{first_name} {last_name}".strip()
            bio = full.full_user.about or "Био отсутствует"
            phone = f"скрыт" if not user.phone else f"`{user.phone}`"
            dc = user.photo.dc_id if user.photo else "N/A"
            bot = "✅ Да" if user.bot else "❌ Нет"
            scam = "⚠️ Да" if user.scam else "❌ Нет"
            verified = "✅ Да" if user.verified else "❌ Нет"
            try:
                common_result = await client(GetCommonChatsRequest(user.id, limit=100))
                common_count = len(common_result.chats)
            except:
                common_count = "N/A"
            premium = "✅ Да" if user.premium else "❌ Нет"
            mutual = "✅ Да" if user.mutual_contact else "❌ Нет"
            fake = "⚠️ Да" if user.fake else "❌ Нет"

            text = (
                "👤 **Информация о пользователе**\n"
                "────────────────────\n"
                f"📛 Имя: **{full_name}**\n"
                f"🔗 Юзернейм: **{username}**\n"
                f"🔢 ID: `{user.id}`\n"
                f"📞 Телефон: {phone}\n"
                f"🖼️ Фото профиля: `{photo_count}` шт\n"
                f"🌍 DC: `{dc}`\n"
                f"⭐ Премиум: {premium}\n"
                f"🤖 Бот: {bot}\n"
                f"🛡️ Верифицирован: {verified}\n"
                f"🚨 Скам: {scam}\n"
                f"📛 Фейк: {fake}\n"
                f"🤝 Взаимный контакт: {mutual}\n"
                f"💬 Общие чаты: `{common_count}`\n"
                f"📝 Био:\n`{bio}`\n"
                "────────────────────\n"
                f"🔗 Ссылка: [{full_name}](tg://user?id={user.id})"
            )
            try:
                await event.delete()
                await client.send_message(event.chat_id, text, file=user.photo, link_preview=False)
            except:
                await event.reply(text)

        elif isinstance(target, types.Chat) or isinstance(target, types.Channel):
            chat = target
            full = await client(GetFullChannelRequest(chat))
            title = chat.title
            members = full.full_chat.participants_count or "N/A"
            admins = full.full_chat.admins_count or "N/A"
            kicked = full.full_chat.kicked_count or 0
            username = f"@{chat.username}" if chat.username else "нет"
            chat_type = "👥 Группа" if chat.megagroup else "📢 Канал"
            description = full.full_chat.about or "Описание отсутствует"
            dc = chat.photo.dc_id if chat.photo else "N/A"
            verified = "✅ Да" if chat.verified else "❌ Нет"
            restricted = "✅ Да" if chat.restricted else "❌ Нет"
            slowmode = "✅ Да" if getattr(full.full_chat, 'slowmode_enabled', False) else "❌ Нет"
            linked_chat = "Да" if full.full_chat.linked_chat_id else "Нет"

            text = (
                f"{chat_type} **{title}**\n"
                "────────────────────\n"
                f"📛 Название: **{title}**\n"
                f"🔗 Юзернейм: **{username}**\n"
                f"🔢 ID: `{chat.id}`\n"
                f"👥 Участников: `{members}`\n"
                f"🛡️ Администраторов: `{admins}`\n"
                f"🚷 Забанено: `{kicked}`\n"
                f"⏱️ Режим медленного чата: `{slowmode}`\n"
                f"🔗 Привязанный чат: `{linked_chat}`\n"
                f"🌍 DC: `{dc}`\n"
                f"🛡️ Верифицирован: {verified}\n"
                f"⛔ Ограничен: {restricted}\n"
                f"📝 Описание:\n`{description}`\n"
                "────────────────────\n"
                f"🔗 Ссылка: [Перейти](https://t.me/{chat.username})" if chat.username else ""
            )
            try:
                await event.delete()
                await client.send_message(event.chat_id, text, file=chat.photo, link_preview=False)
            except:
                await event.reply(text)
        else:
            await event.edit("❌ Не удалось получить информацию.")

    @client.on(events.NewMessage(pattern=r'^\.online$', outgoing=True))
    async def handler(event):
        reply = await event.get_reply_message()
        if not reply:
            await event.edit("⚠️ Ответьте на сообщение пользователя.")
            return
        user = await reply.get_sender()
        if hasattr(user.status, 'online'):
            await event.edit(f"🟢 **{get_display_name(user)}** сейчас в сети!")
        elif hasattr(user.status, 'last_seen'):
            last_seen = user.status.last_seen
            diff = (time.time() - last_seen.timestamp())
            if diff < 60:
                await event.edit(f"🟡 Был в сети {int(diff)} секунд назад.")
            elif diff < 3600:
                await event.edit(f"🟡 Был в сети {int(diff//60)} мин назад.")
            else:
                await event.edit(f"🔴 Был в сети {int(diff//3600)} ч назад.")
        else:
            await event.edit("⚪ Невозможно определить статус.")

    @client.on(events.NewMessage(pattern=r'^\.bio$', outgoing=True))
    async def handler(event):
        reply = await event.get_reply_message()
        if not reply:
            await event.edit("⚠️ Ответьте на сообщение пользователя.")
            return
        user = await reply.get_sender()
        full = await client(GetFullUserRequest(user))
        bio = full.full_user.about or "Био не установлено"
        name = get_display_name(user)
        await event.edit(f"📝 **Био {name}:**\n`{bio}`")

    @client.on(events.NewMessage(pattern=r'^\.clown (.+)$', outgoing=True))
    async def handler(event):
        text = event.pattern_match.group(1).strip()
        if not text:
            await event.edit("⚠️ Укажите текст после команды `.clown`")
            return
        words = text.split()
        await event.delete()
        for word in words:
            await client.send_message(event.chat_id, word)
            await asyncio.sleep(0.1)

    @client.on(events.NewMessage(pattern=r'^\.download (.+)$', outgoing=True))
    async def handler(event):
        url = event.pattern_match.group(1).strip()
        if not url:
            await event.edit("⚠️ Укажите ссылку после `.download`")
            return

        parsed = urlparse(url)
        if not parsed.scheme:
            await event.edit("❌ Неверная ссылка. Укажите полную ссылку (например, https://)")
            return

        await event.edit("📥 Подготавливаю загрузку...")

        ydl_opts = {
            'outtmpl': os.path.join(DOWNLOADS_DIR, '%(title)s.%(ext)s'),
            'format': 'bestvideo+bestaudio/best',
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'allow_unplayable_formats': False,
            'merge_output_format': 'mp4',
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',
            }],
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                await event.edit("🔍 Получаю информацию о видео...")
                info = ydl.extract_info(url, download=False)
                filename = ydl.prepare_filename(info)
                if info.get('duration', 0) > 3600:
                    await event.edit("❌ Видео слишком длинное (более 1 часа)")
                    return

                await event.edit(f"🎥 Загружаю: **{info['title']}**")
                ydl.download([url])

            if os.path.exists(filename):
                await event.edit(f"📤 Отправляю: `{os.path.basename(filename)}`")
                await client.send_file(
                    event.chat_id,
                    filename,
                    caption=f"📥 Загружено с: {url}",
                    supports_streaming=True
                )
                os.remove(filename)
                await event.delete()
            else:
                await event.edit("❌ Ошибка: файл не найден после загрузки")
        except Exception as e:
            await event.edit(f"❌ Ошибка загрузки: `{str(e)}`")

    print("🟢 Юзербот запущен. Используй .help для списка команд.")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
