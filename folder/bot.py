import logging
from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext
from aiogram.utils.exceptions import ChatNotFound
import asyncio
from fastapi import FastAPI
from uvicorn import run
from aiogram.types import InputFile
from aiogram.utils import executor
import os
import csv
from datetime import datetime

from settings import bot_settings
from bot_menu import menu
import orm

logging.basicConfig(level=logging.INFO)

bot = Bot(token=bot_settings.BOT_TOKEN, parse_mode=types.ParseMode.HTML)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello, World!"}


# Состояния
class Form(StatesGroup):
    waiting_message = State()


class Mailing(StatesGroup):
    text = State()
    entity = State()


class Support(StatesGroup):
    waiting_for_message = State()
    waiting_for_reply = State()
    waiting_for_otziv = State()
    waiting_for_otvet = State()
    waiting_for_otvet_end = State()
    # для кнопки в админ меню
    waiting_for_user_id = State()
    waiting_for_reply2 = State()
    waiting_for_send = State()


async def set_default_commands(dp):
    await dp.bot.set_my_commands(
        [
            types.BotCommand('start', 'Перезапустить бота'),
        ]
    )


GROUP_CHAT_ID = -4719535439
GROUP2 = -4634508702
active_chat_processing = False


@dp.message_handler(commands=['start'])
async def start_message(message: types.Message):
    text = f'Приветствуем Вас, *{message.from_user.first_name}*!\n\nНаш бот поможет разобраться в проблеме, связанной с ИИ ботом!\n Главное меню:'
    inline_markup = await menu.main_menu()
    response = orm.add_user(message.from_user.id, message.from_user.username)
    username = message.from_user.username
    if response == 1:
        users = orm.get_admins()
        for user in users:
            if message.from_user.username == None:
                await bot.send_message(user.tg_id,
                                       text=f'Пользователь <a href="tg://user?id={message.from_user.id}">@{message.from_user.first_name}</a> присоединился',
                                       parse_mode='HTML')
            elif message.from_user.username != None:
                await bot.send_message(user.tg_id,
                                       text=f'Пользователь <a href="tg://user?id={message.from_user.id}">@{username}</a> присоединился',
                                       parse_mode='HTML')
            else:
                await bot.send_message(user.tg_id,
                                       text=f'Пользователь <a href="tg://user?id={message.from_user.id}">@{username}</a> присоединился',
                                       parse_mode='HTML')

    await message.answer(text, reply_markup=inline_markup, parse_mode='Markdown')
    # await message.answer(f"ID вашего чата: {message.chat.id}")
    # print(f"Chat ID: {message.chat.id}")
    await set_default_commands(dp)


@dp.message_handler(lambda message: orm.check_admin(message.from_user.id) == 1 and message.text == '/admin')
async def get_admin_menu(message: types.Message):
    text = 'Выберите необходимое действие'
    inline_markup = await menu.admin_menu()
    await message.answer(text, reply_markup=inline_markup)


@dp.callback_query_handler(lambda c: c.data == 'answer')
async def handle_reply_button(callback_query: types.CallbackQuery):
    await callback_query.message.answer("Введите ID пользователя для ответа:")
    await Support.waiting_for_user_id.set()


@dp.message_handler(state=Support.waiting_for_user_id)
async def get_user_id(message: types.Message, state: FSMContext):
    user_id = message.text
    try:
        user_id = int(user_id)  # Проверяем, что это целое число
        await state.update_data(user_id=user_id, admin_id=message.from_user.id)
        await message.answer(f"Вы выбрали ID: {user_id}. Теперь введите ваш ответ для пользователя.")
        await Support.waiting_for_send.set()
    except ValueError:
        await message.answer("Пожалуйста, введите корректный ID пользователя.")


@dp.message_handler(state=Support.waiting_for_send)
async def send_reply(message: types.Message, state: FSMContext):
    state_data = await state.get_data()
    user_id = state_data.get("user_id")
    admin_id = state_data.get("admin_id")
    user = await bot.get_chat(user_id)
    username = user.username
    name = user.first_name
    expected_admin_id = state_data.get("admin_id")
    inline_markup = types.InlineKeyboardMarkup()
    inline_markup.add(types.InlineKeyboardButton(
        "Ответить", callback_data=f"otvet:{admin_id}"
    ))

    if not user_id:
        await message.answer("Ошибка: не найден ID пользователя для ответа.")
        await state.finish()
        return

    if message.from_user.id == expected_admin_id:
        try:
            await bot.send_message(chat_id=user_id, text=f'❗️Администратор отправил вам сообщение: {message.text}',
                                   reply_markup=inline_markup)
            await message.answer(f"Ответ успешно отправлен пользователю {name} @{username}")
            await state.finish()
        except Exception as e:
            await message.answer(f"Ошибка при отправке ответа пользователю: {e}")
            await state.finish()
    else:
        return


