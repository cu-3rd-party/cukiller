from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.utils.markdown import hcode

router = Router()


@router.message(F.text & ~F.text.startswith("/"))
async def bot_echo(message: types.Message):
    text = [
        "Эхо без состояния.",
        "Сообщение:",
        message.text,
    ]
    await message.answer("\n".join(text))


@router.message(F.text & ~F.text.startswith("/"))
async def bot_echo_all(message: types.Message, state: FSMContext):
    state_name = await state.get_state()
    text = [
        f"Эхо в состоянии {hcode(state_name)}",
        "Содержание сообщения:",
        hcode(message.text),
    ]
    await message.answer("\n".join(text))
