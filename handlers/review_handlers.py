"""Обработчики отзывов"""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from core.database import Database
from services.review_service import ReviewService
from keyboards.user import get_back_keyboard

logger = logging.getLogger(__name__)


class ReviewStates(StatesGroup):
    """Состояния для создания отзыва"""
    choosing_rating = State()
    entering_comment = State()


def get_rating_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора оценки"""
    buttons = []
    for rating in range(5, 0, -1):
        stars = "⭐" * rating
        buttons.append([InlineKeyboardButton(
            text=f"{stars} ({rating})",
            callback_data=f"review:rating:{rating}"
        )])
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_review_skip_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для пропуска комментария"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭ Пропустить", callback_data="review:skip_comment")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
    ])


def register_review_handlers(router: Router, db: Database, bot=None):
    """Регистрация обработчиков отзывов"""
    review_service = ReviewService(db)
    
    @router.callback_query(F.data.startswith("review:booking:"))
    async def start_review(callback: CallbackQuery, state: FSMContext):
        """Начало создания отзыва"""
        await callback.answer()
        booking_id = int(callback.data.split(":")[-1])
        user_id = callback.from_user.id
        
        # Проверяем, может ли пользователь оставить отзыв
        can_review = await review_service.user_can_review_booking(user_id, booking_id)
        
        if not can_review:
            await callback.message.edit_text(
                "❌ Вы не можете оставить отзыв на это бронирование.\n\n"
                "Возможные причины:\n"
                "• Бронирование еще не завершено\n"
                "• Вы уже оставили отзыв\n"
                "• Бронирование не принадлежит вам",
                reply_markup=get_back_keyboard()
            )
            return
        
        # Получаем информацию о бронировании
        booking = await db.fetchone("""
            SELECT b.*, brd.name as board_name
            FROM bookings b
            LEFT JOIN boards brd ON b.board_id = brd.id
            WHERE b.id = ?
        """, (booking_id,))
        
        if not booking:
            await callback.message.edit_text(
                "❌ Бронирование не найдено",
                reply_markup=get_back_keyboard()
            )
            return
        
        await state.set_state(ReviewStates.choosing_rating)
        await state.update_data(booking_id=booking_id)
        
        text = f"📝 <b>Оставить отзыв</b>\n\n"
        text += f"Бронирование: {booking['board_name'] or booking['board_name']}\n"
        text += f"Дата: {booking['date']}\n"
        text += f"Время: {booking['start_time']}:{booking['start_minute']:02d}\n\n"
        text += "Выберите оценку:"
        
        try:
            await callback.message.edit_text(text, reply_markup=get_rating_keyboard())
        except:
            await callback.message.answer(text, reply_markup=get_rating_keyboard())
    
    @router.callback_query(F.data.startswith("review:rating:"), ReviewStates.choosing_rating)
    async def rating_chosen(callback: CallbackQuery, state: FSMContext):
        """Обработка выбранной оценки"""
        await callback.answer()
        rating = int(callback.data.split(":")[-1])
        
        await state.update_data(rating=rating)
        await state.set_state(ReviewStates.entering_comment)
        
        text = f"⭐ Оценка: {rating}/5\n\n"
        text += "Напишите комментарий к отзыву (или нажмите 'Пропустить'):"
        
        try:
            await callback.message.edit_text(text, reply_markup=get_review_skip_keyboard())
        except:
            await callback.message.answer(text, reply_markup=get_review_skip_keyboard())
    
    @router.message(ReviewStates.entering_comment, F.text)
    async def comment_entered(message: Message, state: FSMContext):
        """Обработка введенного комментария"""
        comment = message.text.strip()
        
        if len(comment) > 1000:
            await message.answer(
                "❌ Комментарий слишком длинный (максимум 1000 символов). Попробуйте короче.",
                reply_markup=get_review_skip_keyboard()
            )
            return
        
        data = await state.get_data()
        booking_id = data.get('booking_id')
        rating = data.get('rating')
        user_id = message.from_user.id
        
        try:
            # Получаем информацию о бронировании для дополнительных полей
            booking = await db.fetchone("SELECT board_id, partner_id FROM bookings WHERE id = ?", (booking_id,))
            board_id = booking.get('board_id') if booking else None
            partner_id = booking.get('partner_id') if booking else None
            location_id = None
            
            if board_id:
                board = await db.fetchone("SELECT location_id FROM boards WHERE id = ?", (board_id,))
                location_id = board.get('location_id') if board else None
            
            # Создаем отзыв
            review_id = await review_service.create_review(
                user_id=user_id,
                booking_id=booking_id,
                rating=rating,
                comment=comment,
                board_id=board_id,
                location_id=location_id,
                partner_id=partner_id
            )
            
            text = f"✅ <b>Спасибо за отзыв!</b>\n\n"
            text += f"Ваш отзыв сохранен (ID: #{review_id}).\n"
            text += f"Оценка: {'⭐' * rating}\n"
            if comment:
                text += f"Комментарий: {comment[:100]}{'...' if len(comment) > 100 else ''}\n"
            
            await message.answer(text, reply_markup=get_back_keyboard())
            await state.clear()
            
            # Уведомляем партнера о новом отзыве (если есть бот)
            if bot and partner_id:
                try:
                    partner = await db.fetchone("SELECT telegram_id FROM partners WHERE id = ?", (partner_id,))
                    if partner and partner.get('telegram_id'):
                        partner_text = f"⭐ <b>Новый отзыв!</b>\n\n"
                        partner_text += f"Оценка: {'⭐' * rating}/5\n"
                        if comment:
                            partner_text += f"Комментарий: {comment}\n"
                        partner_text += f"\nБронирование: #{booking_id}"
                        
                        await bot.send_message(
                            chat_id=partner['telegram_id'],
                            text=partner_text
                        )
                except Exception as e:
                    logger.error(f"Error notifying partner about review: {e}")
            
        except Exception as e:
            logger.error(f"Error creating review: {e}")
            await message.answer(
                "❌ Ошибка при сохранении отзыва. Попробуйте еще раз.",
                reply_markup=get_back_keyboard()
            )
    
    @router.callback_query(F.data == "review:skip_comment", ReviewStates.entering_comment)
    async def skip_comment(callback: CallbackQuery, state: FSMContext):
        """Пропуск комментария"""
        await callback.answer()
        
        data = await state.get_data()
        booking_id = data.get('booking_id')
        rating = data.get('rating')
        user_id = callback.from_user.id
        
        try:
            # Получаем информацию о бронировании
            booking = await db.fetchone("SELECT board_id, partner_id FROM bookings WHERE id = ?", (booking_id,))
            board_id = booking.get('board_id') if booking else None
            partner_id = booking.get('partner_id') if booking else None
            location_id = None
            
            if board_id:
                board = await db.fetchone("SELECT location_id FROM boards WHERE id = ?", (board_id,))
                location_id = board.get('location_id') if board else None
            
            # Создаем отзыв без комментария
            review_id = await review_service.create_review(
                user_id=user_id,
                booking_id=booking_id,
                rating=rating,
                comment=None,
                board_id=board_id,
                location_id=location_id,
                partner_id=partner_id
            )
            
            text = f"✅ <b>Спасибо за отзыв!</b>\n\n"
            text += f"Ваш отзыв сохранен (ID: #{review_id}).\n"
            text += f"Оценка: {'⭐' * rating}\n"
            
            try:
                await callback.message.edit_text(text, reply_markup=get_back_keyboard())
            except:
                await callback.message.answer(text, reply_markup=get_back_keyboard())
            
            await state.clear()
            
        except Exception as e:
            logger.error(f"Error creating review: {e}")
            try:
                await callback.message.edit_text(
                    "❌ Ошибка при сохранении отзыва. Попробуйте еще раз.",
                    reply_markup=get_back_keyboard()
                )
            except:
                await callback.message.answer(
                    "❌ Ошибка при сохранении отзыва. Попробуйте еще раз.",
                    reply_markup=get_back_keyboard()
                )
    
    @router.callback_query(F.data == "my_reviews")
    async def show_my_reviews(callback: CallbackQuery):
        """Показать отзывы пользователя"""
        await callback.answer()
        user_id = callback.from_user.id
        
        reviews = await review_service.get_user_reviews(user_id)
        
        if not reviews:
            text = "📝 <b>Мои отзывы</b>\n\n"
            text += "У вас пока нет отзывов.\n\n"
            text += "Отзывы можно оставить после завершенных бронирований."
            
            try:
                await callback.message.edit_text(text, reply_markup=get_back_keyboard())
            except:
                await callback.message.answer(text, reply_markup=get_back_keyboard())
            return
        
        text = f"📝 <b>Мои отзывы ({len(reviews)})</b>\n\n"
        
        for review in reviews[:10]:  # Показываем первые 10
            text += f"#{review['id']} - {'⭐' * review['rating']}\n"
            if review.get('board_name'):
                text += f"Доска: {review['board_name']}\n"
            if review.get('comment'):
                comment_preview = review['comment'][:50] + "..." if len(review['comment']) > 50 else review['comment']
                text += f"Комментарий: {comment_preview}\n"
            text += f"Дата: {review['created_at']}\n\n"
        
        if len(reviews) > 10:
            text += f"... и еще {len(reviews) - 10} отзывов"
        
        try:
            await callback.message.edit_text(text, reply_markup=get_back_keyboard())
        except:
            await callback.message.answer(text, reply_markup=get_back_keyboard())

