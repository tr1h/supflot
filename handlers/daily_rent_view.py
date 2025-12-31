# handlers/daily_rent_view.py
from aiogram import Router, types, F
from aiogram.utils.keyboard import InlineKeyboardBuilder

daily_rent_router = Router()

def register_daily_rent_view(router: Router, db):
    @router.message(F.text == "📆 Арендовать на сутки")
    async def show_daily_rent_list(msg: types.Message):
        await send_daily_rent_options(msg, db)

    @router.callback_query(F.data == "daily_rent_list")
    async def daily_rent_cb(cq: types.CallbackQuery):
        await cq.answer()
        await send_daily_rent_options(cq.message, db)

async def send_daily_rent_options(msg: types.Message, db):
    rows = await db.execute("""
        SELECT db.id, b.name, db.daily_price, db.available_quantity, db.pickup_note, db.delivery_note
        FROM daily_boards db
        JOIN boards b ON db.board_id = b.id
        WHERE db.is_active = 1 AND db.available_quantity > 0
    """, fetchall=True)

    if not rows:
        return await msg.answer("😔 Пока никто не сдаёт доски в суточную аренду.")

    text = "📆 <b>Суточная аренда досок:</b>\n\n"
    for dbid, name, price, qty, pickup, delivery in rows:
        pickup = pickup or "не указано"
        delivery = delivery or "не указано"
        text += (
            f"🛶 {name}\n"
            f"💰 {price:.0f}₽/сут, в наличии: {qty} шт.\n"
            f"🛍 Самовывоз: {pickup}\n"
            f"🚚 Доставка: {delivery}\n\n"
        )

    kb = InlineKeyboardBuilder()
    kb.button(text="🔙 Назад", callback_data="to_main_menu")
    await msg.answer(text, reply_markup=kb.as_markup(), parse_mode="HTML")
