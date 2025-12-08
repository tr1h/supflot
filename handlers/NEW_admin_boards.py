# -*- coding: utf-8 -*-
import logging
from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.filters import StateFilter
from aiogram.utils.keyboard import InlineKeyboardBuilder

from keyboards.new_admin_menu import (
    BTN_BOARDS, new_admin_menu, user_main_menu
)

logger = logging.getLogger(__name__)
admin_boards_router = Router()


class BoardFSM(StatesGroup):
    add_name = State()
    add_price = State()
    add_total = State()
    add_location = State()

    edit_choose_field = State()
    edit_name = State()
    edit_price = State()
    edit_total = State()
    edit_location = State()
    toggle_active = State()

    delete_confirm = State()


async def is_admin(db, uid: int) -> bool:
    r = await db.execute("SELECT 1 FROM admins WHERE user_id=?", (uid,), fetch="one")
    return bool(r)


def boards_inline(rows):
    kb = InlineKeyboardBuilder()
    text = "<b>Доски:</b>\n"
    for bid, name, price, total, active, loc_name in rows:
        text += f"• <code>{bid}</code> — {name} ({loc_name or '—'}) {price}₽/ч, всего {total}, {'✅' if active else '🚫'}\n"
        kb.button(text=f"✏️{bid}", callback_data=f"admin_board_edit:{bid}")
        kb.button(text=f"🔄{bid}", callback_data=f"admin_board_toggle:{bid}")
        kb.button(text=f"🗑{bid}", callback_data=f"admin_board_delete:{bid}")
    kb.adjust(3)
    kb.button(text="➕ Добавить", callback_data="admin_board_add")
    kb.adjust(1)
    return text, kb.as_markup()


