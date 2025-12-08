# handlers/NEW_admin_bundle.py
from aiogram import Router

from handlers.NEW_admin_main       import register_admin_main
from handlers.NEW_admin_users      import register_admin_users
from handlers.NEW_admin_locations  import register_admin_locations
from handlers.NEW_admin_boards     import register_admin_boards
from handlers.NEW_admin_finance    import register_admin_finance
from handlers.NEW_admin_approvals  import register_admin_approvals
from handlers.NEW_admin_payments   import register_admin_payments
from handlers.admin_bookings_handlers import register_admin_bookings


def register_all_admin_handlers(parent: Router, db, bot) -> None:
    """
    Регистрирует все админские модули на переданный parent Router.
    Никаких глобальных router'ов из модулей мы не импортируем!
    """

    # создаём подроутеры (можно с именами для дебага)
    r_main       = Router(name="admin_main")
    r_users      = Router(name="admin_users")
    r_locations  = Router(name="admin_locations")
    r_boards     = Router(name="admin_boards")
    r_finance    = Router(name="admin_finance")
    r_approvals  = Router(name="admin_approvals")
    r_payments   = Router(name="admin_payments")
    r_bookings   = Router(name="admin_bookings")

    # регистрируем хэндлеры в эти подроутеры
    register_admin_main(r_main, db)
    register_admin_users(r_users, db)
    register_admin_locations(r_locations, db)
    register_admin_boards(r_boards, db, bot)
    register_admin_finance(r_finance, db)
    register_admin_approvals(r_approvals, db, bot)
    register_admin_payments(r_payments, db)
    register_admin_bookings(r_bookings, db)

    # включаем подроутеры в родительский
    parent.include_router(r_main)
    parent.include_router(r_users)
    parent.include_router(r_locations)
    parent.include_router(r_boards)
    parent.include_router(r_finance)
    parent.include_router(r_approvals)
    parent.include_router(r_payments)
    parent.include_router(r_bookings)
