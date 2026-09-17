from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
btn_1 = KeyboardButton('Sign Up ✌️')
btn_2 = KeyboardButton('Sign In 👋')
btn_3 = KeyboardButton('Forgot Password? 🆘')
markup.add(btn_1).insert(btn_2).add(btn_3)
