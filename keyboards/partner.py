from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

def partner_main_menu(is_approved: bool):
    kb = ReplyKeyboardBuilder()
    if is_approved:
        kb.button(text="📋 Мои доски")
        kb.button(text="📢 Мои объявления")
        kb.button(text="📊 Статистика")
        kb.button(text="⚙️ Настройки")
    else:
        kb.button(text="⏳ Ожидается одобрение")
    kb.button(text="⬅️ Главное меню")
    kb.adjust(2)
    return kb.as_markup(resize_keyboard=True)

def partner_board_confirm_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Подтвердить", callback_data="board_confirm")
    kb.button(text="❌ Отменить", callback_data="board_cancel")
    kb.adjust(2)
    return kb.as_markup()

def partner_ad_confirm_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Подтвердить", callback_data="ad_confirm")
    kb.button(text="❌ Отменить", callback_data="ad_cancel")
    kb.adjust(2)
    return kb.as_markup()
