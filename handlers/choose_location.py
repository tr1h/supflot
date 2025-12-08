from aiogram import Router, types, F
from aiogram.utils.keyboard import InlineKeyboardBuilder

choose_location_router = Router()

def register_choose_location_handlers(router: Router, db):
    @router.message(F.text == "📍 Выбрать локацию")
    async def show_locations_on_map(msg: types.Message):
        locations = await db.execute(
            "SELECT id, name, latitude, longitude FROM locations WHERE is_active = 1",
            fetchall=True
        )
        if not locations:
            return await msg.answer("❌ Локации не найдены.")

        for loc_id, name, lat, lon in locations:
            await msg.bot.send_location(
                chat_id=msg.chat.id,
                latitude=lat,
                longitude=lon
            )

            kb = InlineKeyboardBuilder()
            kb.button(text="✅ Выбрать", callback_data=f"loc_select_{loc_id}")
            await msg.answer(f"📍 <b>{name}</b>", parse_mode="HTML", reply_markup=kb.as_markup())

    @router.callback_query(F.data.startswith("loc_select_"))
    async def handle_location_choice(cq: types.CallbackQuery):
        loc_id = int(cq.data.split("_")[-1])

        row = await db.execute(
            "SELECT name FROM locations WHERE id = ?", (loc_id,), fetch="one"
        )
        if not row:
            return await cq.answer("❌ Локация не найдена", show_alert=True)

        name = row[0]
        await cq.message.answer(f"✅ Вы выбрали локацию: <b>{name}</b>", parse_mode="HTML")

        # Здесь можешь сохранить в сессию FSM, БД или продолжить процесс
        # Например:
        # await state.update_data(location_id=loc_id)

        await cq.answer()