@dp.callback_query_handler(lambda c: c.data.startswith("otvet"))
async def handle_reply_button(callback_query: types.CallbackQuery, state: FSMContext):
    admin_id = callback_query.data.split(":")[1]
    user_id = callback_query.from_user.id
    await state.update_data(user_id=user_id, admin_id=admin_id)
    await callback_query.message.answer("Введите ваш ответ администратору:")
    await Support.waiting_for_otvet.set()


@dp.message_handler(state=Support.waiting_for_otvet)
async def send_reply(message: types.Message, state: FSMContext):
    state_data = await state.get_data()
    user_id = state_data.get("user_id")
    user = await bot.get_chat(user_id)
    username = user.username
    name = user.first_name
    expected_admin_id = state_data.get("admin_id")
    mess_id = state_data.get("mess_id")
    user_name = message.from_user.first_name or "Пользователь"
    username = f"@{message.from_user.username}" if message.from_user.username else "нет имени пользователя"
    now = datetime.now()
    current_date = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M")
    if not user_id:
        await message.answer("Ошибка: не найден ID пользователя для ответа.")
        await state.finish()
        return

    try:
        await bot.send_message(chat_id=expected_admin_id,
                               text=f"📝<b>Ответ пользователя</b>\n\n"
                                    f"<b>Дата:</b> {current_date}\n"
                                    f"<b>Время</b> {current_time}\n"
                                    f"👤<b>Имя:</b> {user_name}\n"
                                    f"🔗<b>Username:</b> {username}\n"
                                    f"🆔<b>ID:</b> {user_id}\n"
                                    f"💬<b>Сообщение:</b>\n{message.text}")
        await message.answer(f"Ответ успешно отправлен администратору")
        await state.finish()
    except Exception as e:
        await message.answer(f"Ошибка при отправке ответа пользователю: {e}")
        await state.finish()
        return


@dp.callback_query_handler(lambda c: c.data == 'help')
async def handle_reply_button(callback_query: types.CallbackQuery):
    await callback_query.message.answer("Введите описание вашей проблемы одним сообщением:")
    orm.add_typing(callback_query.from_user.id)
    await Support.waiting_for_message.set()


