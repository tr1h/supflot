"""Обработчики партнерских функций"""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from core.database import Database
from keyboards.partner import (
    get_partner_menu, get_location_management_keyboard,
    get_board_management_keyboard, get_booking_action_keyboard, get_board_edit_keyboard,
    get_board_images_keyboard, get_reviews_menu_keyboard, get_board_management_keyboard_with_reviews
)
from keyboards.user import get_back_keyboard
from keyboards.common import get_confirm_keyboard

logger = logging.getLogger(__name__)


class PartnerStates(StatesGroup):
    """Состояния для партнерских функций"""
    adding_location_name = State()
    adding_location_address = State()
    adding_location_coords = State()
    adding_board_location = State()
    adding_board_name = State()
    adding_board_price = State()
    adding_board_description = State()
    adding_board_quantity = State()
    adding_board_total = State()
    editing_location_name = State()
    editing_location_address = State()
    editing_board_name = State()
    editing_board_price = State()
    editing_board_description = State()
    editing_board_quantity = State()
    adding_board_image = State()
    adding_employee = State()
    editing_employee_commission = State()


def register_partner_handlers(router: Router, db: Database, bot=None, notification_service=None):
    """Регистрация партнерских обработчиков"""
    
    @router.callback_query(F.data == "partner:locations")
    async def partner_locations(callback: CallbackQuery):
        """Управление локациями партнера"""
        await callback.answer()
        user_id = callback.from_user.id
        
        partner = await db.fetchone(
            "SELECT id FROM partners WHERE telegram_id = ? AND is_approved = 1",
            (user_id,)
        )
        
        if not partner:
            await callback.message.edit_text("❌ У вас нет доступа.")
            return
        
        locations = await db.fetchall(
            "SELECT * FROM locations WHERE partner_id = ? ORDER BY name",
            (partner['id'],)
        )
        
        text = "📍 <b>Мои локации</b>\n\n"
        
        if not locations:
            text += "У вас пока нет локаций.\nИспользуйте кнопку ниже, чтобы добавить."
        else:
            for loc in locations:
                status = "✅" if loc['is_active'] else "❌"
                text += f"{status} {loc['name']}\n"
                text += f"   {loc['address']}\n\n"
        
        buttons = [
            [InlineKeyboardButton(text="➕ Добавить локацию", callback_data="partner:location_add")],
        ]
        for loc in locations[:10]:
            buttons.append([InlineKeyboardButton(
                text=f"📍 {loc['name']}",
                callback_data=f"partner:location:{loc['id']}"
            )])
        buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_partner")])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        await callback.message.edit_text(text, reply_markup=keyboard)
    
    @router.callback_query(F.data == "partner:location_add")
    async def partner_location_add(callback: CallbackQuery, state: FSMContext):
        """Начало добавления локации"""
        await callback.answer()
        await state.set_state(PartnerStates.adding_location_name)
        
        text = "📍 <b>Добавление новой локации</b>\n\n"
        text += "Введите название локации:"
        await callback.message.edit_text(text, reply_markup=get_back_keyboard("partner:locations"))
    
    @router.message(PartnerStates.adding_location_name)
    async def partner_location_name(message: Message, state: FSMContext):
        """Обработка названия локации"""
        location_name = message.text.strip()
        await state.update_data(location_name=location_name)
        await state.set_state(PartnerStates.adding_location_address)
        
        text = f"📍 Название: <b>{location_name}</b>\n\n"
        text += "Введите адрес локации:"
        await message.answer(text, reply_markup=get_back_keyboard("partner:locations"))
    
    @router.message(PartnerStates.adding_location_address)
    async def partner_location_address(message: Message, state: FSMContext):
        """Обработка адреса локации"""
        address = message.text.strip()
        user_id = message.from_user.id
        
        partner = await db.fetchone(
            "SELECT id FROM partners WHERE telegram_id = ? AND is_approved = 1",
            (user_id,)
        )
        
        if not partner:
            await message.answer("❌ Ошибка доступа.")
            return
        
        data = await state.get_data()
        location_name = data.get("location_name")
        
        try:
            # Создаем локацию
            await db.execute(
                """INSERT INTO locations (name, address, partner_id, is_active)
                   VALUES (?, ?, ?, 1)""",
                (location_name, address, partner['id'])
            )
            
            text = f"✅ Локация <b>{location_name}</b> успешно добавлена!"
            await message.answer(text, reply_markup=get_back_keyboard("partner:locations"))
            await state.clear()
            
        except Exception as e:
            logger.error(f"Error adding location: {e}")
            await message.answer("❌ Ошибка при добавлении локации. Попробуйте еще раз.")
    
    @router.callback_query(F.data.startswith("partner:location:"))
    async def partner_location_detail(callback: CallbackQuery):
        """Детали локации"""
        await callback.answer()
        location_id = int(callback.data.split(":")[-1])
        
        location = await db.fetchone(
            "SELECT * FROM locations WHERE id = ?",
            (location_id,)
        )
        
        if not location:
            await callback.message.edit_text("❌ Локация не найдена.")
            return
        
        text = f"📍 <b>{location['name']}</b>\n\n"
        text += f"Адрес: {location['address']}\n"
        text += f"Статус: {'✅ Активна' if location['is_active'] else '❌ Неактивна'}\n"
        
        # Количество досок в локации
        boards_count = await db.fetchone(
            "SELECT COUNT(*) as count FROM boards WHERE location_id = ?",
            (location_id,)
        )
        text += f"\nДосок в локации: {boards_count['count']}"
        
        keyboard = get_location_management_keyboard(location_id)
        await callback.message.edit_text(text, reply_markup=keyboard)
    
    @router.callback_query(F.data.startswith("partner:location_edit:"))
    async def partner_location_edit(callback: CallbackQuery):
        """Меню редактирования локации"""
        await callback.answer()
        location_id = int(callback.data.split(":")[-1])
        
        location = await db.fetchone("SELECT * FROM locations WHERE id = ?", (location_id,))
        
        if not location:
            await callback.message.edit_text("❌ Локация не найдена.")
            return
        
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        buttons = [
            [InlineKeyboardButton(text="✏️ Название", callback_data=f"partner:location_edit_name:{location_id}")],
            [InlineKeyboardButton(text="📍 Адрес", callback_data=f"partner:location_edit_address:{location_id}")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data=f"partner:location:{location_id}")],
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        text = f"✏️ <b>Редактирование локации</b>\n\n"
        text += f"Название: {location['name']}\n"
        text += f"Адрес: {location['address']}\n\n"
        text += "Выберите, что хотите изменить:"
        
        await callback.message.edit_text(text, reply_markup=keyboard)
    
    @router.callback_query(F.data.startswith("partner:location_edit_name:"))
    async def partner_location_edit_name_start(callback: CallbackQuery, state: FSMContext):
        """Начало редактирования названия локации"""
        await callback.answer()
        location_id = int(callback.data.split(":")[-1])
        await state.set_state(PartnerStates.editing_location_name)
        await state.update_data(location_id=location_id)
        
        text = "Введите новое название локации:"
        await callback.message.edit_text(text, reply_markup=get_back_keyboard(f"partner:location_edit:{location_id}"))
    
    @router.message(PartnerStates.editing_location_name)
    async def partner_location_edit_name_input(message: Message, state: FSMContext):
        """Обработка нового названия локации"""
        new_name = message.text.strip()
        if not new_name:
            await message.answer("❌ Название не может быть пустым.")
            return
        
        data = await state.get_data()
        location_id = data.get('location_id')
        
        try:
            await db.execute("UPDATE locations SET name = ? WHERE id = ?", (new_name, location_id))
            await message.answer(f"✅ Название изменено на <b>{new_name}</b>!", reply_markup=get_back_keyboard(f"partner:location:{location_id}"))
            await state.clear()
        except Exception as e:
            logger.error(f"Error updating location name: {e}")
            await message.answer("❌ Ошибка при обновлении названия.")
    
    @router.callback_query(F.data.startswith("partner:location_edit_address:"))
    async def partner_location_edit_address_start(callback: CallbackQuery, state: FSMContext):
        """Начало редактирования адреса локации"""
        await callback.answer()
        location_id = int(callback.data.split(":")[-1])
        await state.set_state(PartnerStates.editing_location_address)
        await state.update_data(location_id=location_id)
        
        text = "Введите новый адрес локации:"
        await callback.message.edit_text(text, reply_markup=get_back_keyboard(f"partner:location_edit:{location_id}"))
    
    @router.message(PartnerStates.editing_location_address)
    async def partner_location_edit_address_input(message: Message, state: FSMContext):
        """Обработка нового адреса локации"""
        new_address = message.text.strip()
        if not new_address:
            await message.answer("❌ Адрес не может быть пустым.")
            return
        
        data = await state.get_data()
        location_id = data.get('location_id')
        
        try:
            await db.execute("UPDATE locations SET address = ? WHERE id = ?", (new_address, location_id))
            await message.answer(f"✅ Адрес изменен на <b>{new_address}</b>!", reply_markup=get_back_keyboard(f"partner:location:{location_id}"))
            await state.clear()
        except Exception as e:
            logger.error(f"Error updating location address: {e}")
            await message.answer("❌ Ошибка при обновлении адреса.")
    
    @router.callback_query(F.data.startswith("partner:location_delete:"))
    async def partner_location_delete(callback: CallbackQuery):
        """Удаление локации"""
        await callback.answer()
        location_id = int(callback.data.split(":")[-1])
        
        location = await db.fetchone("SELECT * FROM locations WHERE id = ?", (location_id,))
        
        if not location:
            await callback.message.edit_text("❌ Локация не найдена.")
            return
        
        # Проверяем, есть ли доски в этой локации
        boards_count = await db.fetchone(
            "SELECT COUNT(*) as count FROM boards WHERE location_id = ?",
            (location_id,)
        )
        
        if boards_count['count'] > 0:
            await callback.message.edit_text(
                f"❌ Нельзя удалить локацию, в которой есть доски ({boards_count['count']} шт.).\nСначала удалите или переместите доски.",
                reply_markup=get_location_management_keyboard(location_id)
            )
            return
        
        keyboard = get_confirm_keyboard(
            f"partner:location_delete_confirm:{location_id}",
            f"partner:location:{location_id}"
        )
        
        await callback.message.edit_text(
            f"⚠️ Вы уверены, что хотите удалить локацию <b>{location['name']}</b>?",
            reply_markup=keyboard
        )
    
    @router.callback_query(F.data.startswith("partner:location_delete_confirm:"))
    async def partner_location_delete_confirm(callback: CallbackQuery):
        """Подтверждение удаления локации"""
        await callback.answer()
        location_id = int(callback.data.split(":")[-1])
        
        location = await db.fetchone("SELECT name FROM locations WHERE id = ?", (location_id,))
        
        try:
            await db.execute("DELETE FROM locations WHERE id = ?", (location_id,))
            
            await callback.message.edit_text(
                f"✅ Локация <b>{location['name']}</b> удалена!",
                reply_markup=get_back_keyboard("partner:locations")
            )
        except Exception as e:
            logger.error(f"Error deleting location: {e}")
            await callback.message.edit_text("❌ Ошибка при удалении локации.")
    
    @router.callback_query(F.data == "partner:boards")
    async def partner_boards(callback: CallbackQuery):
        """Управление досками партнера"""
        await callback.answer()
        user_id = callback.from_user.id
        
        partner = await db.fetchone(
            "SELECT id FROM partners WHERE telegram_id = ? AND is_approved = 1",
            (user_id,)
        )
        
        if not partner:
            await callback.message.edit_text("❌ У вас нет доступа.")
            return
        
        boards = await db.fetchall(
            "SELECT * FROM boards WHERE partner_id = ? ORDER BY name",
            (partner['id'],)
        )
        
        text = "🏄 <b>Мои доски</b>\n\n"
        
        if not boards:
            text += "У вас пока нет досок.\nИспользуйте кнопку ниже, чтобы добавить."
        else:
            for board in boards[:10]:
                status = "✅" if board['is_active'] else "❌"
                text += f"{status} {board['name']} - {board['price']:.0f}₽/ч\n"
                text += f"   Доступно: {board['quantity']}/{board['total']}\n\n"
        
        buttons = [
            [InlineKeyboardButton(text="➕ Добавить доску", callback_data="partner:board_add")],
        ]
        for board in boards[:10]:
            buttons.append([InlineKeyboardButton(
                text=f"🏄 {board['name']}",
                callback_data=f"partner:board:{board['id']}"
            )])
        buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_partner")])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        await callback.message.edit_text(text, reply_markup=keyboard)
    
    @router.callback_query(F.data.startswith("partner:board:"))
    async def partner_board_detail(callback: CallbackQuery):
        """Детали доски"""
        await callback.answer()
        board_id = int(callback.data.split(":")[-1])
        
        board = await db.fetchone(
            "SELECT * FROM boards WHERE id = ?",
            (board_id,)
        )
        
        if not board:
            try:
                await callback.message.edit_text("❌ Доска не найдена.")
            except:
                await callback.message.answer("❌ Доска не найдена.")
            return
        
        text = f"🏄 <b>{board['name']}</b>\n\n"
        text += f"Цена: {board['price']:.0f}₽/час\n"
        text += f"Доступно: {board['quantity']}/{board['total']}\n"
        text += f"Статус: {'✅ Активна' if board['is_active'] else '❌ Неактивна'}\n"
        
        if board.get('description'):
            text += f"\nОписание: {board['description']}"
        
        # Используем клавиатуру с кнопкой отзывов
        keyboard = get_board_management_keyboard_with_reviews(board_id)
        
        # Добавляем информацию об отзывах, если есть
        from services.review_service import ReviewService
        review_service = ReviewService(db)
        avg_rating = await review_service.get_average_rating(board_id=board_id)
        review_count = await review_service.get_review_count(board_id=board_id)
        
        if avg_rating and review_count > 0:
            text += f"\n\n⭐ Рейтинг: {avg_rating:.1f}/5 ({review_count} отзывов)"
        
        # Пытаемся отредактировать текст, если не получается - отправляем новое сообщение
        try:
            await callback.message.edit_text(text, reply_markup=keyboard)
        except Exception as e:
            # Если сообщение было с фото или другим медиа, отправляем новое
            try:
                await callback.message.delete()
            except:
                pass
            await callback.message.answer(text, reply_markup=keyboard)
    
    @router.callback_query(F.data == "partner:board_add")
    async def partner_board_add_start(callback: CallbackQuery, state: FSMContext):
        """Начало добавления доски"""
        await callback.answer()
        user_id = callback.from_user.id
        
        partner = await db.fetchone(
            "SELECT id FROM partners WHERE telegram_id = ? AND is_approved = 1",
            (user_id,)
        )
        
        if not partner:
            await callback.message.edit_text("❌ У вас нет доступа.")
            return
        
        # Получаем локации партнера
        locations = await db.fetchall(
            "SELECT * FROM locations WHERE partner_id = ? AND is_active = 1 ORDER BY name",
            (partner['id'],)
        )
        
        if not locations:
            await callback.message.edit_text(
                "❌ Сначала создайте хотя бы одну локацию.",
                reply_markup=get_back_keyboard("partner:boards")
            )
            return
        
        await state.set_state(PartnerStates.adding_board_location)
        await state.update_data(partner_id=partner['id'])
        
        buttons = []
        for loc in locations:
            buttons.append([InlineKeyboardButton(
                text=f"📍 {loc['name']}",
                callback_data=f"partner:board_location:{loc['id']}"
            )])
        buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="partner:boards")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        text = "🏄 <b>Добавление новой доски</b>\n\n"
        text += "Выберите локацию для доски:"
        await callback.message.edit_text(text, reply_markup=keyboard)
    
    @router.callback_query(F.data.startswith("partner:board_location:"))
    async def partner_board_location_chosen(callback: CallbackQuery, state: FSMContext):
        """Выбор локации для доски"""
        await callback.answer()
        location_id = int(callback.data.split(":")[-1])
        await state.update_data(location_id=location_id)
        await state.set_state(PartnerStates.adding_board_name)
        
        text = "Введите название доски:"
        await callback.message.edit_text(text, reply_markup=get_back_keyboard("partner:board_add"))
    
    @router.message(PartnerStates.adding_board_name)
    async def partner_board_name_input(message: Message, state: FSMContext):
        """Обработка названия доски"""
        board_name = message.text.strip()
        if not board_name:
            await message.answer("❌ Название не может быть пустым.")
            return
        
        await state.update_data(board_name=board_name)
        await state.set_state(PartnerStates.adding_board_price)
        
        text = f"Название: <b>{board_name}</b>\n\n"
        text += "Введите цену за час (в рублях, например: 500):"
        await message.answer(text, reply_markup=get_back_keyboard("partner:board_add"))
    
    @router.message(PartnerStates.adding_board_price)
    async def partner_board_price_input(message: Message, state: FSMContext):
        """Обработка цены доски"""
        try:
            price = float(message.text.replace(',', '.'))
            if price <= 0:
                await message.answer("❌ Цена должна быть больше нуля.")
                return
        except ValueError:
            await message.answer("❌ Неверный формат. Введите число (например: 500)")
            return
        
        await state.update_data(price=price)
        await state.set_state(PartnerStates.adding_board_quantity)
        
        data = await state.get_data()
        board_name = data.get('board_name')
        
        text = f"Название: <b>{board_name}</b>\n"
        text += f"Цена: <b>{price:.0f}₽/час</b>\n\n"
        text += "Введите общее количество досок (например: 5):"
        await message.answer(text, reply_markup=get_back_keyboard("partner:board_add"))
    
    @router.message(PartnerStates.adding_board_quantity)
    async def partner_board_quantity_input(message: Message, state: FSMContext):
        """Обработка количества досок"""
        try:
            total = int(message.text)
            if total <= 0:
                await message.answer("❌ Количество должно быть больше нуля.")
                return
        except ValueError:
            await message.answer("❌ Неверный формат. Введите целое число (например: 5)")
            return
        
        await state.update_data(total=total, quantity=total)
        await state.set_state(PartnerStates.adding_board_description)
        
        data = await state.get_data()
        board_name = data.get('board_name')
        price = data.get('price')
        
        text = f"Название: <b>{board_name}</b>\n"
        text += f"Цена: <b>{price:.0f}₽/час</b>\n"
        text += f"Количество: <b>{total}</b>\n\n"
        text += "Введите описание доски (или отправьте '-' чтобы пропустить):"
        await message.answer(text, reply_markup=get_back_keyboard("partner:board_add"))
    
    @router.message(PartnerStates.adding_board_description)
    async def partner_board_description_input(message: Message, state: FSMContext):
        """Обработка описания доски и создание"""
        user_description = message.text.strip()
        description = user_description if user_description != '-' else None
        
        data = await state.get_data()
        partner_id = data.get('partner_id')
        location_id = data.get('location_id')
        board_name = data.get('board_name')
        price = data.get('price')
        total = data.get('total')
        quantity = data.get('quantity')
        
        # Если описание не указано, пытаемся сгенерировать через AI
        if not description:
            try:
                from services.ai_service import get_ai_service
                ai_service = get_ai_service()
                if ai_service.enabled:
                    generating_msg = await message.answer("🤖 Генерирую описание через AI...")
                    ai_description = await ai_service.generate_board_description(
                        board_name=board_name,
                        price=price
                    )
                    if ai_description:
                        description = ai_description
                        await generating_msg.edit_text(f"✅ Сгенерировано описание:\n\n<i>{description}</i>\n\nПродолжаю создание доски...")
                    else:
                        await generating_msg.delete()
            except Exception as e:
                logger.error(f"Error generating AI description: {e}")
                # Продолжаем без описания
        
        try:
            await db.execute(
                """INSERT INTO boards (name, description, price, total, quantity, partner_id, location_id, is_active)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 1)""",
                (board_name, description, price, total, quantity, partner_id, location_id)
            )
            
            text = f"✅ Доска <b>{board_name}</b> успешно добавлена!"
            if description and user_description == '-':
                text += f"\n\n📝 <i>Описание сгенерировано автоматически</i>"
            await message.answer(text, reply_markup=get_back_keyboard("partner:boards"))
            await state.clear()
            
        except Exception as e:
            logger.error(f"Error adding board: {e}")
            await message.answer("❌ Ошибка при добавлении доски. Попробуйте еще раз.")
    
    @router.callback_query(F.data.startswith("partner:board_delete:"))
    async def partner_board_delete(callback: CallbackQuery):
        """Удаление доски"""
        await callback.answer()
        board_id = int(callback.data.split(":")[-1])
        
        board = await db.fetchone("SELECT * FROM boards WHERE id = ?", (board_id,))
        
        if not board:
            await callback.message.edit_text("❌ Доска не найдена.")
            return
        
        keyboard = get_confirm_keyboard(
            f"partner:board_delete_confirm:{board_id}",
            f"partner:board:{board_id}"
        )
        
        await callback.message.edit_text(
            f"⚠️ Вы уверены, что хотите удалить доску <b>{board['name']}</b>?",
            reply_markup=keyboard
        )
    
    @router.callback_query(F.data.startswith("partner:board_delete_confirm:"))
    async def partner_board_delete_confirm(callback: CallbackQuery):
        """Подтверждение удаления доски"""
        await callback.answer()
        board_id = int(callback.data.split(":")[-1])
        
        board = await db.fetchone("SELECT name FROM boards WHERE id = ?", (board_id,))
        
        try:
            await db.execute("DELETE FROM boards WHERE id = ?", (board_id,))
            
            await callback.message.edit_text(
                f"✅ Доска <b>{board['name']}</b> удалена!",
                reply_markup=get_back_keyboard("partner:boards")
            )
        except Exception as e:
            logger.error(f"Error deleting board: {e}")
            await callback.message.edit_text("❌ Ошибка при удалении доски.")
    
    @router.callback_query(F.data.startswith("partner:board_images:"))
    async def partner_board_images(callback: CallbackQuery):
        """Управление фото доски"""
        await callback.answer()
        board_id = int(callback.data.split(":")[-1])
        
        user_id = callback.from_user.id
        partner = await db.fetchone(
            "SELECT id FROM partners WHERE telegram_id = ? AND is_approved = 1",
            (user_id,)
        )
        
        if not partner:
            await callback.message.edit_text("❌ У вас нет доступа.")
            return
        
        board = await db.fetchone("SELECT * FROM boards WHERE id = ? AND partner_id = ?", (board_id, partner['id']))
        if not board:
            await callback.message.edit_text("❌ Доска не найдена.")
            return
        
        # Получаем фото доски
        images = await db.fetchall(
            "SELECT * FROM board_images WHERE board_id = ? ORDER BY created_at",
            (board_id,)
        )
        
        text = f"🖼️ <b>Фото доски: {board['name']}</b>\n\n"
        
        if images:
            text += f"Всего фото: {len(images)}\n\n"
            text += "📸 <b>Загруженные фото:</b>\n"
            for img in images:
                text += f"• Фото #{img['id']}\n"
        else:
            text += "У этой доски пока нет фото.\n"
            text += "Вы можете добавить фото, отправив изображение."
        
        keyboard = get_board_images_keyboard(board_id, len(images))
        
        # Если есть фото, отправляем первое фото
        if images and bot:
            try:
                # Удаляем предыдущее сообщение, если это возможно
                try:
                    await callback.message.delete()
                except:
                    pass
                
                await bot.send_photo(
                    chat_id=callback.from_user.id,
                    photo=images[0]['file_id'],
                    caption=text,
                    reply_markup=keyboard
                )
            except Exception as e:
                logger.error(f"Error sending photo: {e}")
                try:
                    await callback.message.edit_text(text, reply_markup=keyboard)
                except:
                    try:
                        await callback.message.delete()
                    except:
                        pass
                    await callback.message.answer(text, reply_markup=keyboard)
        else:
            try:
                await callback.message.edit_text(text, reply_markup=keyboard)
            except:
                try:
                    await callback.message.delete()
                except:
                    pass
                await callback.message.answer(text, reply_markup=keyboard)
    
    @router.callback_query(F.data.startswith("partner:board_image_add:"))
    async def partner_board_image_add_start(callback: CallbackQuery, state: FSMContext):
        """Начало добавления фото"""
        await callback.answer()
        board_id = int(callback.data.split(":")[-1])
        
        user_id = callback.from_user.id
        partner = await db.fetchone(
            "SELECT id FROM partners WHERE telegram_id = ? AND is_approved = 1",
            (user_id,)
        )
        
        if not partner:
            try:
                await callback.message.edit_text("❌ У вас нет доступа.")
            except:
                await callback.message.answer("❌ У вас нет доступа.")
            return
        
        board = await db.fetchone("SELECT * FROM boards WHERE id = ? AND partner_id = ?", (board_id, partner['id']))
        if not board:
            try:
                await callback.message.edit_text("❌ Доска не найдена.")
            except:
                await callback.message.answer("❌ Доска не найдена.")
            return
        
        await state.set_state(PartnerStates.adding_board_image)
        await state.update_data(board_id=board_id)
        
        text = "📸 <b>Добавление фото</b>\n\n"
        text += f"Доска: {board['name']}\n\n"
        text += "Отправьте фото для этой доски.\n"
        text += "Можно отправить несколько фото по одному.\n\n"
        text += "Для отмены нажмите кнопку ниже."
        
        keyboard = get_back_keyboard(f"partner:board_images:{board_id}")
        try:
            await callback.message.edit_text(text, reply_markup=keyboard)
        except:
            try:
                await callback.message.delete()
            except:
                pass
            await callback.message.answer(text, reply_markup=keyboard)
    
    @router.message(F.photo, PartnerStates.adding_board_image)
    async def partner_board_image_add_photo(message: Message, state: FSMContext):
        """Обработка загруженного фото"""
        data = await state.get_data()
        board_id = data.get('board_id')
        
        if not board_id:
            await message.answer("❌ Ошибка: не найдена доска. Попробуйте начать заново.")
            await state.clear()
            return
        
        # Берем самое большое фото
        photo = message.photo[-1]
        file_id = photo.file_id
        
        try:
            await db.execute(
                "INSERT INTO board_images (board_id, file_id) VALUES (?, ?)",
                (board_id, file_id)
            )
            
            board = await db.fetchone("SELECT name FROM boards WHERE id = ?", (board_id,))
            await message.answer(f"✅ Фото добавлено для доски <b>{board['name']}</b>!\n\nМожете добавить еще фото или нажать 'Назад'.")
        except Exception as e:
            logger.error(f"Error adding board image: {e}")
            await message.answer("❌ Ошибка при добавлении фото.")
    
    @router.callback_query(F.data.startswith("partner:board_image_delete:"))
    async def partner_board_image_delete(callback: CallbackQuery):
        """Удаление фото доски"""
        await callback.answer()
        board_id = int(callback.data.split(":")[-1])
        
        user_id = callback.from_user.id
        partner = await db.fetchone(
            "SELECT id FROM partners WHERE telegram_id = ? AND is_approved = 1",
            (user_id,)
        )
        
        if not partner:
            try:
                await callback.message.edit_text("❌ У вас нет доступа.")
            except:
                await callback.message.answer("❌ У вас нет доступа.")
            return
        
        board = await db.fetchone("SELECT * FROM boards WHERE id = ? AND partner_id = ?", (board_id, partner['id']))
        if not board:
            try:
                await callback.message.edit_text("❌ Доска не найдена.")
            except:
                await callback.message.answer("❌ Доска не найдена.")
            return
        
        # Получаем все фото
        images = await db.fetchall(
            "SELECT * FROM board_images WHERE board_id = ? ORDER BY created_at",
            (board_id,)
        )
        
        if not images:
            text = "❌ У этой доски нет фото."
            keyboard = get_back_keyboard(f"partner:board_images:{board_id}")
            try:
                await callback.message.edit_text(text, reply_markup=keyboard)
            except:
                try:
                    await callback.message.delete()
                except:
                    pass
                await callback.message.answer(text, reply_markup=keyboard)
            return
        
        # Создаем кнопки для выбора фото
        buttons = []
        for img in images:
            buttons.append([InlineKeyboardButton(
                text=f"🗑️ Удалить фото #{img['id']}",
                callback_data=f"partner:board_image_delete_confirm:{img['id']}"
            )])
        buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data=f"partner:board_images:{board_id}")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        text = f"🗑️ <b>Удаление фото</b>\n\n"
        text += f"Доска: {board['name']}\n"
        text += f"Всего фото: {len(images)}\n\n"
        text += "Выберите фото для удаления:"
        
        try:
            await callback.message.edit_text(text, reply_markup=keyboard)
        except:
            try:
                await callback.message.delete()
            except:
                pass
            await callback.message.answer(text, reply_markup=keyboard)
    
    @router.callback_query(F.data.startswith("partner:board_image_delete_confirm:"))
    async def partner_board_image_delete_confirm(callback: CallbackQuery):
        """Подтверждение удаления фото"""
        await callback.answer()
        image_id = int(callback.data.split(":")[-1])
        
        # Получаем информацию о фото для получения board_id
        image = await db.fetchone("SELECT board_id FROM board_images WHERE id = ?", (image_id,))
        if not image:
            try:
                await callback.message.edit_text("❌ Фото не найдено.")
            except:
                await callback.message.answer("❌ Фото не найдено.")
            return
        
        board_id = image['board_id']
        
        try:
            await db.execute("DELETE FROM board_images WHERE id = ?", (image_id,))
            
            board = await db.fetchone("SELECT name FROM boards WHERE id = ?", (board_id,))
            text = f"✅ Фото удалено для доски <b>{board['name']}</b>!"
            keyboard = get_back_keyboard(f"partner:board_images:{board_id}")
            
            try:
                await callback.message.edit_text(text, reply_markup=keyboard)
            except:
                try:
                    await callback.message.delete()
                except:
                    pass
                await callback.message.answer(text, reply_markup=keyboard)
        except Exception as e:
            logger.error(f"Error deleting board image: {e}")
            try:
                await callback.message.edit_text("❌ Ошибка при удалении фото.")
            except:
                await callback.message.answer("❌ Ошибка при удалении фото.")
    
    @router.callback_query(F.data.startswith("partner:board_edit:"))
    async def partner_board_edit(callback: CallbackQuery):
        """Меню редактирования доски"""
        await callback.answer()
        board_id = int(callback.data.split(":")[-1])
        
        board = await db.fetchone("SELECT * FROM boards WHERE id = ?", (board_id,))
        
        if not board:
            await callback.message.edit_text("❌ Доска не найдена.")
            return
        
        text = f"✏️ <b>Редактирование доски</b>\n\n"
        text += f"Название: {board['name']}\n"
        text += f"Цена: {board['price']:.0f}₽/час\n"
        text += f"Количество: {board['quantity']}/{board['total']}\n\n"
        text += "Выберите, что хотите изменить:"
        
        keyboard = get_board_edit_keyboard(board_id)
        await callback.message.edit_text(text, reply_markup=keyboard)
    
    @router.callback_query(F.data.startswith("partner:board_edit_name:"))
    async def partner_board_edit_name_start(callback: CallbackQuery, state: FSMContext):
        """Начало редактирования названия"""
        await callback.answer()
        board_id = int(callback.data.split(":")[-1])
        await state.set_state(PartnerStates.editing_board_name)
        await state.update_data(board_id=board_id)
        
        text = "Введите новое название доски:"
        await callback.message.edit_text(text, reply_markup=get_back_keyboard(f"partner:board_edit:{board_id}"))
    
    @router.message(PartnerStates.editing_board_name)
    async def partner_board_edit_name_input(message: Message, state: FSMContext):
        """Обработка нового названия"""
        new_name = message.text.strip()
        if not new_name:
            await message.answer("❌ Название не может быть пустым.")
            return
        
        data = await state.get_data()
        board_id = data.get('board_id')
        
        try:
            await db.execute("UPDATE boards SET name = ? WHERE id = ?", (new_name, board_id))
            await message.answer(f"✅ Название изменено на <b>{new_name}</b>!", reply_markup=get_back_keyboard(f"partner:board:{board_id}"))
            await state.clear()
        except Exception as e:
            logger.error(f"Error updating board name: {e}")
            await message.answer("❌ Ошибка при обновлении названия.")
    
    @router.callback_query(F.data.startswith("partner:board_edit_price:"))
    async def partner_board_edit_price_start(callback: CallbackQuery, state: FSMContext):
        """Начало редактирования цены"""
        await callback.answer()
        board_id = int(callback.data.split(":")[-1])
        await state.set_state(PartnerStates.editing_board_price)
        await state.update_data(board_id=board_id)
        
        text = "Введите новую цену за час (в рублях, например: 500):"
        await callback.message.edit_text(text, reply_markup=get_back_keyboard(f"partner:board_edit:{board_id}"))
    
    @router.message(PartnerStates.editing_board_price)
    async def partner_board_edit_price_input(message: Message, state: FSMContext):
        """Обработка новой цены"""
        try:
            new_price = float(message.text.replace(',', '.'))
            if new_price <= 0:
                await message.answer("❌ Цена должна быть больше нуля.")
                return
        except ValueError:
            await message.answer("❌ Неверный формат. Введите число (например: 500)")
            return
        
        data = await state.get_data()
        board_id = data.get('board_id')
        
        try:
            await db.execute("UPDATE boards SET price = ? WHERE id = ?", (new_price, board_id))
            await message.answer(f"✅ Цена изменена на <b>{new_price:.0f}₽/час</b>!", reply_markup=get_back_keyboard(f"partner:board:{board_id}"))
            await state.clear()
        except Exception as e:
            logger.error(f"Error updating board price: {e}")
            await message.answer("❌ Ошибка при обновлении цены.")
    
    @router.callback_query(F.data.startswith("partner:board_edit_description:"))
    async def partner_board_edit_description_start(callback: CallbackQuery, state: FSMContext):
        """Начало редактирования описания"""
        await callback.answer()
        board_id = int(callback.data.split(":")[-1])
        await state.set_state(PartnerStates.editing_board_description)
        await state.update_data(board_id=board_id)
        
        text = "Введите новое описание доски (или отправьте '-' чтобы убрать описание):"
        await callback.message.edit_text(text, reply_markup=get_back_keyboard(f"partner:board_edit:{board_id}"))
    
    @router.message(PartnerStates.editing_board_description)
    async def partner_board_edit_description_input(message: Message, state: FSMContext):
        """Обработка нового описания"""
        new_description = message.text.strip() if message.text.strip() != '-' else None
        
        data = await state.get_data()
        board_id = data.get('board_id')
        
        try:
            await db.execute("UPDATE boards SET description = ? WHERE id = ?", (new_description, board_id))
            text = "✅ Описание обновлено!" if new_description else "✅ Описание удалено!"
            await message.answer(text, reply_markup=get_back_keyboard(f"partner:board:{board_id}"))
            await state.clear()
        except Exception as e:
            logger.error(f"Error updating board description: {e}")
            await message.answer("❌ Ошибка при обновлении описания.")
    
    @router.callback_query(F.data.startswith("partner:board_edit_quantity:"))
    async def partner_board_edit_quantity_start(callback: CallbackQuery, state: FSMContext):
        """Начало редактирования количества"""
        await callback.answer()
        board_id = int(callback.data.split(":")[-1])
        await state.set_state(PartnerStates.editing_board_quantity)
        await state.update_data(board_id=board_id)
        
        board = await db.fetchone("SELECT quantity, total FROM boards WHERE id = ?", (board_id,))
        
        text = f"Текущее количество: {board['quantity']}/{board['total']}\n\n"
        text += "Введите новое общее количество досок (доступное количество будет равно общему):"
        await callback.message.edit_text(text, reply_markup=get_back_keyboard(f"partner:board_edit:{board_id}"))
    
    @router.message(PartnerStates.editing_board_quantity)
    async def partner_board_edit_quantity_input(message: Message, state: FSMContext):
        """Обработка нового количества"""
        try:
            new_total = int(message.text)
            if new_total <= 0:
                await message.answer("❌ Количество должно быть больше нуля.")
                return
        except ValueError:
            await message.answer("❌ Неверный формат. Введите целое число (например: 5)")
            return
        
        data = await state.get_data()
        board_id = data.get('board_id')
        
        try:
            await db.execute(
                "UPDATE boards SET total = ?, quantity = ? WHERE id = ?",
                (new_total, new_total, board_id)
            )
            await message.answer(f"✅ Количество изменено на <b>{new_total}</b>!", reply_markup=get_back_keyboard(f"partner:board:{board_id}"))
            await state.clear()
        except Exception as e:
            logger.error(f"Error updating board quantity: {e}")
            await message.answer("❌ Ошибка при обновлении количества.")
    
    @router.callback_query(F.data == "partner:bookings")
    async def partner_bookings(callback: CallbackQuery):
        """Бронирования партнера"""
        await callback.answer()
        user_id = callback.from_user.id
        
        partner = await db.fetchone(
            "SELECT id FROM partners WHERE telegram_id = ? AND is_approved = 1",
            (user_id,)
        )
        
        if not partner:
            await callback.message.edit_text("❌ У вас нет доступа.")
            return
        
        bookings = await db.fetchall(
            """SELECT * FROM bookings 
               WHERE partner_id = ? 
               ORDER BY date DESC, start_time DESC
               LIMIT 20""",
            (partner['id'],)
        )
        
        text = "📋 <b>Бронирования</b>\n\n"
        
        if not bookings:
            text += "У вас пока нет бронирований."
        else:
            status_counts = {}
            for booking in bookings:
                status = booking['status']
                status_counts[status] = status_counts.get(status, 0) + 1
            
            text += "Статистика:\n"
            for status, count in status_counts.items():
                text += f"  {status}: {count}\n"
            text += "\nПоследние бронирования:\n\n"
            
            for booking in bookings[:5]:
                text += f"#{booking['id']} - {booking['board_name']}\n"
                text += f"📅 {booking['date']} в {booking['start_time']}:{booking['start_minute']:02d}\n"
                text += f"💰 {booking['amount']:.2f}₽\n\n"
        
        buttons = []
        for booking in bookings[:10]:
            status_icon = "⏳" if booking['status'] == "waiting_partner" else "✅"
            buttons.append([InlineKeyboardButton(
                text=f"{status_icon} #{booking['id']} - {booking['board_name']}",
                callback_data=f"partner:booking:{booking['id']}"
            )])
        buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_partner")])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        await callback.message.edit_text(text, reply_markup=keyboard)
    
    @router.callback_query(F.data.startswith("partner:booking:"))
    async def partner_booking_detail(callback: CallbackQuery):
        """Детали бронирования для партнера"""
        await callback.answer()
        booking_id = int(callback.data.split(":")[-1])
        
        booking = await db.fetchone(
            "SELECT * FROM bookings WHERE id = ?",
            (booking_id,)
        )
        
        if not booking:
            await callback.message.edit_text("❌ Бронирование не найдено.")
            return
        
        user = await db.fetchone(
            "SELECT * FROM users WHERE id = ?",
            (booking['user_id'],)
        )
        
        text = f"📋 <b>Бронирование #{booking_id}</b>\n\n"
        text += f"Доска: {booking['board_name']}\n"
        text += f"Дата: {booking['date']}\n"
        text += f"Время: {booking['start_time']}:{booking['start_minute']:02d}\n"
        text += f"Длительность: {booking['duration']} мин\n"
        text += f"Количество: {booking['quantity']} шт.\n"
        text += f"Сумма: {booking['amount']:.2f}₽\n"
        text += f"Статус: {booking['status']}\n\n"
        
        if user:
            text += f"Пользователь: {user.get('full_name', 'Не указано')}\n"
            if user.get('phone'):
                text += f"Телефон: {user['phone']}\n"
        
        keyboard = get_booking_action_keyboard(booking_id)
        await callback.message.edit_text(text, reply_markup=keyboard)
    
    @router.callback_query(F.data.startswith("partner:booking_confirm:"))
    async def partner_booking_confirm(callback: CallbackQuery):
        """Подтверждение бронирования партнером"""
        await callback.answer()
        booking_id = int(callback.data.split(":")[-1])
        
        try:
            await db.execute(
                "UPDATE bookings SET status = 'active' WHERE id = ?",
                (booking_id,)
            )
            
            booking = await db.fetchone(
                "SELECT * FROM bookings WHERE id = ?",
                (booking_id,)
            )
            
            text = f"✅ Бронирование #{booking_id} подтверждено!"
            await callback.message.edit_text(text, reply_markup=get_back_keyboard("partner:bookings"))
            
            # Отправляем уведомление пользователю
            if notification_service:
                try:
                    await notification_service.notify_user_booking_confirmed(booking['user_id'], booking_id)
                except Exception as e:
                    logger.error(f"Error sending notification to user: {e}")
            
        except Exception as e:
            logger.error(f"Error confirming booking: {e}")
            await callback.message.edit_text("❌ Ошибка при подтверждении бронирования.")
    
    @router.callback_query(F.data.startswith("partner:booking_complete:"))
    async def partner_booking_complete(callback: CallbackQuery):
        """Завершение бронирования партнером"""
        await callback.answer()
        booking_id = int(callback.data.split(":")[-1])
        
        try:
            await db.execute(
                "UPDATE bookings SET status = 'completed' WHERE id = ?",
                (booking_id,)
            )
            
            text = f"✅ Бронирование #{booking_id} завершено!"
            await callback.message.edit_text(text, reply_markup=get_back_keyboard("partner:bookings"))
            
            # Начисляем средства партнеру (если не Telegram Pay)
            if booking.get('payment_method') != 'telegram' and booking.get('partner_id'):
                try:
                    from config import Config
                    partner_id = booking['partner_id']
                    amount = booking['amount']
                    
                    # Получаем комиссию платформы
                    platform_commission = Config.PLATFORM_COMMISSION_PERCENT
                    partner_amount = amount * (1 - platform_commission / 100)
                    
                    # Если есть сотрудник, вычитаем его комиссию
                    if booking.get('employee_id'):
                        employee = await db.fetchone(
                            "SELECT commission_percent FROM employees WHERE id = ?",
                            (booking['employee_id'],)
                        )
                        if employee:
                            employee_commission = employee['commission_percent']
                            employee_amount = partner_amount * (employee_commission / 100)
                            partner_amount -= employee_amount
                            
                            # Начисляем сотруднику
                            await db.execute(
                                """INSERT INTO partner_wallet_ops (partner_id, type, amount, src, booking_id)
                                   VALUES (?, 'credit', ?, ?, ?)""",
                                (booking['employee_id'], employee_amount, f"Комиссия за бронирование #{booking_id}", booking_id)
                            )
                    
                    # Начисляем партнеру
                    await db.execute(
                        """INSERT INTO partner_wallet_ops (partner_id, type, amount, src, booking_id)
                           VALUES (?, 'credit', ?, ?, ?)""",
                        (partner_id, partner_amount, f"Бронирование #{booking_id}", booking_id)
                    )
                    
                    logger.info(f"Credited {partner_amount:.2f} to partner {partner_id} for booking {booking_id}")
                except Exception as e:
                    logger.error(f"Error crediting partner wallet: {e}")
            
        except Exception as e:
            logger.error(f"Error completing booking: {e}")
            await callback.message.edit_text("❌ Ошибка при завершении бронирования.")
    
    @router.callback_query(F.data.startswith("partner:booking_cancel:"))
    async def partner_booking_cancel(callback: CallbackQuery):
        """Отмена бронирования партнером"""
        await callback.answer()
        booking_id = int(callback.data.split(":")[-1])
        
        booking = await db.fetchone(
            "SELECT * FROM bookings WHERE id = ?",
            (booking_id,)
        )
        
        if not booking:
            await callback.message.edit_text("❌ Бронирование не найдено.")
            return
        
        # Проверяем статус - можно отменять только ожидающие или активные бронирования
        if booking['status'] not in ['waiting_partner', 'active', 'waiting_card', 'waiting_cash']:
            await callback.message.edit_text(
                f"❌ Нельзя отменить бронирование со статусом: {booking['status']}",
                reply_markup=get_back_keyboard(f"partner:booking:{booking_id}")
            )
            return
        
        keyboard = get_confirm_keyboard(
            f"partner:booking_cancel_confirm:{booking_id}",
            f"partner:booking:{booking_id}"
        )
        
        await callback.message.edit_text(
            f"⚠️ Вы уверены, что хотите отменить бронирование #{booking_id}?\n\n"
            f"Доска: {booking['board_name']}\n"
            f"Дата: {booking['date']}\n"
            f"Сумма: {booking['amount']:.2f}₽\n\n"
            f"Пользователю будет отправлено уведомление об отмене.",
            reply_markup=keyboard
        )
    
    @router.callback_query(F.data.startswith("partner:booking_cancel_confirm:"))
    async def partner_booking_cancel_confirm(callback: CallbackQuery):
        """Подтверждение отмены бронирования"""
        await callback.answer()
        booking_id = int(callback.data.split(":")[-1])
        
        booking = await db.fetchone(
            "SELECT * FROM bookings WHERE id = ?",
            (booking_id,)
        )
        
        if not booking:
            await callback.message.edit_text("❌ Бронирование не найдено.")
            return
        
        try:
            await db.execute(
                "UPDATE bookings SET status = 'canceled' WHERE id = ?",
                (booking_id,)
            )
            
            text = f"✅ Бронирование #{booking_id} отменено!"
            await callback.message.edit_text(text, reply_markup=get_back_keyboard("partner:bookings"))
            
            # Отправляем уведомление пользователю
            if notification_service:
                try:
                    await notification_service.notify_user_booking_canceled(booking['user_id'], booking_id)
                except Exception as e:
                    logger.error(f"Error sending cancellation notification: {e}")
            
        except Exception as e:
            logger.error(f"Error canceling booking: {e}")
            await callback.message.edit_text("❌ Ошибка при отмене бронирования.")
    
    @router.callback_query(F.data == "partner:reviews")
    async def partner_reviews_menu(callback: CallbackQuery):
        """Меню отзывов партнера"""
        await callback.answer()
        user_id = callback.from_user.id
        
        # Проверяем права партнера
        partner = await db.fetchone(
            "SELECT id FROM partners WHERE telegram_id = ? AND is_approved = 1 AND is_active = 1",
            (user_id,)
        )
        
        if not partner:
            await callback.message.edit_text("❌ У вас нет доступа к партнерской панели.")
            return
        
        partner_id = partner['id']
        
        # Получаем статистику
        from services.review_service import ReviewService
        review_service = ReviewService(db)
        
        avg_rating = await review_service.get_average_rating(partner_id=partner_id)
        review_count = await review_service.get_review_count(partner_id=partner_id)
        
        text = "⭐ <b>Отзывы</b>\n\n"
        if review_count > 0:
            text += f"📊 <b>Статистика:</b>\n"
            text += f"Всего отзывов: {review_count}\n"
            if avg_rating:
                stars = "⭐" * int(avg_rating)
                text += f"Средняя оценка: {stars} {avg_rating:.2f}/5\n"
        else:
            text += "У вас пока нет отзывов.\n"
            text += "Отзывы появятся после того, как пользователи оставят их на ваши бронирования.\n"
        
        text += "\nВыберите действие:"
        
        try:
            await callback.message.edit_text(text, reply_markup=get_reviews_menu_keyboard())
        except:
            await callback.message.answer(text, reply_markup=get_reviews_menu_keyboard())
    
    @router.callback_query(F.data == "partner:reviews_stats")
    async def partner_reviews_stats(callback: CallbackQuery):
        """Статистика отзывов партнера"""
        await callback.answer()
        user_id = callback.from_user.id
        
        partner = await db.fetchone(
            "SELECT id FROM partners WHERE telegram_id = ? AND is_approved = 1 AND is_active = 1",
            (user_id,)
        )
        
        if not partner:
            await callback.message.edit_text("❌ У вас нет доступа.")
            return
        
        partner_id = partner['id']
        from services.review_service import ReviewService
        review_service = ReviewService(db)
        
        # Получаем все отзывы
        reviews = await review_service.get_reviews_by_partner(partner_id, limit=1000)
        
        if not reviews:
            text = "📊 <b>Статистика отзывов</b>\n\n"
            text += "У вас пока нет отзывов."
            keyboard = get_back_keyboard("partner:reviews")
            try:
                await callback.message.edit_text(text, reply_markup=keyboard)
            except:
                await callback.message.answer(text, reply_markup=keyboard)
            return
        
        # Подсчитываем статистику
        total = len(reviews)
        ratings = [r['rating'] for r in reviews]
        avg = sum(ratings) / len(ratings) if ratings else 0
        rating_counts = {i: ratings.count(i) for i in range(1, 6)}
        
        text = "📊 <b>Статистика отзывов</b>\n\n"
        text += f"Всего отзывов: {total}\n"
        text += f"Средняя оценка: {'⭐' * int(avg)} {avg:.2f}/5\n\n"
        text += "<b>Распределение оценок:</b>\n"
        for rating in range(5, 0, -1):
            count = rating_counts.get(rating, 0)
            percent = (count / total * 100) if total > 0 else 0
            bar = "█" * int(percent / 5)  # Простая визуализация
            text += f"{'⭐' * rating}: {count} ({percent:.1f}%) {bar}\n"
        
        keyboard = get_back_keyboard("partner:reviews")
        try:
            await callback.message.edit_text(text, reply_markup=keyboard)
        except:
            await callback.message.answer(text, reply_markup=keyboard)
    
    @router.callback_query(F.data == "partner:reviews_list")
    async def partner_reviews_list(callback: CallbackQuery):
        """Список всех отзывов партнера"""
        await callback.answer()
        user_id = callback.from_user.id
        
        partner = await db.fetchone(
            "SELECT id FROM partners WHERE telegram_id = ? AND is_approved = 1 AND is_active = 1",
            (user_id,)
        )
        
        if not partner:
            await callback.message.edit_text("❌ У вас нет доступа.")
            return
        
        partner_id = partner['id']
        from services.review_service import ReviewService
        review_service = ReviewService(db)
        
        reviews = await review_service.get_reviews_by_partner(partner_id, limit=50)
        
        if not reviews:
            text = "📋 <b>Все отзывы</b>\n\n"
            text += "У вас пока нет отзывов."
            keyboard = get_back_keyboard("partner:reviews")
            try:
                await callback.message.edit_text(text, reply_markup=keyboard)
            except:
                await callback.message.answer(text, reply_markup=keyboard)
            return
        
        text = f"📋 <b>Все отзывы ({len(reviews)})</b>\n\n"
        
        # Показываем последние 10 отзывов
        for review in reviews[:10]:
            text += f"#{review['id']} - {'⭐' * review['rating']}/5\n"
            if review.get('board_name'):
                text += f"Доска: {review['board_name']}\n"
            if review.get('comment'):
                comment_preview = review['comment'][:60] + "..." if len(review['comment']) > 60 else review['comment']
                text += f"{comment_preview}\n"
            if review.get('full_name'):
                text += f"Пользователь: {review['full_name']}\n"
            text += f"Дата: {review['created_at']}\n\n"
        
        if len(reviews) > 10:
            text += f"... и еще {len(reviews) - 10} отзывов"
        
        keyboard = get_back_keyboard("partner:reviews")
        try:
            await callback.message.edit_text(text, reply_markup=keyboard)
        except:
            await callback.message.answer(text, reply_markup=keyboard)
    
    @router.callback_query(F.data.startswith("partner:board_reviews:"))
    async def partner_board_reviews(callback: CallbackQuery):
        """Отзывы к конкретной доске"""
        await callback.answer()
        board_id = int(callback.data.split(":")[-1])
        user_id = callback.from_user.id
        
        # Проверяем права
        board = await db.fetchone(
            "SELECT partner_id, name FROM boards WHERE id = ?",
            (board_id,)
        )
        
        if not board:
            await callback.message.edit_text("❌ Доска не найдена.")
            return
        
        partner = await db.fetchone(
            "SELECT id FROM partners WHERE telegram_id = ? AND id = ? AND is_approved = 1",
            (user_id, board['partner_id'])
        )
        
        if not partner:
            await callback.message.edit_text("❌ У вас нет доступа к этой доске.")
            return
        
        from services.review_service import ReviewService
        review_service = ReviewService(db)
        
        reviews = await review_service.get_reviews_by_board(board_id, limit=20)
        avg_rating = await review_service.get_average_rating(board_id=board_id)
        review_count = len(reviews)
        
        text = f"⭐ <b>Отзывы к доске: {board['name']}</b>\n\n"
        
        if review_count > 0:
            if avg_rating:
                text += f"📊 Рейтинг: {'⭐' * int(avg_rating)} {avg_rating:.2f}/5 ({review_count} отзывов)\n\n"
            
            text += "<b>Последние отзывы:</b>\n\n"
            
            for review in reviews[:5]:
                text += f"{'⭐' * review['rating']}/5\n"
                if review.get('comment'):
                    comment_preview = review['comment'][:80] + "..." if len(review['comment']) > 80 else review['comment']
                    text += f"{comment_preview}\n"
                if review.get('full_name'):
                    text += f"— {review['full_name']}\n"
                text += f"{review['created_at']}\n\n"
            
            if review_count > 5:
                text += f"... и еще {review_count - 5} отзывов"
        else:
            text += "К этой доске пока нет отзывов.\n"
            text += "Отзывы появятся после того, как пользователи оставят их."
        
        keyboard = get_back_keyboard(f"partner:board:{board_id}")
        try:
            await callback.message.edit_text(text, reply_markup=keyboard)
        except:
            await callback.message.answer(text, reply_markup=keyboard)
    
    @router.callback_query(F.data == "partner:menu")
    async def partner_menu_from_reviews(callback: CallbackQuery, state: FSMContext):
        """Возврат в партнерское меню из отзывов"""
        await callback.answer()
        await state.clear()
        user_id = callback.from_user.id
        
        partner = await db.fetchone(
            "SELECT * FROM partners WHERE telegram_id = ? AND is_approved = 1",
            (user_id,)
        )
        
        text = f"💼 <b>Партнерская панель</b>\n\n"
        text += f"Партнер: {partner['name']}\n"
        text += f"Комиссия: {partner['commission_percent']}%\n\n"
        text += "Выберите действие:"
        
        await callback.message.edit_text(text, reply_markup=get_partner_menu())
    
    @router.callback_query(F.data == "partner:employees")
    async def partner_employees(callback: CallbackQuery):
        """Управление сотрудниками"""
        await callback.answer()
        user_id = callback.from_user.id
        
        partner = await db.fetchone(
            "SELECT id FROM partners WHERE telegram_id = ? AND is_approved = 1 AND is_active = 1",
            (user_id,)
        )
        
        if not partner:
            await callback.message.edit_text("❌ У вас нет доступа.")
            return
        
        partner_id = partner['id']
        
        # Получаем список сотрудников
        employees = await db.fetchall(
            "SELECT * FROM employees WHERE partner_id = ? ORDER BY created_at DESC",
            (partner_id,)
        )
        
        text = "👥 <b>Сотрудники</b>\n\n"
        text += f"Всего сотрудников: {len(employees)}\n\n"
        
        if not employees:
            text += "У вас пока нет сотрудников.\n"
            text += "Добавьте сотрудника по его Telegram ID."
        else:
            text += "<b>Список сотрудников:</b>\n\n"
            for emp in employees:
                # Получаем информацию о пользователе
                user = await db.fetchone("SELECT full_name, username FROM users WHERE id = ?", (emp['telegram_id'],))
                user_name = user.get('full_name', f"ID: {emp['telegram_id']}") if user else f"ID: {emp['telegram_id']}"
                
                # Статистика по сотруднику
                bookings_count = await db.fetchone(
                    "SELECT COUNT(*) as count FROM bookings WHERE employee_id = ?",
                    (emp['id'],)
                )
                
                text += f"👤 {user_name}\n"
                text += f"   Комиссия: {emp['commission_percent']}%\n"
                text += f"   Бронирований: {bookings_count['count'] if bookings_count else 0}\n"
                text += f"   ID: {emp['telegram_id']}\n\n"
        
        buttons = [
            [InlineKeyboardButton(text="➕ Добавить сотрудника", callback_data="partner:employee_add")],
        ]
        
        for emp in employees[:10]:
            user = await db.fetchone("SELECT full_name FROM users WHERE id = ?", (emp['telegram_id'],))
            emp_name = user.get('full_name', f"ID {emp['telegram_id']}") if user else f"ID {emp['telegram_id']}"
            buttons.append([InlineKeyboardButton(
                text=f"👤 {emp_name}",
                callback_data=f"partner:employee:{emp['id']}"
            )])
        
        buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="partner:menu")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        try:
            await callback.message.edit_text(text, reply_markup=keyboard)
        except:
            await callback.message.answer(text, reply_markup=keyboard)
    
    @router.callback_query(F.data == "partner:employee_add")
    async def partner_employee_add_start(callback: CallbackQuery, state: FSMContext):
        """Начало добавления сотрудника"""
        await callback.answer()
        await state.set_state(PartnerStates.adding_employee)
        
        text = "➕ <b>Добавление сотрудника</b>\n\n"
        text += "Введите Telegram ID сотрудника (число):"
        
        try:
            await callback.message.edit_text(text, reply_markup=get_back_keyboard("partner:employees"))
        except:
            await callback.message.answer(text, reply_markup=get_back_keyboard("partner:employees"))
    
    @router.message(PartnerStates.adding_employee, F.text)
    async def partner_employee_add_save(message: Message, state: FSMContext):
        """Сохранение нового сотрудника"""
        try:
            employee_telegram_id = int(message.text.strip())
        except ValueError:
            await message.answer("❌ Неверный формат. Введите число (Telegram ID).")
            return
        
        user_id = message.from_user.id
        
        partner = await db.fetchone(
            "SELECT id FROM partners WHERE telegram_id = ? AND is_approved = 1 AND is_active = 1",
            (user_id,)
        )
        
        if not partner:
            await message.answer("❌ У вас нет доступа.")
            await state.clear()
            return
        
        partner_id = partner['id']
        
        # Проверяем, не является ли это сам партнер
        if employee_telegram_id == user_id:
            await message.answer("❌ Нельзя добавить самого себя как сотрудника.")
            return
        
        # Проверяем, не добавлен ли уже этот сотрудник
        existing = await db.fetchone(
            "SELECT id FROM employees WHERE telegram_id = ? AND partner_id = ?",
            (employee_telegram_id, partner_id)
        )
        
        if existing:
            await message.answer("❌ Этот сотрудник уже добавлен.")
            await state.clear()
            return
        
        # Добавляем сотрудника с комиссией по умолчанию (30%)
        try:
            await db.execute(
                "INSERT INTO employees (telegram_id, partner_id, commission_percent) VALUES (?, ?, 30.0)",
                (employee_telegram_id, partner_id)
            )
            
            # Получаем информацию о пользователе
            user = await db.fetchone("SELECT full_name FROM users WHERE id = ?", (employee_telegram_id,))
            user_name = user.get('full_name', f"ID: {employee_telegram_id}") if user else f"ID: {employee_telegram_id}"
            
            text = f"✅ Сотрудник добавлен!\n\n"
            text += f"Имя: {user_name}\n"
            text += f"Telegram ID: {employee_telegram_id}\n"
            text += f"Комиссия: 30%\n\n"
            text += "Изменить комиссию можно в деталях сотрудника."
            
            await message.answer(text, reply_markup=get_back_keyboard("partner:employees"))
            await state.clear()
        except Exception as e:
            logger.error(f"Error adding employee: {e}")
            await message.answer("❌ Ошибка при добавлении сотрудника. Попробуйте еще раз.")
    
    @router.callback_query(F.data.startswith("partner:employee:"))
    async def partner_employee_detail(callback: CallbackQuery):
        """Детали сотрудника"""
        await callback.answer()
        employee_id = int(callback.data.split(":")[-1])
        user_id = callback.from_user.id
        
        partner = await db.fetchone(
            "SELECT id FROM partners WHERE telegram_id = ? AND is_approved = 1 AND is_active = 1",
            (user_id,)
        )
        
        if not partner:
            await callback.message.edit_text("❌ У вас нет доступа.")
            return
        
        partner_id = partner['id']
        
        employee = await db.fetchone(
            "SELECT * FROM employees WHERE id = ? AND partner_id = ?",
            (employee_id, partner_id)
        )
        
        if not employee:
            await callback.message.edit_text("❌ Сотрудник не найден.")
            return
        
        # Получаем информацию о пользователе
        user = await db.fetchone("SELECT full_name, username FROM users WHERE id = ?", (employee['telegram_id'],))
        user_name = user.get('full_name', 'Не указано') if user else 'Не указано'
        username = user.get('username', '') if user else ''
        
        # Статистика
        bookings_count = await db.fetchone(
            "SELECT COUNT(*) as count FROM bookings WHERE employee_id = ?",
            (employee_id,)
        )
        
        completed_bookings = await db.fetchone(
            "SELECT COUNT(*) as count FROM bookings WHERE employee_id = ? AND status = 'completed'",
            (employee_id,)
        )
        
        text = f"👤 <b>Сотрудник</b>\n\n"
        text += f"Имя: {user_name}\n"
        if username:
            text += f"Username: @{username}\n"
        text += f"Telegram ID: {employee['telegram_id']}\n"
        text += f"Комиссия: {employee['commission_percent']}%\n\n"
        text += f"<b>Статистика:</b>\n"
        text += f"Всего бронирований: {bookings_count['count'] if bookings_count else 0}\n"
        text += f"Завершено: {completed_bookings['count'] if completed_bookings else 0}\n"
        
        buttons = [
            [InlineKeyboardButton(text="✏️ Изменить комиссию", callback_data=f"partner:employee_commission:{employee_id}")],
            [InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"partner:employee_delete:{employee_id}")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="partner:employees")],
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        try:
            await callback.message.edit_text(text, reply_markup=keyboard)
        except:
            await callback.message.answer(text, reply_markup=keyboard)
    
    @router.callback_query(F.data.startswith("partner:employee_delete:"))
    async def partner_employee_delete(callback: CallbackQuery):
        """Удаление сотрудника"""
        await callback.answer()
        employee_id = int(callback.data.split(":")[-1])
        
        employee = await db.fetchone("SELECT telegram_id FROM employees WHERE id = ?", (employee_id,))
        if not employee:
            await callback.message.edit_text("❌ Сотрудник не найден.")
            return
        
        keyboard = get_confirm_keyboard(
            f"partner:employee_delete_confirm:{employee_id}",
            f"partner:employee:{employee_id}"
        )
        
        text = f"⚠️ <b>Удаление сотрудника</b>\n\n"
        text += f"Telegram ID: {employee['telegram_id']}\n\n"
        text += "Вы уверены, что хотите удалить этого сотрудника?"
        
        try:
            await callback.message.edit_text(text, reply_markup=keyboard)
        except:
            await callback.message.answer(text, reply_markup=keyboard)
    
    @router.callback_query(F.data.startswith("partner:employee_delete_confirm:"))
    async def partner_employee_delete_confirm(callback: CallbackQuery):
        """Подтверждение удаления сотрудника"""
        await callback.answer()
        employee_id = int(callback.data.split(":")[-1])
        
        try:
            await db.execute("DELETE FROM employees WHERE id = ?", (employee_id,))
            text = "✅ Сотрудник удален!"
            keyboard = get_back_keyboard("partner:employees")
            try:
                await callback.message.edit_text(text, reply_markup=keyboard)
            except:
                await callback.message.answer(text, reply_markup=keyboard)
        except Exception as e:
            logger.error(f"Error deleting employee: {e}")
            await callback.message.edit_text("❌ Ошибка при удалении сотрудника.")
    
    @router.callback_query(F.data.startswith("partner:employee_commission:"))
    async def partner_employee_commission_start(callback: CallbackQuery, state: FSMContext):
        """Начало изменения комиссии сотрудника"""
        await callback.answer()
        employee_id = int(callback.data.split(":")[-1])
        await state.set_state(PartnerStates.editing_employee_commission)
        await state.update_data(employee_id=employee_id)
        
        text = "✏️ <b>Изменение комиссии сотрудника</b>\n\n"
        text += "Введите новый процент комиссии (от 0 до 100):"
        
        try:
            await callback.message.edit_text(text, reply_markup=get_back_keyboard(f"partner:employee:{employee_id}"))
        except:
            await callback.message.answer(text, reply_markup=get_back_keyboard(f"partner:employee:{employee_id}"))
    
    @router.message(PartnerStates.editing_employee_commission, F.text)
    async def partner_employee_commission_save(message: Message, state: FSMContext):
        """Сохранение новой комиссии сотрудника"""
        try:
            commission = float(message.text.strip())
        except ValueError:
            await message.answer("❌ Неверный формат. Введите число (например, 30 для 30%).")
            return
        
        if commission < 0 or commission > 100:
            await message.answer("❌ Комиссия должна быть от 0 до 100%.")
            return
        
        data = await state.get_data()
        employee_id = data.get("employee_id")
        user_id = message.from_user.id
        
        partner = await db.fetchone(
            "SELECT id FROM partners WHERE telegram_id = ? AND is_approved = 1 AND is_active = 1",
            (user_id,)
        )
        
        if not partner:
            await message.answer("❌ У вас нет доступа.")
            await state.clear()
            return
        
        partner_id = partner['id']
        
        # Проверяем, что сотрудник принадлежит партнеру
        employee = await db.fetchone(
            "SELECT id FROM employees WHERE id = ? AND partner_id = ?",
            (employee_id, partner_id)
        )
        
        if not employee:
            await message.answer("❌ Сотрудник не найден.")
            await state.clear()
            return
        
        try:
            await db.execute(
                "UPDATE employees SET commission_percent = ? WHERE id = ?",
                (commission, employee_id)
            )
            
            text = f"✅ Комиссия сотрудника обновлена!\n\n"
            text += f"Новая комиссия: {commission}%"
            
            await message.answer(text, reply_markup=get_back_keyboard(f"partner:employee:{employee_id}"))
            await state.clear()
        except Exception as e:
            logger.error(f"Error updating employee commission: {e}")
            await message.answer("❌ Ошибка при обновлении комиссии. Попробуйте еще раз.")
    
    @router.callback_query(F.data == "back_to_partner")
    async def back_to_partner(callback: CallbackQuery, state: FSMContext):
        """Возврат в партнерское меню"""
        await callback.answer()
        await state.clear()
        user_id = callback.from_user.id
        
        partner = await db.fetchone(
            "SELECT * FROM partners WHERE telegram_id = ? AND is_approved = 1",
            (user_id,)
        )
        
        if not partner:
            await callback.message.edit_text("❌ У вас нет доступа к партнерской панели.")
            return
        
        text = f"💼 <b>Партнерская панель</b>\n\n"
        text += f"Партнер: {partner['name']}\n"
        text += f"Комиссия: {partner['commission_percent']}%\n\n"
        text += "Выберите действие:"
        
        try:
            await callback.message.edit_text(text, reply_markup=get_partner_menu())
        except:
            await callback.message.answer(text, reply_markup=get_partner_menu())

