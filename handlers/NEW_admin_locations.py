# -*- coding: utf-8 -*-
import logging
from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.filters import StateFilter
from aiogram.utils.keyboard import InlineKeyboardBuilder

from keyboards.new_admin_menu import (
    BTN_LOCATIONS, BTN_BACK, new_admin_menu, user_main_menu
)

logger = logging.getLogger(__name__)
admin_locations_router = Router()


# ---------- FSM ----------
class LocFSM(StatesGroup):
    add_name = State()
    add_address = State()
    add_lat = State()
    add_lon = State()

    edit_choose_field = State()
    edit_name = State()
    edit_address = State()
    edit_lat = State()
    edit_lon = State()

    delete_confirm = State()


# ---------- HELPERS ----------
def loc_inline_list(rows):
    kb = InlineKeyboardBuilder()
    text = "<b>Локации:</b>\n"
    for lid, name, address, active in rows:
        text += f"• <code>{lid}</code> — {name} ({'✅' if active else '🚫'})\n"
        kb.button(text=f"✏️ {lid}", callback_data=f"admin_loc_edit:{lid}")
        kb.button(text=f"🗑 {lid}", callback_data=f"admin_loc_delete:{lid}")
    kb.adjust(2)
    kb.button(text="➕ Добавить", callback_data="admin_loc_add")
    kb.adjust(2)
    return text, kb.as_markup()


async def is_admin(db, uid: int) -> bool:
    row = await db.execute("SELECT 1 FROM admins WHERE user_id = ?", (uid,), fetch="one")
    return bool(row)


