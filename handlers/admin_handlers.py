"""Обработчики админских команд"""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from core.database import Database
from keyboards.admin import get_admin_menu, get_partner_action_keyboard, get_withdraw_action_keyboard
from keyboards.user import get_back_keyboard
from keyboards.common import get_confirm_keyboard
from config import Config

logger = logging.getLogger(__name__)


def register_admin_handlers(router: Router, db: Database, bot=None, notification_service=None):
    """Регистрация админских обработчиков"""
    
    async def is_admin(user_id: int) -> bool:
        """Проверка, является ли пользователь админом"""
        if user_id in Config.ADMIN_IDS:
            return True
        admin = await db.fetchone("SELECT * FROM admins WHERE user_id = ?", (user_id,))
        return admin is not None
    
    @router.message(Command("admin"))
    async def cmd_admin(message: Message, state: FSMContext):
        """Обработчик команды /admin"""
        await state.clear()
        user_id = message.from_user.id
        
        if not await is_admin(user_id):
            await message.answer("❌ У вас нет доступа к админ-панели.")
            return
        
        text = "🔐 <b>Админ-панель</b>\n\n"
        text += "Выберите раздел для управления:"
        await message.answer(text, reply_markup=get_admin_menu())
    
    @router.callback_query(F.data == "admin:partners")
    async def admin_partners(callback: CallbackQuery):
        """Управление партнерами"""
        await callback.answer()
        user_id = callback.from_user.id
        
        if not await is_admin(user_id):
            await callback.message.edit_text("❌ У вас нет доступа.")
            return
        
        # Получаем партнеров
        partners = await db.fetchall("SELECT * FROM partners ORDER BY created_at DESC LIMIT 20")
        
        if not partners:
            await callback.message.edit_text("📋 Партнеров пока нет.", reply_markup=get_back_keyboard("back_to_admin"))
            return
        
        text = "👥 <b>Партнеры</b>\n\n"
        
        # Статистика
        approved_count = sum(1 for p in partners if p['is_approved'])
        pending_count = len(partners) - approved_count
        text += f"Всего: {len(partners)}\n"
        text += f"Одобрено: {approved_count}\n"
        text += f"На рассмотрении: {pending_count}\n\n"
        
        # Список партнеров
        buttons = []
        for partner in partners[:15]:
            status = "✅" if partner['is_approved'] else "⏳"
            status += "🔒" if not partner['is_active'] else ""
            buttons.append([InlineKeyboardButton(
                text=f"{status} {partner['name']} (ID: {partner['id']})",
                callback_data=f"admin:partner_detail:{partner['id']}"
            )])
        
        buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_admin")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        await callback.message.edit_text(text, reply_markup=keyboard)
    
    @router.callback_query(F.data.startswith("admin:partner_detail:"))
    async def admin_partner_detail(callback: CallbackQuery):
        """Детали партнера"""
        await callback.answer()
        partner_id = int(callback.data.split(":")[-1])
        
        partner = await db.fetchone("SELECT * FROM partners WHERE id = ?", (partner_id,))
        
        if not partner:
            await callback.message.edit_text("❌ Партнер не найден.")
            return
        
        # Статистика партнера
        locations_count = await db.fetchone(
            "SELECT COUNT(*) as count FROM locations WHERE partner_id = ?",
            (partner_id,)
        )
        boards_count = await db.fetchone(
            "SELECT COUNT(*) as count FROM boards WHERE partner_id = ?",
            (partner_id,)
        )
        bookings_count = await db.fetchone(
            "SELECT COUNT(*) as count FROM bookings WHERE partner_id = ?",
            (partner_id,)
        )
        
        # Баланс партнера
        wallet_ops = await db.fetchall(
            """SELECT 
                   SUM(CASE WHEN type = 'credit' THEN amount ELSE 0 END) as credits,
                   SUM(CASE WHEN type = 'debit' THEN amount ELSE 0 END) as debits
               FROM partner_wallet_ops 
               WHERE partner_id = ?""",
            (partner_id,)
        )
        balance = (wallet_ops[0]['credits'] or 0) - (wallet_ops[0]['debits'] or 0)
        
        text = f"👤 <b>Партнер: {partner['name']}</b>\n\n"
        text += f"ID: {partner['id']}\n"
        text += f"Telegram ID: {partner['telegram_id']}\n"
        text += f"Email: {partner.get('contact_email', 'Не указан')}\n"
        text += f"Комиссия: {partner['commission_percent']}%\n"
        text += f"Статус: {'✅ Одобрен' if partner['is_approved'] else '⏳ На рассмотрении'}\n"
        text += f"Активен: {'✅ Да' if partner['is_active'] else '❌ Нет'}\n\n"
        text += f"📊 Статистика:\n"
        text += f"  Локаций: {locations_count['count']}\n"
        text += f"  Досок: {boards_count['count']}\n"
        text += f"  Бронирований: {bookings_count['count']}\n"
        text += f"  Баланс: {balance:.2f}₽\n"
        
        keyboard = get_partner_action_keyboard(partner_id)
        await callback.message.edit_text(text, reply_markup=keyboard)
    
    @router.callback_query(F.data.startswith("admin:partner_approve:"))
    async def admin_partner_approve(callback: CallbackQuery):
        """Одобрение партнера"""
        await callback.answer()
        user_id = callback.from_user.id
        
        if not await is_admin(user_id):
            return
        
        partner_id = int(callback.data.split(":")[-1])
        
        try:
            await db.execute(
                "UPDATE partners SET is_approved = 1, is_active = 1 WHERE id = ?",
                (partner_id,)
            )
            partner = await db.fetchone("SELECT * FROM partners WHERE id = ?", (partner_id,))
            
            await callback.message.edit_text(
                f"✅ Партнер {partner['name']} одобрен!",
                reply_markup=get_back_keyboard(f"admin:partner_detail:{partner_id}")
            )
            
            # Отправляем уведомление партнеру
            if notification_service:
                try:
                    await notification_service.notify_partner_approved(partner_id)
                except Exception as e:
                    logger.error(f"Error sending notification to partner: {e}")
            
        except Exception as e:
            logger.error(f"Error approving partner: {e}")
            await callback.message.edit_text("❌ Ошибка при одобрении партнера.")
    
    @router.callback_query(F.data.startswith("admin:partner_reject:"))
    async def admin_partner_reject(callback: CallbackQuery):
        """Отклонение партнера"""
        await callback.answer()
        user_id = callback.from_user.id
        
        if not await is_admin(user_id):
            return
        
        partner_id = int(callback.data.split(":")[-1])
        
        try:
            partner = await db.fetchone("SELECT * FROM partners WHERE id = ?", (partner_id,))
            
            keyboard = get_confirm_keyboard(
                f"admin:partner_reject_confirm:{partner_id}",
                f"admin:partner_detail:{partner_id}"
            )
            
            await callback.message.edit_text(
                f"⚠️ Вы уверены, что хотите отклонить заявку партнера {partner['name']}?",
                reply_markup=keyboard
            )
            
        except Exception as e:
            logger.error(f"Error rejecting partner: {e}")
    
    @router.callback_query(F.data.startswith("admin:partner_reject_confirm:"))
    async def admin_partner_reject_confirm(callback: CallbackQuery):
        """Подтверждение отклонения партнера"""
        await callback.answer()
        partner_id = int(callback.data.split(":")[-1])
        
        try:
            await db.execute("DELETE FROM partners WHERE id = ?", (partner_id,))
            await callback.message.edit_text(
                f"✅ Заявка партнера отклонена и удалена.",
                reply_markup=get_back_keyboard("admin:partners")
            )
        except Exception as e:
            logger.error(f"Error rejecting partner: {e}")
            await callback.message.edit_text("❌ Ошибка при отклонении партнера.")
    
    @router.callback_query(F.data.startswith("admin:partner_block:"))
    async def admin_partner_block(callback: CallbackQuery):
        """Блокировка/разблокировка партнера"""
        await callback.answer()
        partner_id = int(callback.data.split(":")[-1])
        
        partner = await db.fetchone("SELECT * FROM partners WHERE id = ?", (partner_id,))
        new_status = 0 if partner['is_active'] else 1
        
        try:
            await db.execute(
                "UPDATE partners SET is_active = ? WHERE id = ?",
                (new_status, partner_id)
            )
            
            action = "заблокирован" if new_status == 0 else "разблокирован"
            await callback.message.edit_text(
                f"✅ Партнер {partner['name']} {action}!",
                reply_markup=get_back_keyboard(f"admin:partner_detail:{partner_id}")
            )
        except Exception as e:
            logger.error(f"Error blocking partner: {e}")
    
    @router.callback_query(F.data == "admin:finance")
    async def admin_finance(callback: CallbackQuery):
        """Финансы"""
        await callback.answer()
        user_id = callback.from_user.id
        
        if not await is_admin(user_id):
            return
        
        # Получаем запросы на вывод
        requests = await db.fetchall(
            """SELECT pwr.*, p.name as partner_name 
               FROM partner_withdraw_requests pwr
               JOIN partners p ON pwr.partner_id = p.id
               WHERE pwr.status = 'pending'
               ORDER BY pwr.created_at DESC"""
        )
        
        text = "💰 <b>Финансы</b>\n\n"
        
        if requests:
            text += f"<b>Запросы на вывод ({len(requests)}):</b>\n\n"
            
            buttons = []
            for req in requests[:10]:
                text += f"💵 {req['partner_name']}: {req['amount']:.2f}₽ (ID: {req['id']})\n"
                buttons.append([InlineKeyboardButton(
                    text=f"💵 {req['partner_name']} - {req['amount']:.2f}₽",
                    callback_data=f"admin:withdraw_detail:{req['id']}"
                )])
            
            buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_admin")])
            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
            await callback.message.edit_text(text, reply_markup=keyboard)
        else:
            text += "Нет запросов на вывод."
            await callback.message.edit_text(text, reply_markup=get_back_keyboard("back_to_admin"))
    
    @router.callback_query(F.data.startswith("admin:withdraw_detail:"))
    async def admin_withdraw_detail(callback: CallbackQuery):
        """Детали запроса на вывод"""
        await callback.answer()
        request_id = int(callback.data.split(":")[-1])
        
        request = await db.fetchone(
            """SELECT pwr.*, p.name as partner_name, p.telegram_id 
               FROM partner_withdraw_requests pwr
               JOIN partners p ON pwr.partner_id = p.id
               WHERE pwr.id = ?""",
            (request_id,)
        )
        
        if not request:
            await callback.message.edit_text("❌ Запрос не найден.")
            return
        
        text = f"💵 <b>Запрос на вывод #{request_id}</b>\n\n"
        text += f"Партнер: {request['partner_name']}\n"
        text += f"Сумма: {request['amount']:.2f}₽\n"
        text += f"Статус: {request['status']}\n"
        text += f"Дата: {request['created_at']}\n"
        
        keyboard = get_withdraw_action_keyboard(request_id)
        await callback.message.edit_text(text, reply_markup=keyboard)
    
    @router.callback_query(F.data.startswith("admin:withdraw_approve:"))
    async def admin_withdraw_approve(callback: CallbackQuery):
        """Одобрение вывода"""
        await callback.answer()
        request_id = int(callback.data.split(":")[-1])
        
        request = await db.fetchone(
            "SELECT * FROM partner_withdraw_requests WHERE id = ?",
            (request_id,)
        )
        
        if not request:
            await callback.message.edit_text("❌ Запрос не найден.")
            return
        
        # Проверяем баланс партнера
        wallet_ops = await db.fetchall(
            """SELECT 
                   SUM(CASE WHEN type = 'credit' THEN amount ELSE 0 END) as credits,
                   SUM(CASE WHEN type = 'debit' THEN amount ELSE 0 END) as debits
               FROM partner_wallet_ops 
               WHERE partner_id = ?""",
            (request['partner_id'],)
        )
        balance = (wallet_ops[0]['credits'] or 0) - (wallet_ops[0]['debits'] or 0)
        
        if balance < request['amount']:
            await callback.message.edit_text(
                f"❌ Недостаточно средств. Баланс: {balance:.2f}₽, запрошено: {request['amount']:.2f}₽",
                reply_markup=get_back_keyboard(f"admin:withdraw_detail:{request_id}")
            )
            return
        
        try:
            # Обновляем статус запроса
            await db.execute(
                "UPDATE partner_withdraw_requests SET status = 'approved' WHERE id = ?",
                (request_id,)
            )
            
            # Создаем операцию списания
            await db.execute(
                """INSERT INTO partner_wallet_ops (partner_id, type, amount, src)
                   VALUES (?, 'debit', ?, ?)""",
                (request['partner_id'], request['amount'], f"Вывод средств (запрос #{request_id})")
            )
            
            await callback.message.edit_text(
                f"✅ Вывод {request['amount']:.2f}₽ одобрен и выполнен!",
                reply_markup=get_back_keyboard("admin:finance")
            )
            
        except Exception as e:
            logger.error(f"Error approving withdraw: {e}")
            await callback.message.edit_text("❌ Ошибка при одобрении вывода.")
    
    @router.callback_query(F.data.startswith("admin:withdraw_reject:"))
    async def admin_withdraw_reject(callback: CallbackQuery):
        """Отклонение вывода"""
        await callback.answer()
        request_id = int(callback.data.split(":")[-1])
        
        try:
            await db.execute(
                "UPDATE partner_withdraw_requests SET status = 'rejected' WHERE id = ?",
                (request_id,)
            )
            
            await callback.message.edit_text(
                "✅ Запрос на вывод отклонен.",
                reply_markup=get_back_keyboard("admin:finance")
            )
        except Exception as e:
            logger.error(f"Error rejecting withdraw: {e}")
            await callback.message.edit_text("❌ Ошибка при отклонении вывода.")
    
    @router.callback_query(F.data == "admin:bookings")
    async def admin_bookings(callback: CallbackQuery):
        """Управление бронированиями"""
        await callback.answer()
        user_id = callback.from_user.id
        
        if not await is_admin(user_id):
            return
        
        # Статистика бронирований
        stats = await db.fetchall(
            """SELECT status, COUNT(*) as count 
               FROM bookings 
               GROUP BY status"""
        )
        
        # Последние бронирования
        bookings = await db.fetchall(
            """SELECT * FROM bookings 
               ORDER BY created_at DESC 
               LIMIT 20"""
        )
        
        text = "📋 <b>Бронирования</b>\n\n"
        text += "<b>Статистика:</b>\n"
        for stat in stats:
            text += f"  {stat['status']}: {stat['count']}\n"
        
        text += "\n<b>Последние бронирования:</b>\n\n"
        
        buttons = []
        for booking in bookings[:10]:
            status_icon = "⏳" if booking['status'] == "waiting_partner" else "✅"
            buttons.append([InlineKeyboardButton(
                text=f"{status_icon} #{booking['id']} - {booking['board_name']}",
                callback_data=f"admin:booking_detail:{booking['id']}"
            )])
        
        buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_admin")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        await callback.message.edit_text(text, reply_markup=keyboard)
    
    @router.callback_query(F.data.startswith("admin:booking_detail:"))
    async def admin_booking_detail(callback: CallbackQuery):
        """Детали бронирования для админа"""
        await callback.answer()
        booking_id = int(callback.data.split(":")[-1])
        
        booking = await db.fetchone(
            "SELECT * FROM bookings WHERE id = ?",
            (booking_id,)
        )
        
        if not booking:
            await callback.message.edit_text("❌ Бронирование не найдено.")
            return
        
        user = await db.fetchone("SELECT * FROM users WHERE id = ?", (booking['user_id'],))
        partner = None
        if booking.get('partner_id'):
            partner = await db.fetchone("SELECT * FROM partners WHERE id = ?", (booking['partner_id'],))
        
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
            text += f"Telegram ID: {user['id']}\n"
        
        if partner:
            text += f"\nПартнер: {partner['name']}\n"
        
        buttons = [[InlineKeyboardButton(text="🔙 Назад", callback_data="admin:bookings")]]
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        await callback.message.edit_text(text, reply_markup=keyboard)
    
    @router.callback_query(F.data == "admin:reviews")
    async def admin_reviews(callback: CallbackQuery):
        """Модерация отзывов"""
        await callback.answer()
        user_id = callback.from_user.id
        
        if not await is_admin(user_id):
            await callback.message.edit_text("❌ У вас нет доступа.")
            return
        
        from services.review_service import ReviewService
        review_service = ReviewService(db)
        
        # Получаем все отзывы (последние 50)
        reviews = await db.fetchall("""
            SELECT r.*, u.full_name, u.username, b.board_name 
            FROM reviews r
            JOIN users u ON r.user_id = u.id
            LEFT JOIN bookings b ON r.booking_id = b.id
            ORDER BY r.created_at DESC
            LIMIT 50
        """)
        
        text = "⭐ <b>Модерация отзывов</b>\n\n"
        text += f"Всего отзывов: {len(reviews)}\n\n"
        text += "Последние отзывы:\n\n"
        
        buttons = []
        for review in reviews[:15]:
            stars = "⭐" * review['rating']
            user_name = review.get('full_name', f"User {review['user_id']}")
            preview = f"{stars} от {user_name}"
            if review.get('comment'):
                comment_preview = review['comment'][:30] + "..." if len(review['comment']) > 30 else review['comment']
                preview += f": {comment_preview}"
            
            buttons.append([InlineKeyboardButton(
                text=preview,
                callback_data=f"admin:review_detail:{review['id']}"
            )])
        
        buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_admin")])
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        try:
            await callback.message.edit_text(text, reply_markup=keyboard)
        except:
            await callback.message.answer(text, reply_markup=keyboard)
    
    @router.callback_query(F.data.startswith("admin:review_detail:"))
    async def admin_review_detail(callback: CallbackQuery):
        """Детали отзыва для модерации"""
        await callback.answer()
        user_id = callback.from_user.id
        review_id = int(callback.data.split(":")[-1])
        
        if not await is_admin(user_id):
            await callback.message.edit_text("❌ У вас нет доступа.")
            return
        
        review = await db.fetchone("""
            SELECT r.*, u.full_name, u.username, b.board_name, b.date as booking_date
            FROM reviews r
            JOIN users u ON r.user_id = u.id
            LEFT JOIN bookings b ON r.booking_id = b.id
            WHERE r.id = ?
        """, (review_id,))
        
        if not review:
            await callback.message.edit_text("❌ Отзыв не найден.")
            return
        
        stars = "⭐" * review['rating']
        text = f"⭐ <b>Отзыв #{review_id}</b>\n\n"
        text += f"Оценка: {stars} ({review['rating']}/5)\n\n"
        text += f"Пользователь: {review.get('full_name', 'Не указано')}\n"
        if review.get('username'):
            text += f"Username: @{review['username']}\n"
        text += f"User ID: {review['user_id']}\n\n"
        
        if review.get('board_name'):
            text += f"Доска: {review['board_name']}\n"
        if review.get('booking_date'):
            text += f"Дата бронирования: {review['booking_date']}\n"
        text += f"Дата отзыва: {review['created_at']}\n\n"
        
        if review.get('comment'):
            text += f"<b>Комментарий:</b>\n{review['comment']}\n"
        else:
            text += "Комментарий отсутствует\n"
        
        buttons = [
            [InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"admin:review_delete:{review_id}")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin:reviews")],
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        try:
            await callback.message.edit_text(text, reply_markup=keyboard)
        except:
            await callback.message.answer(text, reply_markup=keyboard)
    
    @router.callback_query(F.data.startswith("admin:review_delete:"))
    async def admin_review_delete(callback: CallbackQuery):
        """Удаление отзыва"""
        await callback.answer()
        user_id = callback.from_user.id
        review_id = int(callback.data.split(":")[-1])
        
        if not await is_admin(user_id):
            await callback.message.edit_text("❌ У вас нет доступа.")
            return
        
        review = await db.fetchone("SELECT * FROM reviews WHERE id = ?", (review_id,))
        if not review:
            await callback.message.edit_text("❌ Отзыв не найден.")
            return
        
        keyboard = get_confirm_keyboard(
            f"admin:review_delete_confirm:{review_id}",
            f"admin:review_detail:{review_id}"
        )
        
        text = f"⚠️ <b>Удаление отзыва #{review_id}</b>\n\n"
        text += f"Оценка: {'⭐' * review['rating']}/5\n"
        if review.get('comment'):
            text += f"Комментарий: {review['comment'][:50]}...\n"
        text += "\nВы уверены, что хотите удалить этот отзыв?"
        
        try:
            await callback.message.edit_text(text, reply_markup=keyboard)
        except:
            await callback.message.answer(text, reply_markup=keyboard)
    
    @router.callback_query(F.data.startswith("admin:review_delete_confirm:"))
    async def admin_review_delete_confirm(callback: CallbackQuery):
        """Подтверждение удаления отзыва"""
        await callback.answer()
        user_id = callback.from_user.id
        review_id = int(callback.data.split(":")[-1])
        
        if not await is_admin(user_id):
            await callback.message.edit_text("❌ У вас нет доступа.")
            return
        
        try:
            await db.execute("DELETE FROM reviews WHERE id = ?", (review_id,))
            text = f"✅ Отзыв #{review_id} удален!"
            keyboard = get_back_keyboard("admin:reviews")
            try:
                await callback.message.edit_text(text, reply_markup=keyboard)
            except:
                await callback.message.answer(text, reply_markup=keyboard)
        except Exception as e:
            logger.error(f"Error deleting review: {e}")
            await callback.message.edit_text("❌ Ошибка при удалении отзыва.")
    
    @router.callback_query(F.data == "back_to_admin")
    async def back_to_admin(callback: CallbackQuery, state: FSMContext):
        """Возврат в админ-меню"""
        await callback.answer()
        await state.clear()
        text = "🔐 <b>Админ-панель</b>\n\n"
        text += "Выберите раздел для управления:"
        await callback.message.edit_text(text, reply_markup=get_admin_menu())

