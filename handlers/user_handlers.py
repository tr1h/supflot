"""Обработчики пользовательских команд"""
import logging
from datetime import datetime
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from core.database import Database
from keyboards.user import get_main_menu, get_back_keyboard
from keyboards.partner import get_partner_menu

logger = logging.getLogger(__name__)


def register_user_handlers(router: Router, db: Database, bot=None):
    """Регистрация пользовательских обработчиков"""
    
    @router.message(Command("start"))
    async def cmd_start(message: Message, state: FSMContext):
        """Обработчик команды /start"""
        await state.clear()
        user_id = message.from_user.id
        username = message.from_user.username
        full_name = message.from_user.full_name
        
        # Регистрация/обновление пользователя
        try:
            await db.execute(
                """INSERT OR REPLACE INTO users (id, username, full_name, reg_date)
                   VALUES (?, ?, ?, CURRENT_TIMESTAMP)""",
                (user_id, username, full_name)
            )
        except Exception as e:
            logger.error(f"Error registering user: {e}")
        
        # Проверка ролей
        is_admin = await db.fetchone("SELECT * FROM admins WHERE user_id = ?", (user_id,))
        is_partner = await db.fetchone("SELECT * FROM partners WHERE telegram_id = ? AND is_approved = 1", (user_id,))
        
        welcome_text = f"👋 <b>Привет, {full_name or 'друг'}!</b>\n\n"
        welcome_text += "🏄 <b>Добро пожаловать в SUPFLOT!</b>\n\n"
        welcome_text += "🌊 <b>Платформа для аренды SUP-досок</b>\n\n"
        welcome_text += "📋 <b>Что вы можете делать:</b>\n"
        welcome_text += "• 🆕 Забронировать SUP-доску\n"
        welcome_text += "• 📋 Посмотреть свои бронирования\n"
        welcome_text += "• 📞 Связаться с нами\n\n"
        welcome_text += "💡 <b>Выберите действие из меню ниже:</b>"
        
        keyboard = get_main_menu()
        
        if is_partner:
            welcome_text += "\n\n💼 <i>У вас есть доступ к партнерской панели</i> → /partner"
        if is_admin:
            welcome_text += "\n\n🔐 <i>У вас есть доступ к админ-панели</i> → /admin"
        
        await message.answer(welcome_text, reply_markup=keyboard)
    
    @router.message(Command("help"))
    async def cmd_help(message: Message):
        """Обработчик команды /help"""
        help_text = """
📖 <b>Справка по использованию бота</b>

<b>🚀 Основные команды:</b>
/start - Главное меню
/help - Эта справка
/contacts - Контакты
/offer - Публичная оферта

<b>📅 Как забронировать доску:</b>
1️⃣ Нажмите кнопку "🆕 Новая бронь"
2️⃣ Выберите локацию из списка
3️⃣ Выберите доску для аренды
4️⃣ Выберите дату (из предложенных вариантов)
5️⃣ Выберите время начала аренды
6️⃣ Выберите длительность
7️⃣ Укажите количество досок
8️⃣ Выберите способ оплаты

<b>💳 Способы оплаты:</b>
• 💳 Telegram Pay (если настроено)
• 💳 Банковская карта (YooKassa)
• 💵 Перевод на карту
• 💵 Наличные при получении

<b>📋 Просмотр бронирований:</b>
Используйте кнопку "📋 Мои бронирования" для просмотра всех ваших активных и завершенных бронирований.

<b>💼 Для партнеров:</b>
/partner - Партнерская панель (управление локациями, досками, бронированиями)

<b>❓ Вопросы?</b>
Используйте /contacts для связи с поддержкой.
        """
        await message.answer(help_text, reply_markup=get_back_keyboard())
    
    @router.message(Command("contacts"))
    async def cmd_contacts(message: Message):
        """Обработчик команды /contacts"""
        contacts_text = """
💬 <b>Контакты поддержки</b>

Если у вас есть вопросы или возникли проблемы, свяжитесь с нами:

📧 Email: support@supflot.ru
💬 Telegram: @supflot_support

⏰ Время работы: Пн-Вс, 9:00 - 21:00

Мы всегда готовы помочь! 😊
        """
        await message.answer(contacts_text, reply_markup=get_back_keyboard())
    
    @router.message(Command("offer"))
    async def cmd_offer(message: Message):
        """Обработчик команды /offer"""
        offer_text = """
📄 <b>Публичная оферта</b>

Текст оферты будет здесь.

[Здесь должна быть ссылка на полный текст оферты]
        """
        await message.answer(offer_text, reply_markup=get_back_keyboard())
    
    @router.message(Command("partner"))
    async def cmd_partner(message: Message, state: FSMContext):
        """Обработчик команды /partner"""
        await state.clear()
        user_id = message.from_user.id
        
        # Проверка, является ли пользователь партнером
        partner = await db.fetchone(
            "SELECT * FROM partners WHERE telegram_id = ?",
            (user_id,)
        )
        
        if not partner:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            text = "💼 <b>Партнерская панель</b>\n\n"
            text += "Вы еще не зарегистрированы как партнер.\n"
            text += "Хотите стать партнером?"
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📝 Подать заявку", callback_data="partner:register")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
            ])
            await message.answer(text, reply_markup=keyboard)
            return
        
        if not partner['is_approved']:
            text = "⏳ <b>Ваша заявка на рассмотрении</b>\n\n"
            text += "Мы рассмотрим вашу заявку в ближайшее время и свяжемся с вами."
            await message.answer(text, reply_markup=get_back_keyboard())
            return
        
        if not partner['is_active']:
            text = "❌ <b>Ваш аккаунт заблокирован</b>\n\n"
            text += "Обратитесь в поддержку для выяснения причин."
            await message.answer(text, reply_markup=get_back_keyboard())
            return
        
        text = f"💼 <b>Партнерская панель</b>\n\n"
        text += f"Партнер: {partner['name']}\n"
        text += f"Комиссия: {partner['commission_percent']}%\n\n"
        text += "Выберите действие:"
        
        await message.answer(text, reply_markup=get_partner_menu())
    
    @router.callback_query(F.data == "back_to_menu")
    async def back_to_menu_handler(callback: CallbackQuery, state: FSMContext):
        """Обработчик возврата в главное меню"""
        await callback.answer()
        await state.clear()
        user_id = callback.from_user.id
        user = await db.fetchone("SELECT * FROM users WHERE id = ?", (user_id,))
        full_name = user.get('full_name', 'друг') if user else 'друг'
        
        text = f"👋 <b>Привет, {full_name}!</b>\n\n"
        text += "🏄 <b>Добро пожаловать в SUPFLOT!</b>\n\n"
        text += "🌊 <b>Платформа для аренды SUP-досок</b>\n\n"
        text += "💡 <b>Выберите действие из меню ниже:</b>"
        
        try:
            await callback.message.edit_text(text, reply_markup=get_main_menu())
        except:
            await callback.message.answer(text, reply_markup=get_main_menu())
    
    @router.message(Command("daily"))
    async def cmd_daily(message: Message):
        """Обработчик команды /daily"""
        text = "🌙 <b>Суточная аренда</b>\n\n"
        text += "Выберите доску для суточной аренды:"
        # TODO: Реализовать выбор досок для суточной аренды
        await message.answer(text, reply_markup=get_back_keyboard())
    
    @router.message(F.text == "⭐ Отзывы")
    async def reviews_menu(message: Message):
        """Обработчик кнопки Отзывы"""
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📝 Мои отзывы", callback_data="my_reviews")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
        ])
        
        text = "⭐ <b>Отзывы</b>\n\n"
        text += "Здесь вы можете:\n"
        text += "• Просмотреть свои отзывы\n"
        text += "• Оставить отзыв после завершенного бронирования\n\n"
        text += "Отзывы помогают другим пользователям выбрать лучшую доску!"
        
        await message.answer(text, reply_markup=keyboard)
    
    @router.message(F.text == "🔙 Назад")
    async def back_handler(message: Message, state: FSMContext):
        """Обработчик кнопки Назад"""
        await state.clear()
        await cmd_start(message, state)
    
    @router.message(F.text, StateFilter(None))
    async def handle_free_text(message: Message, state: FSMContext):
        """Обработчик свободных текстовых сообщений (умная поддержка через AI)"""
        # Игнорируем команды
        if message.text.startswith('/'):
            return
        
        # Игнорируем кнопки меню
        menu_texts = ["🆕 Новая бронь", "📋 Мои брони", "💬 Контакты"]
        if message.text in menu_texts:
            return
        
        user_text = message.text.strip()
        
        # Проверяем, что это похоже на вопрос (более 5 символов, содержит вопрос или обращение)
        if len(user_text) < 5:
            return
        
        try:
            from services.ai_service import get_ai_service
            from config import Config
            
            ai_service = get_ai_service()
            
            # Используем AI только если он включен и доступен
            if Config.AI_ENABLED and ai_service.enabled:
                # Собираем контекст пользователя
                user_id = message.from_user.id
                active_bookings = await db.fetchall(
                    """SELECT COUNT(*) as count FROM bookings 
                       WHERE user_id = ? AND status IN ('waiting_partner', 'active', 'waiting_card', 'waiting_cash')""",
                    (user_id,)
                )
                bookings_count = active_bookings[0]['count'] if active_bookings else 0
                
                context = {
                    "bookings_count": bookings_count
                }
                
                # Генерируем ответ через AI
                ai_response = await ai_service.generate_support_response(
                    user_message=user_text,
                    user_context=context if bookings_count > 0 else None
                )
                
                if ai_response:
                    response_text = f"🤖 {ai_response}\n\n"
                    response_text += "💡 <i>Это ответ AI-помощника. Если нужна помощь человека, используйте /contacts</i>"
                    await message.answer(response_text, reply_markup=get_back_keyboard())
                    return
            
            # Если AI недоступен, предлагаем использовать команды
            help_response = "❓ Я пока не могу понять ваш вопрос.\n\n"
            help_response += "💡 <b>Попробуйте:</b>\n"
            help_response += "• /help - Справка по боту\n"
            help_response += "• /contacts - Связаться с поддержкой\n"
            help_response += "• /start - Главное меню\n\n"
            help_response += "Или используйте кнопки меню для навигации."
            await message.answer(help_response, reply_markup=get_back_keyboard())
            
        except Exception as e:
            logger.error(f"Error in AI support handler: {e}")
            # В случае ошибки отправляем стандартный ответ
            help_response = "❓ Используйте /help для справки или /contacts для связи с поддержкой."
            await message.answer(help_response, reply_markup=get_back_keyboard())