def register_admin_boards(router: Router, db, bot):

    @router.message(F.text == BTN_BOARDS)
    async def show_boards(msg: types.Message, state: FSMContext):
        if not await is_admin(db, msg.from_user.id):
            return await msg.answer("⛔ Нет доступа", reply_markup=user_main_menu())

        rows = await db.execute("""
            SELECT br.id, br.name, br.price, br.total, br.is_active, l.name
            FROM boards br
            LEFT JOIN locations l ON l.id = br.location_id
            ORDER BY br.id DESC
        """, fetchall=True)

        if not rows:
            kb = InlineKeyboardBuilder()
            kb.button(text="➕ Добавить", callback_data="admin_board_add")
            return await msg.answer("Досок нет.", reply_markup=new_admin_menu()) or \
                   await msg.answer("Добавить:", reply_markup=kb.as_markup())

        text, kb = boards_inline(rows)
        await msg.answer(text, parse_mode="HTML", reply_markup=new_admin_menu())
        await msg.answer("Управление досками:", reply_markup=kb)

    # ---------- ADD ----------
    @router.callback_query(F.data == "admin_board_add")
    async def b_add_start(cq: types.CallbackQuery, state: FSMContext):
        await cq.answer()
        await state.clear()
        await state.set_state(BoardFSM.add_name)
        await cq.message.answer("Введите название доски:")

    @router.message(StateFilter(BoardFSM.add_name))
    async def b_add_name(msg: types.Message, state: FSMContext):
        await state.update_data(name=msg.text.strip())
        await state.set_state(BoardFSM.add_price)
        await msg.answer("Цена ₽/час:")

    @router.message(StateFilter(BoardFSM.add_price))
    async def b_add_price(msg: types.Message, state: FSMContext):
        try:
            price = float(msg.text.replace(",", "."))
        except ValueError:
            return await msg.answer("Введите число.")
        await state.update_data(price=price)
        await state.set_state(BoardFSM.add_total)
        await msg.answer("Количество (шт.):")

    @router.message(StateFilter(BoardFSM.add_total))
    async def b_add_total(msg: types.Message, state: FSMContext):
        if not msg.text.isdigit():
            return await msg.answer("Только целое число.")
        await state.update_data(total=int(msg.text))
        # список локаций
        rows = await db.execute("SELECT id, name FROM locations ORDER BY id", fetchall=True)
        if not rows:
            return await msg.answer("Нет локаций. Добавьте локацию сначала.")
        kb = InlineKeyboardBuilder()
        for lid, name in rows:
            kb.button(text=name, callback_data=f"admin_board_loc:{lid}")
        kb.adjust(2)
        await state.set_state(BoardFSM.add_location)
        await msg.answer("Выберите локацию:", reply_markup=kb.as_markup())

    @router.callback_query(StateFilter(BoardFSM.add_location), F.data.startswith("admin_board_loc:"))
    async def b_add_location(cq: types.CallbackQuery, state: FSMContext):
        await cq.answer()
        lid = int(cq.data.split(":")[1])
        data = await state.get_data()
        await db.execute(
            "INSERT INTO boards (name, price, total, location_id, is_active) VALUES (?,?,?,?,1)",
            (data["name"], data["price"], data["total"], lid),
            commit=True
        )
        await state.clear()
        await cq.message.answer("✅ Доска добавлена.", reply_markup=new_admin_menu())

    # ---------- EDIT ----------
    @router.callback_query(F.data.startswith("admin_board_edit:"))
    async def b_edit_choose(cq: types.CallbackQuery, state: FSMContext):
        await cq.answer()
        bid = int(cq.data.split(":")[1])
        row = await db.execute(
            "SELECT id, name, price, total, location_id FROM boards WHERE id=?",
            (bid,), fetch="one"
        )
        if not row:
            return await cq.answer("Не найдено", show_alert=True)
        _, name, price, total, loc_id = row
        await state.update_data(bid=bid)

        kb = InlineKeyboardBuilder()
        kb.button(text="1 Название", callback_data="admin_board_field:name")
        kb.button(text="2 Цена",     callback_data="admin_board_field:price")
        kb.button(text="3 Кол-во",   callback_data="admin_board_field:total")
        kb.button(text="4 Локация",  callback_data="admin_board_field:loc")
        kb.adjust(2)

        text = (f"<b>ID {bid}</b>\n"
                f"Название: {name}\n"
                f"Цена: {price}₽/ч\n"
                f"Всего: {total}\n"
                f"Локация ID: {loc_id}\n\n"
                "Что изменяем?")
        await cq.message.answer(text, parse_mode="HTML", reply_markup=kb.as_markup())

    @router.callback_query(F.data.startswith("admin_board_field:"))
    async def b_field_select(cq: types.CallbackQuery, state: FSMContext):
        await cq.answer()
        field = cq.data.split(":")[1]
        mapping = {
            "name": (BoardFSM.edit_name, "Новое название:"),
            "price": (BoardFSM.edit_price, "Новая цена ₽/ч:"),
            "total": (BoardFSM.edit_total, "Новое количество:"),
            "loc": (BoardFSM.edit_location, "Выберите локацию:")
        }
        st, prompt = mapping[field]
        await state.set_state(st)

        if field == "loc":
            rows = await db.execute("SELECT id, name FROM locations", fetchall=True)
            kb = InlineKeyboardBuilder()
            for lid, name in rows:
                kb.button(text=name, callback_data=f"admin_board_setloc:{lid}")
            kb.adjust(2)
            return await cq.message.answer(prompt, reply_markup=kb.as_markup())

        await cq.message.answer(prompt)

    @router.message(StateFilter(BoardFSM.edit_name))
    async def b_edit_name(msg: types.Message, state: FSMContext):
        data = await state.get_data()
        await db.execute("UPDATE boards SET name=? WHERE id=?", (msg.text.strip(), data["bid"]), commit=True)
        await state.clear()
        await msg.answer("✅ Обновлено.", reply_markup=new_admin_menu())

    @router.message(StateFilter(BoardFSM.edit_price))
    async def b_edit_price(msg: types.Message, state: FSMContext):
        try:
            price = float(msg.text.replace(",", "."))
        except ValueError:
            return await msg.answer("Введите число.")
        data = await state.get_data()
        await db.execute("UPDATE boards SET price=? WHERE id=?", (price, data["bid"]), commit=True)
        await state.clear()
        await msg.answer("✅ Обновлено.", reply_markup=new_admin_menu())

    @router.message(StateFilter(BoardFSM.edit_total))
    async def b_edit_total(msg: types.Message, state: FSMContext):
        if not msg.text.isdigit():
            return await msg.answer("Введите целое число.")
        total = int(msg.text)
        data = await state.get_data()
        await db.execute("UPDATE boards SET total=? WHERE id=?", (total, data["bid"]), commit=True)
        await state.clear()
        await msg.answer("✅ Обновлено.", reply_markup=new_admin_menu())

    @router.callback_query(StateFilter(BoardFSM.edit_location), F.data.startswith("admin_board_setloc:"))
    async def b_edit_loc_set(cq: types.CallbackQuery, state: FSMContext):
        await cq.answer()
        lid = int(cq.data.split(":")[1])
        data = await state.get_data()
        await db.execute("UPDATE boards SET location_id=? WHERE id=?", (lid, data["bid"]), commit=True)
        await state.clear()
        await cq.message.answer("✅ Локация обновлена.", reply_markup=new_admin_menu())

    # ---------- TOGGLE ACTIVE ----------
    @router.callback_query(F.data.startswith("admin_board_toggle:"))
    async def b_toggle(cq: types.CallbackQuery):
        await cq.answer()
        bid = int(cq.data.split(":")[1])
        row = await db.execute("SELECT is_active FROM boards WHERE id=?", (bid,), fetch="one")
        if not row:
            return await cq.answer("Не найдено", show_alert=True)
        new_val = 0 if row[0] else 1
        await db.execute("UPDATE boards SET is_active=? WHERE id=?", (new_val, bid), commit=True)
        await cq.message.answer(f"Статус доски #{bid}: {'✅ активна' if new_val else '🚫 выключена'}",
                                reply_markup=new_admin_menu())

    # ---------- DELETE ----------
    @router.callback_query(F.data.startswith("admin_board_delete:"))
    async def b_delete_start(cq: types.CallbackQuery, state: FSMContext):
        await cq.answer()
        bid = int(cq.data.split(":")[1])
        name_row = await db.execute("SELECT name FROM boards WHERE id=?", (bid,), fetch="one")
        if not name_row:
            return await cq.answer("Не найдено", show_alert=True)

        await state.set_state(BoardFSM.delete_confirm)
        await state.update_data(bid=bid)

        kb = InlineKeyboardBuilder()
        kb.button(text="✅ Да, удалить", callback_data="admin_board_del_yes")
        kb.button(text="❌ Отмена",      callback_data="admin_board_del_no")
        kb.adjust(2)
        await cq.message.answer(f"Удалить доску <code>{name_row[0]}</code> (ID {bid})?",
                                parse_mode="HTML", reply_markup=kb.as_markup())

    @router.callback_query(StateFilter(BoardFSM.delete_confirm), F.data == "admin_board_del_yes")
    async def b_delete_yes(cq: types.CallbackQuery, state: FSMContext):
        await cq.answer()
        data = await state.get_data()
        await db.execute("DELETE FROM boards WHERE id=?", (data["bid"],), commit=True)
        await state.clear()
        await cq.message.answer("🗑 Доска удалена.", reply_markup=new_admin_menu())

    @router.callback_query(StateFilter(BoardFSM.delete_confirm), F.data == "admin_board_del_no")
    async def b_delete_no(cq: types.CallbackQuery, state: FSMContext):
        await cq.answer("Отменено")
        await state.clear()
        await cq.message.answer("Удаление отменено.", reply_markup=new_admin_menu())