@dp.message_handler(state=Support.waiting_for_message)
async def receive_problem(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_name = message.from_user.first_name or "Пользователь"
    username = f"@{message.from_user.username}" if message.from_user.username else "нет имени пользователя"

    # Клавиатура с кнопкой "Ответить", содержащей ID пользователя
    inline_markup = types.InlineKeyboardMarkup()
    inline_markup.add(types.InlineKeyboardButton(
        "Ответить", callback_data=f"reply:{user_id},{message.message_id}"
    ))
    inline_markup.add(types.InlineKeyboardButton(
        text='Завершить✅',
        callback_data=f"end:{message.message_id}"
    ))
    orm.add_problem(user_id, username, message.text, message.message_id)
    users = orm.get_admins()
    num = orm.get_problem_order_number(message.message_id)
    now = datetime.now()
    current_date = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M")
    for user in users:
        try:
            await bot.send_message(
                chat_id=user.tg_id,
                text=f"🔔<b>{num}. Новая проблема</b>\n\n"
                     f"<b>Дата:</b> {current_date}\n"
                     f"<b>Время:</b> {current_time}\n"
                     f"👤<b>Имя:</b> {user_name}\n"
                     f"🔗<b>Username:</b> {username}\n"
                     f"🆔<b>ID:</b> {user_id}\n"
                     f"🆔<b>ID сообщения:</b> {message.message_id}\n"
                     f"💬<b>Сообщение:</b>\n{message.text}",
                reply_markup=inline_markup
            )
        except ChatNotFound:
            print(f"Чат с пользователем {user.tg_id} не найден.")
        except Exception as e:
            print(f"Ошибка отправки сообщения администратору {user.tg_id}: {e}")

    # Отправка сообщения в общий чат
    try:
        await bot.send_message(
            chat_id=GROUP_CHAT_ID,
            text=f"🔔<b>{num}. Новая проблема в поддержке</b>\n\n"
                 f"<b>Дата:</b> {current_date}\n"
                 f"<b>Время:</b> {current_time}\n"
                 f"👤<b>Пользователь:</b> {user_name} ({username})\n"
                 f"🆔<b>ID пользователя:</b> {user_id}\n"
                 f"🆔<b>ID сообщения:</b> {message.message_id}\n"
                 f"💬<b>Сообщение:</b>\n{message.text}",
            reply_markup=inline_markup
        )
    except Exception as e:
        print(f"Ошибка отправки сообщения в общий чат: {e}")

    # Сохранение проблемы в базе данных
    print(message.message_id)
    inline_markup = await menu.main_menu()
    # Ответ пользователю
    await message.answer(
        "✅ Ваше сообщение отправлено. Ожидайте ответа администратора!",
        reply_markup=inline_markup
    )
    await state.finish()


@dp.callback_query_handler(lambda c: c.data == 'otziv')
async def handle_reply_button(callback_query: types.CallbackQuery):
    await callback_query.message.answer("Введите ваш отзыв одним сообщением:")
    await Support.waiting_for_otziv.set()


@dp.message_handler(state=Support.waiting_for_otziv)
async def receive_problem(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_name = message.from_user.first_name or "Пользователь"
    username = f"@{message.from_user.username}" if message.from_user.username else "нет имени пользователя"

    # Клавиатура с кнопкой "Ответить", содержащей ID пользователя
    inline_markup = types.InlineKeyboardMarkup()
    inline_markup.add(types.InlineKeyboardButton(
        "Ответить", callback_data=f"ott:{user_id},{message.message_id}"
    ))
    inline_markup.add(types.InlineKeyboardButton(
        text='Завершить✅',
        callback_data=f"req:{message.message_id}"
    ))
    now = datetime.now()
    current_date = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M:%S")
    orm.add_otziv(user_id, username, message.text, message.message_id)
    users = orm.get_admins()
    num = orm.get_otziv_order_number(message.message_id)
    for user in users:
        try:
            await bot.send_message(
                chat_id=user.tg_id,
                text=f"🔔<b>{num}. Новый отзыв</b>\n\n"
                     f"<b>Дата:</b> {current_date}\n"
                     f"<b>Время:</b> {current_time}\n"
                     f"👤<b>Имя:</b> {user_name}\n"
                     f"🔗<b>Username:</b> {username}\n"
                     f"🆔<b>ID:</b> {user_id}\n"
                     f"🆔<b>ID сообщения:</b> {message.message_id}\n"
                     f"💬<b>Сообщение:</b>\n{message.text}",
                reply_markup=inline_markup
            )
        except ChatNotFound:
            print(f"Чат с пользователем {user.tg_id} не найден.")
        except Exception as e:
            print(f"Ошибка отправки сообщения администратору {user.tg_id}: {e}")

    # Отправка сообщения в общий чат
    try:
        await bot.send_message(
            chat_id=GROUP2,
            text=f"🔔<b>{num}. Новый отзыв в поддержке</b>\n\n"
                 f"<b>Дата:</b> {current_date}\n"
                 f"<b>Время:</b> {current_time}\n"
                 f"👤<b>Пользователь</b> {user_name} ({username})\n"
                 f"🆔<b>ID пользователя:</b> {user_id}\n"
                 f"🆔<b>ID сообщения:</b> {message.message_id}\n"
                 f"💬<b>Сообщение:</b>\n{message.text}",
            reply_markup=inline_markup
        )
    except Exception as e:
        print(f"Ошибка отправки сообщения в общий чат: {e}")

    # Сохранение проблемы в базе данных
    print(message.message_id)
    inline_markup = await menu.main_menu()
    # Ответ пользователю
    await message.answer(
        "✅ Ваше сообщение отправлено. Спасибо за отзыв!",
        reply_markup=inline_markup
    )
    await state.finish()


# Обработка кнопки "Ответить" с привязкой к пользователю
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


@dp.callback_query_handler(lambda c: c.data.startswith("reply"))
async def handle_reply_button(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.data.split(":")[1]
    mess_id = callback_query.data.split(",")[1]
    admin_id = callback_query.from_user.id
    await state.update_data(user_id=user_id, admin_id=admin_id, mess_id=mess_id)

    # Создаем клавиатуру с кнопкой "Отменить"
    cancel_keyboard = InlineKeyboardMarkup().add(
        InlineKeyboardButton("Отменить", callback_data="cancel_reply")
    )

    # Отправляем сообщение и сохраняем его ID в состоянии
    sent_message = await callback_query.message.answer(
        "Введите ваш ответ пользователю:",
        reply_markup=cancel_keyboard
    )
    await state.update_data(cancel_message_id=sent_message.message_id)
    await Support.waiting_for_reply.set()


@dp.callback_query_handler(lambda c: c.data == "cancel_reply", state=[Support.waiting_for_reply, Support.waiting_for_reply2])
async def cancel_reply(callback_query: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await callback_query.message.edit_text("Ответ отменён.")  # Убираем инлайн-кнопку


@dp.callback_query_handler(lambda c: c.data.startswith("ott"))
async def handle_reply_button(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.data.split(":")[1]
    mess_id = callback_query.data.split(",")[1]
    admin_id = callback_query.from_user.id
    await state.update_data(user_id=user_id, admin_id=admin_id, mess_id=mess_id)

    # Создаем клавиатуру с кнопкой "Отменить"
    cancel_keyboard = InlineKeyboardMarkup().add(
        InlineKeyboardButton("Отменить", callback_data="cancel_reply")
    )

    # Отправляем сообщение и сохраняем его ID в состоянии
    sent_message = await callback_query.message.answer(
        "Введите ваш ответ пользователю:",
        reply_markup=cancel_keyboard
    )
    await state.update_data(cancel_message_id=sent_message.message_id)
    await Support.waiting_for_reply2.set()


@dp.callback_query_handler(lambda c: c.data.startswith("req"))
async def handle_end_button(callback_query: types.CallbackQuery, state: FSMContext):
    mess_id = callback_query.data.split(":")[1]  # Извлекаем ID пользователя из callback data
    orm.delete_otziv(mess_id)
    text, idus, usname, num, date = orm.get_otziv(mess_id)
    now = datetime.now()
    current_date = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M")
    await bot.edit_message_text(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        text=f"✅<b>{num}. Ответ на отзыв получен</b>\n\n"
             f"<b>Поступил:</b> {date}\n"
             f"👤<b>Пользователь:</b> {usname}\n"
             f"🆔<b>ID пользователя:</b> {idus}\n"
             f"🆔<b>ID сообщения:</b> {mess_id}\n"
             f"💬<b>Сообщение:</b>\n{text}\n\n"
             f"<b>Завершено:</b>\n"
             f"<b>Дата:</b> {current_date}\n"
             f"<b>Время:</b> {current_time}\n"
    )

    # Отправляем уведомление об успешном завершении
    # await callback_query.message.answer("Завершено. Ответ отправлен, сообщение в чате изменено.")


@dp.callback_query_handler(lambda c: c.data.startswith("end"))
async def handle_end_button(callback_query: types.CallbackQuery, state: FSMContext):
    mess_id = callback_query.data.split(":")[1]  # Извлекаем ID пользователя из callback data
    orm.delete_problem(mess_id)
    text, idus, usname, num, date = orm.get_problem(mess_id)
    now = datetime.now()
    current_date = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M:%S")
    await bot.edit_message_text(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        text=f"✅<b>{num}. Проблема решена</b>\n\n"
             f"<b>Поступила:</b> {date}\n"
             f"👤<b>Пользователь:</b> {usname}\n"
             f"🆔<b>ID пользователя:</b> {idus}\n"
             f"🆔<b>ID сообщения:</b> {mess_id}\n"
             f"💬<b>Сообщение:</b>\n{text}\n\n"
             f"<b>Завершено:</b>\n"
             f"<b>Дата:</b> {current_date}\n"
             f"<b>Время:</b> {current_time}\n"
    )

    # Отправляем уведомление об успешном завершении
    # await callback_query.message.answer("Завершено. Ответ отправлен, сообщение в чате изменено.")


# Отправка ответа пользователю
@dp.message_handler(state=Support.waiting_for_reply)
async def send_reply(message: types.Message, state: FSMContext):
    state_data = await state.get_data()
    user_id = state_data.get("user_id")
    cancel_message_id = state_data.get("cancel_message_id")  # Получаем ID сообщения с кнопкой "Отменить"
    user = await bot.get_chat(user_id)
    username = user.username
    name = user.first_name
    expected_admin_id = state_data.get("admin_id")
    mess_id = state_data.get("mess_id")
    orm.add_otvet(mess_id, message.text)

    if not user_id:
        await message.answer("Ошибка: не найден ID пользователя для ответа.")
        await state.finish()
        return

    if message.from_user.id == expected_admin_id:
        try:
            # Отправляем ответ пользователю
            await bot.send_message(chat_id=user_id, text=f'⚒️ {message.text}')
            await message.answer(f"Ответ успешно отправлен пользователю {name} @{username}")

            # Удаляем сообщение с кнопкой "Отменить"
            if cancel_message_id:
                try:
                    await bot.delete_message(chat_id=message.chat.id, message_id=cancel_message_id)
                except Exception as e:
                    await message.answer(f"Не удалось удалить сообщение с кнопкой: {e}")

            await state.finish()
        except Exception as e:
            await message.answer(f"Ошибка при отправке ответа пользователю: {e}")
            await state.finish()
            return
    else:
        return



@dp.message_handler(state=Support.waiting_for_reply2)
async def send_reply2(message: types.Message, state: FSMContext):
    state_data = await state.get_data()
    user_id = state_data.get("user_id")
    cancel_message_id = state_data.get("cancel_message_id")  # Получаем ID сообщения с кнопкой "Отменить"
    expected_admin_id = state_data.get("admin_id")
    mess_id = state_data.get("mess_id")

    # Проверяем данные пользователя
    if not user_id:
        await message.answer("Ошибка: не найден ID пользователя для ответа.")
        await state.finish()
        return

    if message.from_user.id == expected_admin_id:
        try:
            # Отправляем сообщение пользователю
            user = await bot.get_chat(user_id)
            username = user.username
            name = user.first_name

            await bot.send_message(chat_id=user_id, text=f"✉️ {message.text}")
            await message.answer(f"Ответ успешно отправлен пользователю {name} @{username}")

            # Сохраняем решение в базу данных
            orm.add_reshenie(mess_id, message.text)

            # Удаляем сообщение с кнопкой "Отменить", если оно существует
            if cancel_message_id:
                try:
                    await bot.delete_message(chat_id=message.chat.id, message_id=cancel_message_id)
                except Exception as e:
                    await message.answer(f"Ошибка при удалении сообщения с кнопкой: {e}")

            # Завершаем состояние
            await state.finish()

        except Exception as e:
            await message.answer(f"Ошибка при отправке ответа пользователю: {e}")
            await state.finish()
            return
    else:
        await message.answer("Вы не являетесь авторизованным администратором для отправки этого ответа.")
        return


@dp.callback_query_handler(lambda c: c.data == 'create_mailing')
async def create_mailing(callback_query: types.CallbackQuery):
    text = 'Введите текст, который хотите разослать'
    await callback_query.message.answer(text)
    await Mailing.text.set()


@dp.message_handler(state=Mailing.text)
async def mailing(message: types.Message, state: FSMContext):
    await state.update_data(text=message.text, entity=message.entities)
    state_data = await state.get_data()
    text = state_data.get('text')
    entity = state_data.get('entity')
    users = orm.get_all_users()
    await message.answer('Начинаю рассылку', parse_mode='Markdown')
    count = 0
    count_of_banned = 0
    for user in users:
        try:
            await bot.send_message(user.tg_id, text=text, entities=entity, disable_web_page_preview=True)
            count += 1
            if count == 15:
                await asyncio.sleep(5)
                count = 0
        except:
            count_of_banned += 1
    answer = f'Отправка рыссылки завершена\nВсего пользователей: {len(users)}\nОтправлено успешно: {len(users) - count_of_banned}\nУдалили чат с ботом: {count_of_banned}'
    orm.add_blocked(count_of_banned)
    await message.answer(answer, parse_mode='Markdown')
    await state.finish()


@dp.callback_query_handler(lambda c: c.data == 'information')
async def inform(message: types.Message):
    text = f'''🌟 <b>Описание бота техподдержки</b> 🌟  

    Наш бот техподдержки  предназначен для пользователей ИИ-бота <b>"Терапия"</b>, которые:
    🛠 столкнулись с техническими проблемами и неполадками
    📣 хотят рассказать, поделиться своим мнением о нашем боте

    <b>Мы просим вас открыто говорить нам своё мнение о боте и возможных проблемах, которые возникли в период работы с ним.</b>

    ➡️ <b>Для того, чтобы дать свою обратную связь, отправьте сообщение в этот бот с описанием проблемы:</b>
    1️⃣ Вы отправляете сообщение 📝  
    2️⃣ Специалист поддержки получает ваш запрос и принимает его в работу 🫡  
    3️⃣ После обработки вы получите от специалиста обратную связь 📬

    ❤️ <b>Этот бот создан для того, чтобы вы помогли нам, а мы были полезны вам.</b>'''

    inline_markup = await menu.main_menu()
    await bot.send_message(message.from_user.id, text, reply_markup=inline_markup, parse_mode='HTML')


@dp.callback_query_handler(lambda c: c.data == 'spisok')
async def spisok(callback_query: types.CallbackQuery):
    zadaniya = orm.spisok_problem()

    for zadanie in zadaniya:
        username = f"@{zadanie.username}" if zadanie.username else "нет имени пользователя"
        inline_markup = types.InlineKeyboardMarkup()
        print(zadanie.message_id)
        inline_markup.add(types.InlineKeyboardButton(
            "Ответить", callback_data=f"reply:{zadanie.tg_id},{zadanie.message_id}"
        ))
        inline_markup.add(types.InlineKeyboardButton(
            text='Завершить✅',
            callback_data=f"end:{zadanie.message_id}"
        ))
        text = f"У пользователя с ID: {zadanie.tg_id} {username} была проблема: {zadanie.problem_text}"
        await callback_query.message.answer(text, reply_markup=inline_markup)


@dp.callback_query_handler(lambda c: c.data == 'spisok_otziv')
async def spisok(callback_query: types.CallbackQuery):
    zadaniya = orm.spisok_otziv()

    for zadanie in zadaniya:
        username = f"@{zadanie.username}" if zadanie.username else "нет имени пользователя"
        inline_markup = types.InlineKeyboardMarkup()
        inline_markup.add(types.InlineKeyboardButton(
            "Ответить", callback_data=f"ott:{zadanie.tg_id},{zadanie.message_id}"
        ))
        inline_markup.add(types.InlineKeyboardButton(
            text='Завершить✅',
            callback_data=f"req:{zadanie.message_id}"
        ))
        text = f"У пользователя с ID: {zadanie.tg_id} {username} был отзыв: {zadanie.otziv_text}"
        await callback_query.message.answer(text, reply_markup=inline_markup)


@dp.callback_query_handler(lambda c: c.data == 'vse_problems')
async def problems(callback_query: types.CallbackQuery):
    txt_file_path, excel_file_path = orm.vse_problems()
    text = 'Вот все ваши файлы: '
    await callback_query.message.answer(text)
    # Отправляем текстовый файл
    await bot.send_document(
        callback_query.message.chat.id,
        InputFile(txt_file_path),
        caption="Список проблем в текстовом формате."
    )

    # Отправляем Excel файл
    await bot.send_document(
        callback_query.message.chat.id,
        InputFile(excel_file_path),
        caption="Список проблем в Excel формате."
    )

    # Удаляем файлы после отправки (по желанию)
    os.remove(txt_file_path)
    os.remove(excel_file_path)


@dp.callback_query_handler(lambda c: c.data == 'vse_otzivi')
async def problems(callback_query: types.CallbackQuery):
    txt_file_path, excel_file_path = orm.vse_otziv()
    text = 'Вот все ваши файлы: '
    await callback_query.message.answer(text)
    # Отправляем текстовый файл
    await bot.send_document(
        callback_query.message.chat.id,
        InputFile(txt_file_path),
        caption="Список отзывов в текстовом формате."
    )

    # Отправляем Excel файл
    await bot.send_document(
        callback_query.message.chat.id,
        InputFile(excel_file_path),
        caption="Список отзывов в Excel формате."
    )

    # Удаляем файлы после отправки (по желанию)
    os.remove(txt_file_path)
    os.remove(excel_file_path)


@dp.callback_query_handler(lambda c: c.data == 'stat')
async def get_stat(callback_query: types.CallbackQuery):
    stat = orm.stat()
    text = f'Всего пользователей: {stat[0]}\nУдалили чат с ботом: {stat[1]}\n*Количество удаливших чат с ботом обновляется после рассылки*'
    await callback_query.message.answer(text)


@dp.callback_query_handler(lambda c: c.data == 'menu')
async def exit(message: types.Message):
    text = 'Главное меню:'
    inline_markup = await menu.main_menu()
    await bot.send_message(message.from_user.id, text, reply_markup=inline_markup)


@dp.message_handler(content_types=types.ContentType.TEXT)
async def handle_messages(message: types.Message):
    inline_markup = await menu.main_menu()
    await message.answer(
        "Выберите действие для связи с техподдержкой: ",
        reply_markup=inline_markup
    )


@app.get("/bot_status")
async def bot_status():
    return {"status": "running", "bot_name": "TherapyBot"}


# Функция запуска FastAPI
def start_fastapi():
    run(app, host="0.0.0.0", port=8000)


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
