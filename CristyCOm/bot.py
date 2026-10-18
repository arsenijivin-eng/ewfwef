import asyncio
import aiosqlite
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# --- НАСТРОЙКИ ---
TOKEN = "ВАШ_НОВЫЙ_ТОКЕН"  # замените на действующий
ADMIN_IDS = {7894051808, 5969266721}
DB = "bot.db"

bot = Bot(TOKEN)
dp = Dispatcher()

# --- 25 УНИКАЛЬНЫХ ТЕКСТОВ (отзывы о продукте) ---
TEXTS = [
    "CristyVPN_bot — реально мощный, 3 дня бесплатно и безлимит. Белые списки работают!",
    "Попробовал CristyVPN_bot: скорость отличная, безлимит бесплатно, белые списки в комплекте.",
    "CristyVPN_bot даёт 3 дня фри — успел оценить безлимит и белые списки. Рекомендую.",
    "Наконец-то нашёл CristyVPN_bot: бесплатно, безлимит, белые списки. Круто!",
    "CristyVPN_bot — топ за свои деньги (а точнее за ноль): 3 дня фри, безлимит, белые списки.",
    "В CristyVPN_bot понравилось: безлимит, белые списки и бесплатный пробный период 3 дня.",
    "CristyVPN_bot — самый мощный из тех, что пробовал. Белые списки и безлимит бесплатно.",
    "3 дня бесплатно в CristyVPN_bot — это реально круто. Безлимит и белые списки на месте.",
    "CristyVPN_bot: белые списки, безлимит и бесплатный старт. Что ещё нужно?",
    "Пользуюсь CristyVPN_bot — безлимит, белые списки, 3 дня фри. Всё честно.",
    "CristyVPN_bot удивил: бесплатно, безлимит, белые списки. Мощно!",
    "Советую CristyVPN_bot: 3 дня бесплатно, безлимит и белые списки. Не пожалеете.",
    "CristyVPN_bot — это безлимит, белые списки и бесплатный пробный период. Топ.",
    "Проверил CristyVPN_bot: белые списки работают, безлимит бесплатно 3 дня. Огонь.",
    "CristyVPN_bot: мощный, бесплатный старт на 3 дня, безлимит и белые списки.",
    "В CristyVPN_bot всё просто: безлимит, белые списки и 3 дня фри. Круто.",
    "CristyVPN_bot — лучший выбор: безлимит, белые списки, бесплатно 3 дня.",
    "CristyVPN_bot дарит 3 дня безлимита и белые списки. Попробуйте — не пожалеете.",
    "CristyVPN_bot: белые списки, безлимит, бесплатный пробный период. Всё как надо.",
    "CristyVPN_bot — мощь, безлимит и белые списки бесплатно на 3 дня. Рекомендую.",
    "CristyVPN_bot: безлимит, белые списки и 3 дня фри — идеальный старт.",
    "Оценил CristyVPN_bot: бесплатно, безлимит, белые списки. Всё работает.",
    "CristyVPN_bot — это круто: 3 дня бесплатно, безлимит и белые списки.",
    "CristyVPN_bot: белые списки, безлимит и бесплатный пробный период. Супер.",
    "CristyVPN_bot — самый мощный бесплатный вариант: безлимит и белые списки на 3 дня.",
]

class TaskStates(StatesGroup):
    waiting_screens = State()
    waiting_partial = State()

