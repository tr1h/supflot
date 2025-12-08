# handlers/NEW_user_bundle.py
# -*- coding: utf-8 -*-
from aiogram import Router

# 1) /start, /help
from .NEW_main_handlers     import register_main_handlers
# 2) Меню выбора сценария бронирования (внутри него подключаются instant, regular, daily)
from .NEW_booking_entry     import register_booking_entry
# 3) Предварительная почасовая бронь
from .NEW_regular_booking   import register_regular_booking
# 4) Мгновенная аренда “у воды”
from .NEW_instant_booking   import register_instant_booking
# 5) Суточная аренда через “как авто”
from .NEW_daily_booking_p2p     import register_daily_booking

def register_user_handlers(router: Router, db):
    """
    Регистрирует все пользовательские сценарии: /start, меню выбора,
    почасовая, мгновенная и суточная аренда.
    """
    register_main_handlers(router)
    register_booking_entry(router, db)
    register_regular_booking(router, db)
    register_instant_booking(router, db)
    register_daily_booking(router, db)
