from aiogram import types

async def main_menu():
    inline_markup = types.InlineKeyboardMarkup()
    inline_markup.add(types.InlineKeyboardButton(
            text='📖Описание бота',
            callback_data='information'
        ))
    inline_markup.add(types.InlineKeyboardButton(
            text='⚒️Сообщить о проблеме',
            callback_data='help'
        ))
    inline_markup.add(types.InlineKeyboardButton(
            text='✉️Написать отзыв',
            callback_data='otziv'
        ))
    return inline_markup

async def admin_menu():
    inline_markup = types.InlineKeyboardMarkup()
    inline_markup.add(types.InlineKeyboardButton(
            text='Написать пользователю',
            callback_data='answer'
        ))
    inline_markup.add(types.InlineKeyboardButton(
            text='Получить список нерешенных проблем',
            callback_data='spisok'
        ))
    inline_markup.add(types.InlineKeyboardButton(
            text='Получить список неотвеченных отзывов',
            callback_data='spisok_otziv'
        ))
    inline_markup.add(types.InlineKeyboardButton(
            text='Получить список Всех проблем',
            callback_data='vse_problems'
        ))
    inline_markup.add(types.InlineKeyboardButton(
            text='Получить список Всех отзывов',
            callback_data='vse_otzivi'
        ))
    inline_markup.add(types.InlineKeyboardButton(
            text='Создать рассылку',
            callback_data='create_mailing'
        ))
    inline_markup.add(types.InlineKeyboardButton(
            text='Статистика',
            callback_data='stat'
        ))
    inline_markup.add(types.InlineKeyboardButton(
            text='Вернуться в обычное меню',
            callback_data='menu'
        ))
    return inline_markup



