"""Обработчики документации"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from core.database import Database
from keyboards.user import get_back_keyboard
from config import Config

logger = logging.getLogger(__name__)


def get_docs_menu_keyboard(user_role: str = "user") -> InlineKeyboardMarkup:
    """Меню документации в зависимости от роли"""
    buttons = []
    
    if user_role == "user":
        buttons.append([InlineKeyboardButton(text="👤 Для пользователей", callback_data="docs:user")])
    elif user_role == "partner":
        buttons.append([InlineKeyboardButton(text="💼 Для партнеров", callback_data="docs:partner")])
    elif user_role == "admin":
        buttons.append([InlineKeyboardButton(text="👤 Для пользователей", callback_data="docs:user")])
        buttons.append([InlineKeyboardButton(text="💼 Для партнеров", callback_data="docs:partner")])
        buttons.append([InlineKeyboardButton(text="🔐 Для администраторов", callback_data="docs:admin")])
    else:
        # Для всех
        buttons.append([InlineKeyboardButton(text="👤 Для пользователей", callback_data="docs:user")])
        buttons.append([InlineKeyboardButton(text="💼 Для партнеров", callback_data="docs:partner")])
    
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def register_docs_handlers(router: Router, db: Database, bot=None):
    """Регистрация обработчиков документации"""
    
    @router.message(F.text == "📖 Документация")
    async def docs_menu(message: Message):
        """Меню документации"""
        user_id = message.from_user.id
        
        # Определяем роль пользователя
        is_admin = user_id in Config.ADMIN_IDS or await db.fetchone("SELECT * FROM admins WHERE user_id = ?", (user_id,))
        is_partner = await db.fetchone("SELECT * FROM partners WHERE telegram_id = ? AND is_approved = 1", (user_id,))
        
        if is_admin:
            role = "admin"
        elif is_partner:
            role = "partner"
        else:
            role = "user"
        
        text = "📖 <b>Документация SUPFLOT</b>\n\n"
        text += "Выберите раздел документации:"
        
        await message.answer(text, reply_markup=get_docs_menu_keyboard(role))
    
    @router.callback_query(F.data == "docs:user")
    async def docs_user(callback: CallbackQuery):
        """Документация для пользователей"""
        await callback.answer()
        
        try:
            with open("docs/USER_GUIDE.md", "r", encoding="utf-8") as f:
                content = f.read()
        except FileNotFoundError:
            content = "❌ Документация для пользователей не найдена.\n\nОбратитесь к администратору: @supflot_support"
        
        # Разбиваем на части, если слишком длинная (лимит Telegram - 4096 символов)
        # Используем 3800 символов на часть, чтобы осталось место для форматирования
        max_length = 3800
        if len(content) > max_length:
            parts = []
            lines = content.split('\n')
            current_part = ""
            
            for line in lines:
                if len(current_part) + len(line) + 1 > max_length:
                    if current_part:
                        parts.append(current_part)
                    current_part = line + '\n'
                else:
                    current_part += line + '\n'
            
            if current_part:
                parts.append(current_part)
            
            # Отправляем части
            for i, part in enumerate(parts):
                if i == 0:
                    try:
                        await callback.message.edit_text(part, reply_markup=get_back_keyboard("docs:menu"), parse_mode="HTML")
                    except:
                        await callback.message.answer(part, reply_markup=get_back_keyboard("docs:menu"), parse_mode="HTML")
                else:
                    await callback.message.answer(part, parse_mode="HTML")
        else:
            try:
                await callback.message.edit_text(content, reply_markup=get_back_keyboard("docs:menu"), parse_mode="HTML")
            except:
                await callback.message.answer(content, reply_markup=get_back_keyboard("docs:menu"), parse_mode="HTML")
    
    @router.callback_query(F.data == "docs:partner")
    async def docs_partner(callback: CallbackQuery):
        """Документация для партнеров"""
        await callback.answer()
        
        try:
            with open("docs/PARTNER_GUIDE.md", "r", encoding="utf-8") as f:
                content = f.read()
        except FileNotFoundError:
            content = "❌ Документация для партнеров не найдена.\n\nОбратитесь к администратору: @supflot_support"
        
        max_length = 3800
        if len(content) > max_length:
            parts = []
            lines = content.split('\n')
            current_part = ""
            
            for line in lines:
                if len(current_part) + len(line) + 1 > max_length:
                    if current_part:
                        parts.append(current_part)
                    current_part = line + '\n'
                else:
                    current_part += line + '\n'
            
            if current_part:
                parts.append(current_part)
            
            for i, part in enumerate(parts):
                if i == 0:
                    try:
                        await callback.message.edit_text(part, reply_markup=get_back_keyboard("docs:menu"), parse_mode="HTML")
                    except:
                        await callback.message.answer(part, reply_markup=get_back_keyboard("docs:menu"), parse_mode="HTML")
                else:
                    await callback.message.answer(part, parse_mode="HTML")
        else:
            try:
                await callback.message.edit_text(content, reply_markup=get_back_keyboard("docs:menu"), parse_mode="HTML")
            except:
                await callback.message.answer(content, reply_markup=get_back_keyboard("docs:menu"), parse_mode="HTML")
    
    @router.callback_query(F.data == "docs:admin")
    async def docs_admin(callback: CallbackQuery):
        """Документация для администраторов"""
        await callback.answer()
        user_id = callback.from_user.id
        
        # Проверка прав администратора
        is_admin = user_id in Config.ADMIN_IDS or await db.fetchone("SELECT * FROM admins WHERE user_id = ?", (user_id,))
        if not is_admin:
            await callback.message.edit_text("❌ У вас нет доступа к этой документации.")
            return
        
        try:
            with open("docs/ADMIN_GUIDE.md", "r", encoding="utf-8") as f:
                content = f.read()
        except FileNotFoundError:
            content = "❌ Документация для администраторов не найдена.\n\nОбратитесь к технической поддержке."
        
        max_length = 3800
        if len(content) > max_length:
            parts = []
            lines = content.split('\n')
            current_part = ""
            
            for line in lines:
                if len(current_part) + len(line) + 1 > max_length:
                    if current_part:
                        parts.append(current_part)
                    current_part = line + '\n'
                else:
                    current_part += line + '\n'
            
            if current_part:
                parts.append(current_part)
            
            for i, part in enumerate(parts):
                if i == 0:
                    try:
                        await callback.message.edit_text(part, reply_markup=get_back_keyboard("docs:menu"), parse_mode="HTML")
                    except:
                        await callback.message.answer(part, reply_markup=get_back_keyboard("docs:menu"), parse_mode="HTML")
                else:
                    await callback.message.answer(part, parse_mode="HTML")
        else:
            try:
                await callback.message.edit_text(content, reply_markup=get_back_keyboard("docs:menu"), parse_mode="HTML")
            except:
                await callback.message.answer(content, reply_markup=get_back_keyboard("docs:menu"), parse_mode="HTML")
    
    @router.callback_query(F.data == "docs:menu")
    async def docs_menu_callback(callback: CallbackQuery):
        """Меню документации (из callback)"""
        await callback.answer()
        user_id = callback.from_user.id
        
        # Определяем роль пользователя
        is_admin = user_id in Config.ADMIN_IDS or await db.fetchone("SELECT * FROM admins WHERE user_id = ?", (user_id,))
        is_partner = await db.fetchone("SELECT * FROM partners WHERE telegram_id = ? AND is_approved = 1", (user_id,))
        
        if is_admin:
            role = "admin"
        elif is_partner:
            role = "partner"
        else:
            role = "user"
        
        text = "📖 <b>Документация SUPFLOT</b>\n\n"
        text += "Выберите раздел документации:"
        
        try:
            await callback.message.edit_text(text, reply_markup=get_docs_menu_keyboard(role))
        except:
            await callback.message.answer(text, reply_markup=get_docs_menu_keyboard(role))

