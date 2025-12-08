from aiogram import Router, F, types
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from keyboards.admin import admin_menu

import logging
logger = logging.getLogger(__name__)
admin_locations_router = Router()

class LocationStates(StatesGroup):
    enter_name = State()
    enter_address = State()
    enter_latitude = State()
    enter_longitude = State()
    choose_edit = State()
    choose_edit_field = State()
    edit_name = State()
    edit_address = State()
    edit_lat = State()
    edit_lon = State()
    choose_delete = State()
    confirm_delete = State()

def register_admin_locations(router, db):
    # --- Добавление локации ---
    @router.message(F.text == "➕ Добавить локацию")
    async def add_location_start(message: types.Message, state: FSMContext):
        await message.answer("Введите название локации:", reply_markup=admin_menu())
        await state.set_state(LocationStates.enter_name)

    @router.message(StateFilter(LocationStates.enter_name))
    async def add_location_name(message: types.Message, state: FSMContext):
        await state.update_data(name=message.text)
        await message.answer("Введите адрес (или - если нет):", reply_markup=admin_menu())
        await state.set_state(LocationStates.enter_address)

    @router.message(StateFilter(LocationStates.enter_address))
    async def add_location_address(message: types.Message, state: FSMContext):
        await state.update_data(address=message.text)
        await message.answer("Введите широту (latitude):", reply_markup=admin_menu())
        await state.set_state(LocationStates.enter_latitude)

    @router.message(StateFilter(LocationStates.enter_latitude))
    async def add_location_latitude(message: types.Message, state: FSMContext):
        try:
            lat = float(message.text.replace(',', '.'))
        except ValueError:
            await message.answer("❗ Введите число для широты!")
            return
        await state.update_data(latitude=lat)
        await message.answer("Введите долготу (longitude):", reply_markup=admin_menu())
        await state.set_state(LocationStates.enter_longitude)

    @router.message(StateFilter(LocationStates.enter_longitude))
    async def add_location_longitude(message: types.Message, state: FSMContext):
        try:
            lon = float(message.text.replace(',', '.'))
        except ValueError:
            await message.answer("❗ Введите число для долготы!")
            return
        data = await state.get_data()
        await db.add_location(
            name=data["name"],
            address=data["address"] if data["address"] != '-' else None,
            latitude=data["latitude"],
            longitude=lon
        )
        await message.answer("✅ Локация добавлена!", reply_markup=admin_menu())
        await state.clear()

    # --- Редактирование локации ---
    @router.message(F.text == "✏️ Редактировать локацию")
    async def edit_location_start(message: types.Message, state: FSMContext):
        locations = await db.get_locations()
        if not locations:
            await message.answer("Нет локаций для редактирования.", reply_markup=admin_menu())
            return
        text = "Выберите ID локации для редактирования:\n" + "\n".join(f"{loc[0]}: {loc[1]}" for loc in locations)
        await message.answer(text, reply_markup=admin_menu())
        await state.set_state(LocationStates.choose_edit)

    @router.message(StateFilter(LocationStates.choose_edit))
    async def edit_location_choose(message: types.Message, state: FSMContext):
        if not message.text.isdigit():
            await message.answer("Введите ID локации цифрами!")
            return
        loc_id = int(message.text)
        location = await db.get_location(loc_id)
        if not location:
            await message.answer("Локация не найдена!")
            return
        await state.update_data(loc_id=loc_id)
        await message.answer(
            f"Текущее название: {location[1]}\nТекущий адрес: {location[2]}\nШирота: {location[3]}\nДолгота: {location[4]}\n\n"
            "Что хотите изменить?\n1 - Название\n2 - Адрес\n3 - Широта\n4 - Долгота",
            reply_markup=admin_menu()
        )
        await state.set_state(LocationStates.choose_edit_field)

    @router.message(StateFilter(LocationStates.choose_edit_field))
    async def edit_location_field(message: types.Message, state: FSMContext):
        if message.text.strip() == "1":
            await message.answer("Введите новое название:")
            await state.set_state(LocationStates.edit_name)
        elif message.text.strip() == "2":
            await message.answer("Введите новый адрес:")
            await state.set_state(LocationStates.edit_address)
        elif message.text.strip() == "3":
            await message.answer("Введите новую широту:")
            await state.set_state(LocationStates.edit_lat)
        elif message.text.strip() == "4":
            await message.answer("Введите новую долготу:")
            await state.set_state(LocationStates.edit_lon)
        else:
            await message.answer("Выберите только 1, 2, 3 или 4!")

    @router.message(StateFilter(LocationStates.edit_name))
    async def edit_name(message: types.Message, state: FSMContext):
        data = await state.get_data()
        await db.execute("UPDATE locations SET name = ? WHERE id = ?", (message.text, data['loc_id']), commit=True)
        await message.answer("Название обновлено!", reply_markup=admin_menu())
        await state.clear()

    @router.message(StateFilter(LocationStates.edit_address))
    async def edit_address(message: types.Message, state: FSMContext):
        data = await state.get_data()
        await db.execute("UPDATE locations SET address = ? WHERE id = ?", (message.text, data['loc_id']), commit=True)
        await message.answer("Адрес обновлен!", reply_markup=admin_menu())
        await state.clear()

    @router.message(StateFilter(LocationStates.edit_lat))
    async def edit_lat(message: types.Message, state: FSMContext):
        data = await state.get_data()
        try:
            lat = float(message.text.replace(',', '.'))
        except ValueError:
            await message.answer("Введите число для широты!")
            return
        await db.execute("UPDATE locations SET latitude = ? WHERE id = ?", (lat, data['loc_id']), commit=True)
        await message.answer("Широта обновлена!", reply_markup=admin_menu())
        await state.clear()

    @router.message(StateFilter(LocationStates.edit_lon))
    async def edit_lon(message: types.Message, state: FSMContext):
        data = await state.get_data()
        try:
            lon = float(message.text.replace(',', '.'))
        except ValueError:
            await message.answer("Введите число для долготы!")
            return
        await db.execute("UPDATE locations SET longitude = ? WHERE id = ?", (lon, data['loc_id']), commit=True)
        await message.answer("Долгота обновлена!", reply_markup=admin_menu())
        await state.clear()

    # --- Удаление локации ---
    @router.message(F.text == "🗑️ Удалить локацию")
    async def delete_location_start(message: types.Message, state: FSMContext):
        locations = await db.get_locations()
        if not locations:
            await message.answer("Нет локаций для удаления.", reply_markup=admin_menu())
            return
        text = "Выберите ID локации для удаления:\n" + "\n".join(f"{loc[0]}: {loc[1]}" for loc in locations)
        await message.answer(text, reply_markup=admin_menu())
        await state.set_state(LocationStates.choose_delete)

    @router.message(StateFilter(LocationStates.choose_delete))
    async def delete_location_confirm(message: types.Message, state: FSMContext):
        if not message.text.isdigit():
            await message.answer("Введите ID локации цифрами!")
            return
        loc_id = int(message.text)
        location = await db.get_location(loc_id)
        if not location:
            await message.answer("Локация не найдена!")
            return
        await state.update_data(loc_id=loc_id)
        await message.answer(
            f"Удалить локацию: {location[1]} (id {loc_id})?\nОтветь 'да' для подтверждения.",
            reply_markup=admin_menu()
        )
        await state.set_state(LocationStates.confirm_delete)

    @router.message(StateFilter(LocationStates.confirm_delete))
    async def delete_location_do(message: types.Message, state: FSMContext):
        if message.text.lower().strip() == "да":
            data = await state.get_data()
            await db.execute("DELETE FROM locations WHERE id = ?", (data['loc_id'],), commit=True)
            await message.answer("Локация удалена!", reply_markup=admin_menu())
        else:
            await message.answer("Удаление отменено.", reply_markup=admin_menu())
        await state.clear()

__all__ = ["register_admin_locations", "admin_locations_router"]
