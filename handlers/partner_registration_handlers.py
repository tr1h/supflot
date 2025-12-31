"""Обработчики регистрации партнеров"""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from core.database import Database
from keyboards.user import get_back_keyboard
from keyboards.common import get_confirm_keyboard

logger = logging.getLogger(__name__)


class PartnerRegistrationStates(StatesGroup):
    """Состояния для регистрации партнера"""
    entering_name = State()
    entering_email = State()


def register_partner_registration_handlers(router: Router, db: Database, bot=None, notification_service=None):
    """Регистрация обработчиков регистрации партнеров"""
    
    @router.callback_query(F.data == "partner:register")
    async def partner_register_start(callback: CallbackQuery, state: FSMContext):
        """Начало регистрации партнера"""
        await callback.answer()
        user_id = callback.from_user.id
        
        # Проверяем, не является ли пользователь уже партнером
        existing_partner = await db.fetchone(
            "SELECT * FROM partners WHERE telegram_id = ?",
            (user_id,)
        )
        
        if existing_partner:
            if existing_partner['is_approved']:
                await callback.message.edit_text(
                    "✅ Вы уже являетесь партнером!",
                    reply_markup=get_back_keyboard()
                )
                return
            else:
                await callback.message.edit_text(
                    "⏳ Ваша заявка уже находится на рассмотрении.",
                    reply_markup=get_back_keyboard()
                )
                return
        
        await state.set_state(PartnerRegistrationStates.entering_name)
        
        text = "💼 <b>Регистрация партнера</b>\n\n"
        text += "Для регистрации в качестве партнера необходимо заполнить заявку.\n\n"
        text += "Введите название вашей компании/организации:"
        
        await callback.message.edit_text(text, reply_markup=get_back_keyboard())
    
    @router.message(PartnerRegistrationStates.entering_name)
    async def partner_register_name(message: Message, state: FSMContext):
        """Обработка названия партнера"""
        partner_name = message.text.strip()
        
        if not partner_name or len(partner_name) < 3:
            await message.answer("❌ Название должно содержать минимум 3 символа.")
            return
        
        await state.update_data(partner_name=partner_name)
        await state.set_state(PartnerRegistrationStates.entering_email)
        
        text = f"Название: <b>{partner_name}</b>\n\n"
        text += "Введите email для связи (или отправьте '-' чтобы пропустить):"
        await message.answer(text, reply_markup=get_back_keyboard())
    
    @router.message(PartnerRegistrationStates.entering_email)
    async def partner_register_email(message: Message, state: FSMContext):
        """Обработка email и создание заявки"""
        email = message.text.strip() if message.text.strip() != '-' else None
        
        # Валидация email (если указан)
        if email and '@' not in email:
            await message.answer("❌ Неверный формат email. Введите корректный email или '-' чтобы пропустить.")
            return
        
        data = await state.get_data()
        partner_name = data.get('partner_name')
        user_id = message.from_user.id
        
        try:
            # Создаем заявку партнера
            await db.execute(
                """INSERT INTO partners (name, contact_email, telegram_id, is_active, is_approved)
                   VALUES (?, ?, ?, 1, 0)""",
                (partner_name, email, user_id)
            )
            
            text = "✅ <b>Заявка на партнерство отправлена!</b>\n\n"
            text += f"Название: {partner_name}\n"
            if email:
                text += f"Email: {email}\n"
            text += "\nВаша заявка будет рассмотрена администратором в ближайшее время.\n"
            text += "Мы свяжемся с вами, как только примем решение."
            
            await message.answer(text, reply_markup=get_back_keyboard())
            await state.clear()
            
            # Уведомляем админов
            if bot and notification_service:
                try:
                    from config import Config
                    admin_text = f"📋 <b>Новая заявка на партнерство</b>\n\n"
                    admin_text += f"Название: {partner_name}\n"
                    admin_text += f"Telegram ID: {user_id}\n"
                    if email:
                        admin_text += f"Email: {email}\n"
                    admin_text += f"\nИспользуйте /admin для просмотра заявок."
                    
                    for admin_id in Config.ADMIN_IDS:
                        try:
                            await bot.send_message(chat_id=admin_id, text=admin_text)
                        except Exception as e:
                            logger.error(f"Error notifying admin {admin_id}: {e}")
                except Exception as e:
                    logger.error(f"Error notifying admins: {e}")
            
            logger.info(f"New partner application: {partner_name} (TG: {user_id})")
            
        except Exception as e:
            logger.error(f"Error creating partner application: {e}")
            await message.answer("❌ Ошибка при создании заявки. Попробуйте еще раз.")

