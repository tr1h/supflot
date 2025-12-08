from aiogram import Router, types, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from keyboards.admin import admin_menu

admin_users_router = Router()

class AdminUserState(StatesGroup):
    waiting_user_id = State()
    waiting_username = State()
    waiting_full_name = State()
    waiting_phone = State()

# 👇 Регистрируем маршруты
def register_admin_users(router: Router, db):
    router.message.register(admin_get_user_id, StateFilter(AdminUserState.waiting_user_id))
    router.message.register(admin_get_username, StateFilter(AdminUserState.waiting_username))
    router.message.register(admin_get_fullname, StateFilter(AdminUserState.waiting_full_name))
    router.message.register(admin_get_phone, StateFilter(AdminUserState.waiting_phone))

# 👇 Обработчики (временно с заглушками — не вызывают ошибку)
async def admin_get_user_id(message: types.Message, state: FSMContext):
    await message.answer("🧩 Введите username:")
    await state.set_state(AdminUserState.waiting_username)

async def admin_get_username(message: types.Message, state: FSMContext):
    await message.answer("🧩 Введите полное имя:")
    await state.set_state(AdminUserState.waiting_full_name)

async def admin_get_fullname(message: types.Message, state: FSMContext):
    await message.answer("🧩 Введите телефон:")
    await state.set_state(AdminUserState.waiting_phone)

async def admin_get_phone(message: types.Message, state: FSMContext):
    await message.answer("✅ Пользователь добавлен! (заглушка)")
    await state.clear()
