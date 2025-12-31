"""Обработчики каталога локаций и досок"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from core.database import Database
from keyboards.user import get_back_keyboard
from services.review_service import ReviewService

logger = logging.getLogger(__name__)


def register_catalog_handlers(router: Router, db: Database, bot=None):
    """Регистрация обработчиков каталога"""
    review_service = ReviewService(db)
    
    @router.message(F.text == "📚 Каталог")
    async def catalog_menu(message: Message):
        """Меню каталога"""
        locations = await db.fetchall(
            "SELECT * FROM locations WHERE is_active = 1 ORDER BY name"
        )
        
        text = "📚 <b>Каталог локаций и досок</b>\n\n"
        text += f"Доступно локаций: {len(locations)}\n\n"
        text += "Выберите локацию для просмотра досок:"
        
        buttons = []
        for location in locations[:20]:  # Показываем первые 20
            buttons.append([InlineKeyboardButton(
                text=f"📍 {location['name']}",
                callback_data=f"catalog:location:{location['id']}"
            )])
        
        buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        await message.answer(text, reply_markup=keyboard)
    
    @router.callback_query(F.data.startswith("catalog:location:"))
    async def catalog_location_boards(callback: CallbackQuery):
        """Доски в локации"""
        await callback.answer()
        location_id = int(callback.data.split(":")[-1])
        
        location = await db.fetchone("SELECT * FROM locations WHERE id = ?", (location_id,))
        if not location:
            await callback.message.edit_text("❌ Локация не найдена.", reply_markup=get_back_keyboard())
            return
        
        boards = await db.fetchall(
            """SELECT * FROM boards 
               WHERE location_id = ? AND is_active = 1 
               ORDER BY name""",
            (location_id,)
        )
        
        text = f"📍 <b>{location['name']}</b>\n\n"
        if location.get('address'):
            text += f"Адрес: {location['address']}\n\n"
        
        if not boards:
            text += "В этой локации пока нет доступных досок."
            keyboard = get_back_keyboard("catalog:menu")
            try:
                await callback.message.edit_text(text, reply_markup=keyboard)
            except:
                await callback.message.answer(text, reply_markup=keyboard)
            return
        
        text += f"Доступно досок: {len(boards)}\n\n"
        text += "Выберите доску для просмотра:"
        
        buttons = []
        for board in boards[:20]:
            # Получаем рейтинг для доски
            avg_rating = await review_service.get_average_rating(board_id=board['id'])
            review_count = await review_service.get_review_count(board_id=board['id'])
            
            board_text = f"🏄 {board['name']} - {board['price']:.0f}₽/ч"
            if avg_rating and review_count > 0:
                board_text += f" ⭐ {avg_rating:.1f}"
            
            buttons.append([InlineKeyboardButton(
                text=board_text,
                callback_data=f"catalog:board:{board['id']}"
            )])
        
        buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="catalog:menu")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        try:
            await callback.message.edit_text(text, reply_markup=keyboard)
        except:
            await callback.message.answer(text, reply_markup=keyboard)
    
    @router.callback_query(F.data.startswith("catalog:board:"))
    async def catalog_board_detail(callback: CallbackQuery):
        """Детали доски в каталоге"""
        await callback.answer()
        board_id = int(callback.data.split(":")[-1])
        
        board = await db.fetchone("SELECT * FROM boards WHERE id = ?", (board_id,))
        if not board:
            await callback.message.edit_text("❌ Доска не найдена.", reply_markup=get_back_keyboard())
            return
        
        location = await db.fetchone("SELECT * FROM locations WHERE id = ?", (board['location_id'],))
        
        # Получаем отзывы и рейтинг
        avg_rating = await review_service.get_average_rating(board_id=board_id)
        review_count = await review_service.get_review_count(board_id=board_id)
        
        text = f"🏄 <b>{board['name']}</b>\n\n"
        text += f"📍 Локация: {location['name'] if location else 'Не указана'}\n"
        if location and location.get('address'):
            text += f"Адрес: {location['address']}\n"
        text += f"\n💰 Цена: {board['price']:.0f}₽/час\n"
        text += f"📊 Доступно: {board['quantity']}/{board['total']} досок\n"
        
        if avg_rating and review_count > 0:
            stars = "⭐" * int(avg_rating)
            text += f"⭐ Рейтинг: {stars} {avg_rating:.2f}/5 ({review_count} отзывов)\n"
        
        if board.get('description'):
            text += f"\n📝 Описание:\n{board['description']}\n"
        
        # Проверяем наличие фото
        images = await db.fetchall(
            "SELECT file_id FROM board_images WHERE board_id = ? LIMIT 1",
            (board_id,)
        )
        
        buttons = [
            [InlineKeyboardButton(text="🆕 Забронировать", callback_data=f"booking_from_catalog:{board_id}")],
        ]
        
        if images:
            buttons.append([InlineKeyboardButton(text="🖼️ Фото", callback_data=f"catalog:board_images:{board_id}")])
        
        buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data=f"catalog:location:{board['location_id']}")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        # Если есть фото, отправляем его
        if images and bot:
            try:
                text_preview = f"🏄 <b>{board['name']}</b>\n💰 {board['price']:.0f}₽/час"
                if avg_rating and review_count > 0:
                    text_preview += f" ⭐ {avg_rating:.1f}/5"
                
                await bot.send_photo(
                    chat_id=callback.from_user.id,
                    photo=images[0]['file_id'],
                    caption=text,
                    reply_markup=keyboard
                )
                try:
                    await callback.message.delete()
                except:
                    pass
                return
            except Exception as e:
                logger.error(f"Error sending board photo: {e}")
        
        try:
            await callback.message.edit_text(text, reply_markup=keyboard)
        except:
            await callback.message.answer(text, reply_markup=keyboard)
    
    @router.callback_query(F.data.startswith("catalog:board_images:"))
    async def catalog_board_images(callback: CallbackQuery):
        """Просмотр фото доски в каталоге"""
        await callback.answer()
        board_id = int(callback.data.split(":")[-1])
        
        images = await db.fetchall(
            "SELECT file_id FROM board_images WHERE board_id = ?",
            (board_id,)
        )
        
        if not images:
            await callback.answer("У этой доски нет фото.", show_alert=True)
            return
        
        board = await db.fetchone("SELECT name FROM boards WHERE id = ?", (board_id,))
        text = f"🖼️ <b>Фото доски: {board['name']}</b>\n\n"
        text += f"Всего фото: {len(images)}"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data=f"catalog:board:{board_id}")]
        ])
        
        # Отправляем первое фото
        if bot:
            try:
                await bot.send_photo(
                    chat_id=callback.from_user.id,
                    photo=images[0]['file_id'],
                    caption=text,
                    reply_markup=keyboard
                )
                try:
                    await callback.message.delete()
                except:
                    pass
            except Exception as e:
                logger.error(f"Error sending photo: {e}")
                await callback.message.edit_text(text, reply_markup=keyboard)
        else:
            await callback.message.edit_text(text, reply_markup=keyboard)
    
    @router.callback_query(F.data == "catalog:menu")
    async def catalog_menu_callback(callback: CallbackQuery):
        """Меню каталога (из callback)"""
        await callback.answer()
        
        locations = await db.fetchall(
            "SELECT * FROM locations WHERE is_active = 1 ORDER BY name"
        )
        
        text = "📚 <b>Каталог локаций и досок</b>\n\n"
        text += f"Доступно локаций: {len(locations)}\n\n"
        text += "Выберите локацию для просмотра досок:"
        
        buttons = []
        for location in locations[:20]:
            buttons.append([InlineKeyboardButton(
                text=f"📍 {location['name']}",
                callback_data=f"catalog:location:{location['id']}"
            )])
        
        buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        try:
            await callback.message.edit_text(text, reply_markup=keyboard)
        except:
            await callback.message.answer(text, reply_markup=keyboard)
    
    @router.callback_query(F.data.startswith("booking_from_catalog:"))
    async def booking_from_catalog(callback: CallbackQuery, state):
        """Начало бронирования из каталога"""
        await callback.answer()
        board_id = int(callback.data.split(":")[-1])
        
        # Начинаем процесс бронирования с выбранной доской
        from aiogram.fsm.state import State, StatesGroup
        from handlers.booking_handlers import BookingStates
        
        board = await db.fetchone("SELECT * FROM boards WHERE id = ?", (board_id,))
        if not board:
            await callback.message.edit_text("❌ Доска не найдена.", reply_markup=get_back_keyboard())
            return
        
        # Устанавливаем данные в state
        await state.update_data(
            board_id=board_id,
            board_name=board['name'],
            board_price=board['price'],
            location_id=board['location_id'],
            booking_type="regular"
        )
        
        # Переходим к выбору даты
        from keyboards.user import get_date_keyboard
        await state.set_state(BookingStates.choosing_date)
        
        text = f"🏄 <b>Бронирование: {board['name']}</b>\n\n"
        text += f"💰 Цена: {board['price']:.0f}₽/час\n\n"
        text += "Выберите дату бронирования:"
        
        keyboard = get_date_keyboard()
        try:
            await callback.message.edit_text(text, reply_markup=keyboard)
        except:
            await callback.message.answer(text, reply_markup=keyboard)

