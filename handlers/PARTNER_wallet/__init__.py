# handlers/PARTNER_wallet/__init__.py

from aiogram import Router

# В wallet_handlers.py у нас создаётся просто `router = Router()`,
# поэтому импортим его под именем wallet_router
from .wallet_handlers import router as wallet_router

from .earnings import earnings_router
from .referral_handlers import referral_router
from .withdraw_handlers import withdraw_router

def register_partner_wallet(dp: Router, db):
    dp.include_router(wallet_router)
    dp.include_router(earnings_router)
    dp.include_router(referral_router)
    dp.include_router(withdraw_router)

    # Передаём доступ к базе в earnings
    earnings_router.data["db"] = db
