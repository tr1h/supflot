from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

class BoardAdminStates(StatesGroup):
    deleting = State()

def register_admin_boards(router: Router, db):
    @router.message(F.text == "🔧 Управление досками")
    async def manage_boards(...): ...
    @router.callback_query(F.data.startswith("admin_board_delete:"))
    async def confirm_delete_board(...): ...
    @router.callback_query(StateFilter(BoardAdminStates.deleting), F.data == "admin_board_confirm_delete")
    async def delete_board_confirm(...): ...
    @router.callback_query(StateFilter(BoardAdminStates.deleting), F.data == "admin_board_cancel_delete")
    async def cancel_delete_board(...): ...
    @router.callback_query(F.data.startswith("admin_board_edit:"))
    async def edit_board_stub(...): ...
