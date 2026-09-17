from aiogram import types
from aiogram.dispatcher.filters import Text
from django.conf import settings
from random import randrange

from core.apps.bot.handlers.authorization import sign_in
from core.apps.bot.keyboards import admin_kb, default_kb
from core.apps.bot.keyboards import sign_inup_kb
from core.apps.bot.loader import bot, dp
from core.apps.bot.models import TelegramUser

HELP_TEXT = """
Hello 👋, I’m a bot for selling various products! We have the following commands:

<b>Help ⭐️</b> - help with bot commands
<b>Description 📌</> -address, contact details, working hours
<b>Catalog 🛒</b> - list of products you can buy
<b>Admin 👑</b> - admin menu

But before starting, you need to <b>register or log in</b> to your profile. 
Click on the <b>Sign Up ✌️</b> or <b>Sign In 👋</b> command.
If you don't do this, some commands will be <b>unavailable</b> 🔴

We’re glad you’re using this bot ❤️
"""


async def cmd_start(message: types.Message):
    try:
        await bot.send_message(
            chat_id=message.chat.id,
            text="Hello ✋, I’m a bot for selling various products!\n\n" \
                 "You can buy anything you want here. To see the list of " \
                 "products I have, just click on the 'Catalog 🛒' command below.\n\n" \
                 "But first, <b>you need to register</b>, " \
                 "otherwise, other commands will be unavailable!\n\n" \
                 "Click on the <b>Sign Up ✌️</b> or <b>Sign In 👋</b> command.",
            reply_markup=sign_inup_kb.markup,
        )
    except:
        await message.reply(
            text="To be able to communicate with the bot, "
                 "you can send me a direct message: "
                 "https://t.me/yourbot",
        )


async def cmd_help(message: types.Message):
    await bot.send_message(chat_id=message.chat.id, text=HELP_TEXT, reply_markup=default_kb.markup)


async def cmd_description(message: types.Message):
    await bot.send_message(
        chat_id=message.chat.id,
        text="Hello ✋, we are a company that sells various products! "
             "We’re very glad you’re using our service ❤️. We work from Monday to "
             "Friday.\n9:00 AM - 9:00 PM",
    )
    await bot.send_location(
        chat_id=message.chat.id,
        latitude=randrange(1, 100),
        longitude=randrange(1, 100),
    )


async def send_all(message: types.Message):
    if sign_in['current_state']:
        if message.chat.id == settings.ADMIN_ID:
            await message.answer(f"Message: <b>{message.text[message.text.find(' '):]}</b> is being sent to all users!")
            async for user in TelegramUser.objects.filter(is_registered=True):
                await bot.send_message(chat_id=user.chat_id, text=message.text[message.text.find(' '):])
            await message.answer("All sent successfully!")
        else:
            await message.answer("You are not an administrator, and you cannot send a broadcast!")
    else:
        await message.answer(
            "You are not logged in, please try logging into your profile ‼️",
            reply_markup=sign_inup_kb.markup,
        )


async def cmd_admin(message: types.Message):
    if sign_in['current_state']:
        if message.chat.id == settings.ADMIN_ID:
            await message.answer(
                "You have entered the admin menu 🤴\n\n"
                "Below are the commands available to you 💭",
                reply_markup=admin_kb.markup,
            )
        else:
            await message.answer("You are not an administrator, and you cannot send a broadcast!")
    else:
        await message.answer(
            "You are not logged in, please try logging into your profile ‼️",
            reply_markup=sign_inup_kb.markup,
        )


async def cmd_home(message: types.Message):
    if sign_in['current_state']:
        if message.chat.id == settings.ADMIN_ID:
            await message.answer("You have entered the admin menu 🤴", reply_markup=default_kb.markup)
        else:
            await message.answer("You are not an administrator, and you cannot send a broadcast!")
    else:
        await message.answer(
            "You are not logged in, please try logging into your profile ‼️",
            reply_markup=sign_inup_kb.markup,
        )


HELP_ADMIN_TEXT = '''
Hello Administrator 🙋\n\n
Currently, you have the following commands:
- <b>Broadcast:</b> - with this command, you can send a message to all users of this bot.
Example usage: Broadcast: 'BROADCAST TEXT'
'''


async def cmd_help_admin(message: types.Message):
    if sign_in['current_state']:
        if message.chat.id == settings.ADMIN_ID:
            await message.answer(text=HELP_ADMIN_TEXT, reply_markup=admin_kb.markup)
        else:
            await message.answer("You are not an administrator, and you cannot send a broadcast!")
    else:
        await message.answer(
            "You are not logged in, please try logging into your profile ‼️",
            reply_markup=sign_inup_kb.markup,
        )


def default_handlers_register():
    dp.register_message_handler(cmd_start, commands='start')
    dp.register_message_handler(cmd_help, Text(equals='Help ⭐️'))
    dp.register_message_handler(cmd_description, Text(equals='Description 📌'))
    dp.register_message_handler(send_all, Text(contains='Broadcast:'))
    dp.register_message_handler(cmd_admin, Text(equals='Admin 👑'))
    dp.register_message_handler(cmd_home, Text(equals='Home 🏠'))
    dp.register_message_handler(cmd_help_admin, Text(equals='Help 🔔'))