# ---------- REGISTER ----------
def register_admin_locations(router: Router, db):

    # Главное меню: кнопка "📍 Локации"
    @router.message(F.text == BTN_LOCATIONS)
    async def show_locations(msg: types.Message, state: FSMContext):
        if not await is_admin(db, msg.from_user.id):
            return await msg.answer("⛔ Нет доступа", reply_markup=user_main_menu())

        rows = await db.execute(
            "SELECT id, name, COALESCE(address,'—'), is_active FROM locations ORDER BY id DESC",
            fetchall=True
        )
        if not rows:
            kb = InlineKeyboardBuilder()
            kb.button(text="➕ Добавить", callback_data="admin_loc_add")
            return await msg.answer("Локаций нет.", reply_markup=new_admin_menu(), reply_markup_inline=kb.as_markup())

        text, kb = loc_inline_list(rows)
        await msg.answer(text, parse_mode="HTML", reply_markup=new_admin_menu())
        await msg.answer("Управление локациями:", reply_markup=kb)

    # ➕ Добавить
    @router.callback_query(F.data == "admin_loc_add")
    async def add_loc_start(cq: types.CallbackQuery, state: FSMContext):
        await cq.answer()
        await state.clear()
        await state.set_state(LocFSM.add_name)
        await cq.message.answer("Введите название локации:")

    @router.message(StateFilter(LocFSM.add_name))
    async def add_loc_name(msg: types.Message, state: FSMContext):
        await state.update_data(name=msg.text.strip())
        await state.set_state(LocFSM.add_address)
        await msg.answer("Введите адрес (или - если нет):")

    @router.message(StateFilter(LocFSM.add_address))
    async def add_loc_address(msg: types.Message, state: FSMContext):
        addr = None if msg.text.strip() == "-" else msg.text.strip()
        await state.update_data(address=addr)
        await state.set_state(LocFSM.add_lat)
        await msg.answer("Введите широту (число):")

    @router.message(StateFilter(LocFSM.add_lat))
    async def add_loc_lat(msg: types.Message, state: FSMContext):
        try:
            lat = float(msg.text.replace(",", "."))
        except ValueError:
            return await msg.answer("❗ Широта должна быть числом.")
        await state.update_data(latitude=lat)
        await state.set_state(LocFSM.add_lon)
        await msg.answer("Введите долготу (число):")

    @router.message(StateFilter(LocFSM.add_lon))
    async def add_loc_lon(msg: types.Message, state: FSMContext):
        try:
            lon = float(msg.text.replace(",", "."))
        except ValueError:
            return await msg.answer("❗ Долгота должна быть числом.")

        data = await state.get_data()
        await db.execute(
            "INSERT INTO locations (name, address, latitude, longitude, is_active) VALUES (?,?,?,?,1)",
            (data["name"], data["address"], data["latitude"], lon),
            commit=True
        )
        await state.clear()
        await msg.answer("✅ Локация добавлена!", reply_markup=new_admin_menu())

    # ✏️ Редактирование
    @router.callback_query(F.data.startswith("admin_loc_edit:"))
    async def edit_loc_choose_field(cq: types.CallbackQuery, state: FSMContext):
        await cq.answer()
        loc_id = int(cq.data.split(":")[1])
        row = await db.execute(
            "SELECT id, name, COALESCE(address,'—'), latitude, longitude FROM locations WHERE id=?",
            (loc_id,), fetch="one"
        )
        if not row:
            return await cq.answer("Не найдено", show_alert=True)
        _, name, addr, lat, lon = row
        await state.update_data(loc_id=loc_id)

        kb = InlineKeyboardBuilder()
        kb.button(text="1 Название", callback_data="admin_loc_edit_field:name")
        kb.button(text="2 Адрес",    callback_data="admin_loc_edit_field:address")
        kb.button(text="3 Широта",   callback_data="admin_loc_edit_field:lat")
        kb.button(text="4 Долгота",  callback_data="admin_loc_edit_field:lon")
        kb.adjust(2)

        text = (f"<b>ID {loc_id}</b>\n"
                f"Название: {name}\n"
                f"Адрес: {addr}\n"
                f"Lat: {lat}, Lon: {lon}\n\n"
                "Что изменяем?")
        await cq.message.answer(text, parse_mode="HTML", reply_markup=kb.as_markup())

    @router.callback_query(F.data.startswith("admin_loc_edit_field:"))
    async def edit_loc_field_select(cq: types.CallbackQuery, state: FSMContext):
        await cq.answer()
        field = cq.data.split(":")[1]
        data = await state.get_data()
        if "loc_id" not in data:
            return await cq.answer("Сессия истекла", show_alert=True)

        mapping = {
            "name":   (LocFSM.edit_name,    "Введите новое название:"),
            "address":(LocFSM.edit_address, "Введите новый адрес (или -):"),
            "lat":    (LocFSM.edit_lat,     "Введите новую широту (число):"),
            "lon":    (LocFSM.edit_lon,     "Введите новую долготу (число):"),
        }
        st, prompt = mapping[field]
        await state.set_state(st)
        await cq.message.answer(prompt)

    @router.message(StateFilter(LocFSM.edit_name))
    async def edit_name(msg: types.Message, state: FSMContext):
        data = await state.get_data()
        await db.execute("UPDATE locations SET name=? WHERE id=?", (msg.text.strip(), data["loc_id"]), commit=True)
        await state.clear()
        await msg.answer("✅ Название обновлено.", reply_markup=new_admin_menu())

    @router.message(StateFilter(LocFSM.edit_address))
    async def edit_address(msg: types.Message, state: FSMContext):
        data = await state.get_data()
        addr = None if msg.text.strip() == "-" else msg.text.strip()
        await db.execute("UPDATE locations SET address=? WHERE id=?", (addr, data["loc_id"]), commit=True)
        await state.clear()
        await msg.answer("✅ Адрес обновлён.", reply_markup=new_admin_menu())

    @router.message(StateFilter(LocFSM.edit_lat))
    async def edit_lat(msg: types.Message, state: FSMContext):
        try:
            lat = float(msg.text.replace(",", "."))
        except ValueError:
            return await msg.answer("❗ Широта должна быть числом.")
        data = await state.get_data()
        await db.execute("UPDATE locations SET latitude=? WHERE id=?", (lat, data["loc_id"]), commit=True)
        await state.clear()
        await msg.answer("✅ Широта обновлена.", reply_markup=new_admin_menu())

    @router.message(StateFilter(LocFSM.edit_lon))
    async def edit_lon(msg: types.Message, state: FSMContext):
        try:
            lon = float(msg.text.replace(",", "."))
        except ValueError:
            return await msg.answer("❗ Долгота должна быть числом.")
        data = await state.get_data()
        await db.execute("UPDATE locations SET longitude=? WHERE id=?", (lon, data["loc_id"]), commit=True)
        await state.clear()
        await msg.answer("✅ Долгота обновлена.", reply_markup=new_admin_menu())

    # 🗑 Удаление
    @router.callback_query(F.data.startswith("admin_loc_delete:"))
    async def delete_loc_start(cq: types.CallbackQuery, state: FSMContext):
        await cq.answer()
        loc_id = int(cq.data.split(":")[1])
        row = await db.execute("SELECT name FROM locations WHERE id=?", (loc_id,), fetch="one")
        if not row:
            return await cq.answer("Не найдено", show_alert=True)
        await state.set_state(LocFSM.delete_confirm)
        await state.update_data(loc_id=loc_id)

        kb = InlineKeyboardBuilder()
        kb.button(text="✅ Да, удалить", callback_data="admin_loc_confirm_delete")
        kb.button(text="❌ Отмена",      callback_data="admin_loc_cancel_delete")
        kb.adjust(2)
        await cq.message.answer(f"Удалить локацию <code>{row[0]}</code> (ID {loc_id})?", parse_mode="HTML",
                                reply_markup=kb.as_markup())

    @router.callback_query(StateFilter(LocFSM.delete_confirm), F.data == "admin_loc_confirm_delete")
    async def delete_loc_confirm(cq: types.CallbackQuery, state: FSMContext):
        await cq.answer()
        data = await state.get_data()
        await db.execute("DELETE FROM locations WHERE id=?", (data["loc_id"],), commit=True)
        await state.clear()
        await cq.message.answer("🗑 Локация удалена.", reply_markup=new_admin_menu())

    @router.callback_query(StateFilter(LocFSM.delete_confirm), F.data == "admin_loc_cancel_delete")
    async def delete_loc_cancel(cq: types.CallbackQuery, state: FSMContext):
        await cq.answer("Отменено")
        await state.clear()
        await cq.message.answer("Удаление отменено.", reply_markup=new_admin_menu())