async def init_db():
    async with aiosqlite.connect(DB) as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            screenshots INTEGER DEFAULT 0,
            status TEXT DEFAULT 'idle'
        )""")
        await db.execute("""CREATE TABLE IF NOT EXISTS admins (user_id INTEGER PRIMARY KEY)""")
        await db.execute("""CREATE TABLE IF NOT EXISTS payouts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            count INTEGER,
            status TEXT DEFAULT 'pending'
        )""")
        for uid in ADMIN_IDS:
            await db.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (uid,))
        await db.commit()

async def is_admin(uid: int) -> bool:
    if uid in ADMIN_IDS:
        return True
    async with aiosqlite.connect(DB) as db:
        async with db.execute("SELECT 1 FROM admins WHERE user_id=?", (uid,)) as cur:
            return await cur.fetchone() is not None

@dp.message(Command("start"))
async def start(msg: Message):
    async with aiosqlite.connect(DB) as db:
        await db.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (msg.from_user.id,))
        await db.commit()
    await msg.answer("Привет! Нажми /task, чтобы получить задание.")

@dp.message(Command("task"))
async def task(msg: Message, state: FSMContext):
    await msg.answer(
        "Отправь 50 скриншотов публикаций с текстами:\n\n" +
        "\n".join(f"{i+1}. {t}" for i, t in enumerate(TEXTS))
    )
    await state.set_state(TaskStates.waiting_screens)

@dp.message(TaskStates.waiting_screens, F.photo)
async def collect_photo(msg: Message, state: FSMContext):
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE users SET screenshots = screenshots + 1 WHERE user_id=?", (msg.from_user.id,))
        await db.commit()
        async with db.execute("SELECT screenshots FROM users WHERE user_id=?", (msg.from_user.id,)) as cur:
            count = (await cur.fetchone())[0]
        if count >= 50:
            await db.execute("INSERT INTO payouts (user_id, count) VALUES (?, ?)", (msg.from_user.id, count))
            await db.commit()
            await msg.answer("Заявка создана! Ожидай проверки админом.")
            await state.clear()
        else:
            await msg.answer(f"Принято: {count}/50")

@dp.message(Command("admin"))
async def admin_panel(msg: Message):
    if not await is_admin(msg.from_user.id):
        return
    async with aiosqlite.connect(DB) as db:
        async with db.execute("SELECT id, user_id, count FROM payouts WHERE status='pending'") as cur:
            rows = await cur.fetchall()
    if not rows:
        await msg.answer("Нет заявок.")
        return
    for pid, uid, cnt in rows:
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="Выплатить 1⭐", callback_data=f"pay:{pid}:1"),
            InlineKeyboardButton(text="Частично", callback_data=f"partial:{pid}"),
            InlineKeyboardButton(text="Отказать", callback_data=f"deny:{pid}")
        ]])
        await msg.answer(f"Заявка #{pid} от {uid}, скринов: {cnt}", reply_markup=kb)

@dp.callback_query(F.data.startswith("pay:"))
async def pay(cb: CallbackQuery):
    if not await is_admin(cb.from_user.id):
        return
    _, pid, stars = cb.data.split(":")
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE payouts SET status='paid' WHERE id=?", (pid,))
        await db.commit()
        async with db.execute("SELECT user_id FROM payouts WHERE id=?", (pid,)) as cur:
            uid = (await cur.fetchone())[0]
    await cb.message.edit_text(f"Заявка #{pid} выплачена ({stars}⭐)")
    await bot.send_message(uid, f"Твоя заявка #{pid} выплачена: {stars}⭐")

@dp.callback_query(F.data.startswith("deny:"))
async def deny(cb: CallbackQuery):
    if not await is_admin(cb.from_user.id):
        return
    _, pid = cb.data.split(":")
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE payouts SET status='denied' WHERE id=?", (pid,))
        await db.commit()
        async with db.execute("SELECT user_id FROM payouts WHERE id=?", (pid,)) as cur:
            uid = (await cur.fetchone())[0]
    await cb.message.edit_text(f"Заявка #{pid} отклонена.")
    await bot.send_message(uid, f"Заявка #{pid} отклонена.")

@dp.callback_query(F.data.startswith("partial:"))
async def partial(cb: CallbackQuery, state: FSMContext):
    if not await is_admin(cb.from_user.id):
        return
    _, pid = cb.data.split(":")
    await state.update_data(pid=pid)
    await cb.message.answer(f"Введите количество звёзд для заявки #{pid}:")
    await state.set_state(TaskStates.waiting_partial)

@dp.message(TaskStates.waiting_partial)
async def partial_amount(msg: Message, state: FSMContext):
    if not await is_admin(msg.from_user.id):
        return
    try:
        stars = int(msg.text)
    except ValueError:
        await msg.answer("Введите число.")
        return
    data = await state.get_data()
    pid = data["pid"]
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE payouts SET status='partial' WHERE id=?", (pid,))
        await db.commit()
        async with db.execute("SELECT user_id FROM payouts WHERE id=?", (pid,)) as cur:
            uid = (await cur.fetchone())[0]
    await msg.answer(f"Заявка #{pid} выплачена частично: {stars}⭐")
    await bot.send_message(uid, f"Заявка #{pid} выплачена частично: {stars}⭐")
    await state.clear()

@dp.message(Command("add_admin"))
async def add_admin(msg: Message):
    if msg.from_user.id not in ADMIN_IDS:
        return
    try:
        new_id = int(msg.text.split()[1])
    except (IndexError, ValueError):
        await msg.answer("Использование: /add_admin <user_id>")
        return
    async with aiosqlite.connect(DB) as db:
        await db.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (new_id,))
        await db.commit()
    await msg.answer(f"Админ {new_id} добавлен.")

async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())