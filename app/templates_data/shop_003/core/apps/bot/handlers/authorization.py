import re

from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from asgiref.sync import sync_to_async
from django.contrib.auth.hashers import make_password, check_password

from core.apps.bot.keyboards import default_kb
from core.apps.bot.keyboards import sign_inup_kb
from core.apps.bot.keyboards.registration_kb import markup, markup_cancel_forgot_password
from core.apps.bot.loader import dp
from core.apps.bot.models import TelegramUser
from core.apps.bot.states import AuthState, SignInState, ForgotPasswordState

new_user = {}
sign_in = {'current_state': False}
update_data = {}

REGISTRATION_TEXT = """
To register, first write your username!

What should the username consist of?
    - The username should only contain <b>Latin letters</b>!
    - The username must be <b>longer than 3 characters (letters and numbers)</b>
    - The username must be <b>unique and non-repetitive</b>

Before submitting your username, double-check it!
"""


async def command_cancel(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        return
    await state.finish()
    await message.answer(text="The operation was successfully canceled 🙅‍", reply_markup=sign_inup_kb.markup)


async def process_registration(message: types.Message):
    await message.answer(REGISTRATION_TEXT, reply_markup=markup)
    await AuthState.user_login.set()


async def process_login(message: types.Message, state: FSMContext):
    login = message.text
    if not await check_users_chat_id(chat_id=message.chat.id):
        if not await check_user(login=login):
            if re.match('^[A-Za-z]+$', login) and len(login) > 3:
                async with state.proxy() as data:
                    data['login'] = login
                    new_user['user_login'] = data['login']
                await message.answer("Now, please enter your password ✍️", reply_markup=markup)
                await AuthState.user_password.set()
            else:
                await message.answer(
                    "The username should only consist of <b>Latin letters and must be more than 3 characters 🔡</b>\n\n"
                    "Please try again ↩️!",
                    reply_markup=markup,
                )
                await AuthState.user_login.set()
        else:
            await message.answer(
                "A user with this username <b>already exists</b>, please try again ↩️",
                reply_markup=markup,
            )
            await AuthState.user_login.set()
    else:
        await message.answer(
            "A user with the same ID as yours already exists, please log into your account 🫡",
            reply_markup=sign_inup_kb.markup,
        )


async def process_password(message: types.Message, state: FSMContext):
    if len(message.text) > 5 and re.match('^[a-zA-Z0-9]+$', message.text) and \
            any(digit.isdigit() for digit in message.text):
        async with state.proxy() as data:
            data['password'] = message.text
        await message.answer("Please enter the password <b>again</b> 🔄", reply_markup=markup)
        await AuthState.user_password_2.set()
    else:
        await message.answer(
            "The password must only consist of <b>Latin letters</b> "
            "and contain at least <b>one digit</b>\n\n"
            "Please try again 🔄",
            reply_markup=markup,
        )
        await AuthState.user_password.set()


async def process_password_2(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['password_2'] = message.text
        new_user['user_password'] = data['password_2']
        if data['password'] == data['password_2']:
            new_user['chat_id'] = message.chat.id
            await save_user()
            await state.finish()
            await message.answer(
                "Registration was <b>successful</b> ✅\n\n"
                "Now, please log into your profile 💝",
                reply_markup=sign_inup_kb.markup,
            )
        else:
            await message.answer(
                "You entered the password <b>incorrectly</b> ❌\n\n"
                "Please try again 🔄",
                reply_markup=markup,
            )
            await AuthState.user_password.set()


async def command_sign_in(message: types.Message):
    await message.answer("Please enter your username ✨", reply_markup=markup)
    await SignInState.login.set()


async def process_sign_in(message: types.Message, state: FSMContext):
    if await check_user(message.text):
        async with state.proxy() as sign_in_data:
            sign_in_data['login'] = message.text
            sign_in['login'] = sign_in_data['login']
        await message.answer("Now, you need to enter your password 🔐", reply_markup=markup_cancel_forgot_password)
        await SignInState.password.set()
    else:
        await message.answer("This username <b>does not exist</b>, please try again ❌", reply_markup=markup)
        await SignInState.login.set()


async def process_pass(message: types.Message, state: FSMContext):
    async with state.proxy() as sign_in_data:
        sign_in_data['password'] = message.text
        sign_in['password'] = sign_in_data['password']
        sign_in['current_state'] = True
        if await get_password(username=sign_in['login'], password=sign_in['password']):
            await message.answer("Login was <b>successful</b> ⭐️", reply_markup=default_kb.markup)
            await state.finish()
        else:
            await message.answer(
                "The password is <b>incorrect</b>, please try again 🔄",
                reply_markup=markup_cancel_forgot_password,
            )
            await SignInState.password.set()


async def forgot_password(message: types.Message):
    await message.answer("To change your password, first enter your username 🫡", reply_markup=markup)
    await ForgotPasswordState.user_login.set()


async def process_forgot_password_login(message: types.Message, state: FSMContext):
    if await check_login_chat_id(login=message.text, chat_id=message.chat.id):
        await message.answer(
            "The username was <b>successfully</b> found, "
            "and the user ID matches the username 🌟\n\n"
            "Now, you <b>can</b> change your password ✅\n\n"
            "Please enter your <b>new password</b> ✍️",
            reply_markup=markup,
        )
        update_data['user_login'] = message.text
        await ForgotPasswordState.user_password.set()
    else:
        await message.answer(
            "You <b>did not pass the check</b> ❌\n\n"
            "There could be two reasons for this:\n"
            "1. This username does not exist\n"
            "2. Your user ID does not match the username you provided\n\n"
            "You can <b>try again</b> 🔄",
            reply_markup=sign_inup_kb.markup,
        )
        await state.finish()


async def process_forgot_password_password(message: types.Message, state: FSMContext):
    if len(message.text) > 5 and re.match('^[a-zA-Z0-9]+$', message.text) and \
            any(digit.isdigit() for digit in message.text):
        async with state.proxy() as forgot_password_data:
            forgot_password_data['user_password'] = message.text
            update_data['user_password'] = forgot_password_data['user_password']
        await message.answer("Please enter the password <b>again</b> 🔄", reply_markup=markup)
        await ForgotPasswordState.user_password_2.set()
    else:
        await message.answer(
            "The password must only consist of <b>Latin letters</b> "
            "and contain at least <b>one digit</b>\n\n"
            "Please try again 🔄",
            reply_markup=markup,
        )
        await ForgotPasswordState.user_password.set()


async def process_forgot_password_password_2(message: types.Message, state: FSMContext):
    async with state.proxy() as forgot_password_data:
        forgot_password_data['user_password_2'] = message.text
        update_data['user_password'] = forgot_password_data['user_password_2']
        if forgot_password_data['user_password'] == forgot_password_data['user_password_2']:
            await update_user_password(login=update_data['user_login'], password=update_data['user_password'])
            await state.finish()
            await message.answer(
                "Password change was <b>successful</b> ✅\n\n"
                "Now, please log into your profile 💝",
                reply_markup=sign_inup_kb.markup,
            )
        else:
            await message.answer(
                "You entered the password <b>incorrectly</b> ❌\n\n"
                "Please try again 🔄",
                reply_markup=markup,
            )
            await ForgotPasswordState.user_password.set()


@sync_to_async
def save_user():
    user = TelegramUser.objects.create(
        user_login=new_user['user_login'],
        user_password=make_password(new_user['user_password']),
        is_registered=True,
        chat_id=new_user['chat_id'],
    )
    return user


@sync_to_async
def update_user_password(login, password):
    user = TelegramUser.objects.filter(user_login=login).update(user_password=make_password(password))
    return user


@sync_to_async
def get_password(username, password):
    user = TelegramUser.objects.get(user_login=username)
    if check_password(password, user.user_password):
        return True
    else:
        return False


@sync_to_async
def check_user(login):
    return TelegramUser.objects.filter(user_login=login).exists()


@sync_to_async
def check_login_chat_id(login, chat_id):
    return TelegramUser.objects.filter(user_login=login, chat_id=chat_id).exists()


@sync_to_async
def check_users_chat_id(chat_id):
    return TelegramUser.objects.filter(chat_id=chat_id).exists()


def authorization_handlers_register():
    dp.register_message_handler(command_cancel, Text(equals='Cancel ❌', ignore_case=True), state='*')
    dp.register_message_handler(process_registration, Text(equals='Sign Up ✌️'), state='*')
    dp.register_message_handler(process_login, state=AuthState.user_login)
    dp.register_message_handler(process_password, state=AuthState.user_password)
    dp.register_message_handler(process_password_2, state=AuthState.user_password_2)
    dp.register_message_handler(forgot_password, Text(equals='Forgot Password? 🆘'), state='*')
    dp.register_message_handler(process_forgot_password_login, state=ForgotPasswordState.user_login)
    dp.register_message_handler(process_forgot_password_password, state=ForgotPasswordState.user_password)
    dp.register_message_handler(process_forgot_password_password_2, state=ForgotPasswordState.user_password_2)
    dp.register_message_handler(command_sign_in, Text(equals='Sign In 👋'))
    dp.register_message_handler(process_sign_in, state=SignInState.login)
    dp.register_message_handler(process_pass, state=SignInState.password)
