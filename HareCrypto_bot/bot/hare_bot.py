# IDEA: сделать бота инлайн, но нужно знать, какие данные выводить инлайн
# IDEA: добавить в настройку изменение количества дней, после истечения которых удаляются события
# IDEA: добавить в настройку изменение количества минут для уведомления о надвигающемся событии

import asyncio
import logging
import sqlite3
import aioschedule  # библиотека для выставления заданий по расписанию

# подключаем библиотеку для работы с API телеграм бота
import pendulum
from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import ReplyKeyboardRemove, \
    InlineKeyboardMarkup, InlineKeyboardButton

# подключение функций из сторонних файлов
from admin_panel import admin_panel, in_admin_panel, admin_inline, first_launch
from config import admin_id
from defs import get_admin_list, log, user_logger, get_moder_list, chat_logger, hot_notification, page_output
from extensions import Settings, Event_List, Message_Mem, check_repeated_message, Page_Mem
import files
from mod_panel import moder_panel, in_moder_panel, moder_inline

# формат даты
date_formatter = "%d.%m.%Y %H:%M"

# объекты классов для работы с сообщениями по командам start, help, event
last_message_start = Message_Mem()
last_message_help = Message_Mem()
last_message_event = Message_Mem()
# объект класса для работы с постраничным выводом
last_page = Page_Mem()

# set logging level
logging.basicConfig(level=logging.INFO)

# настройка и инициализация бота
settings = Settings()
with Settings() as tg_token:
    bot = Bot(token=tg_token)
dp = Dispatcher(bot)


# обработчик команды start
@dp.message_handler(commands=['start'])
async def process_start_command(message: types.Message):
    if message.chat.type == 'private':
        user_logger(message.chat.id)
        await bot.send_message(message.chat.id, f"Привет, {message.chat.username}!\n",
                               reply_markup=ReplyKeyboardRemove())
        add_bot_ingroup = InlineKeyboardMarkup()
        add_bot_ingroup.add(InlineKeyboardButton('Добавить бота в группу',
                                                 url='http://t.me/HareCrypta_bot?startgroup=botstart'))
        await bot.send_message(message.chat.id, "Я HareCrypta-бот!\nМожешь использовать меня для слежения "
                                                "за событиями в криптосообществах!\n"
                                                "По команде /help можно получить "
                                                "дополнительную информацию", reply_markup=add_bot_ingroup)
        await log(f'User {message.chat.id} started bot')
    else:
        await check_repeated_message(bot, message, last_message_start)

        user_logger(message.from_user.id)
        try:
            chat_logger(message.chat.id, message.chat.title, message.chat.username)
        except:
            chat_logger(message.chat.id, message.chat.title)
        await bot.send_message(message.chat.id, "Привет всем!\n"
                                                "Я HareCrypta-бот!\nМожете использовать меня для слежения "
                                                "за событиями в криптосообществах!\n"
                                                "По команде /help можно получить "
                                                "дополнительную информацию",
                               reply_markup=ReplyKeyboardRemove())
        await log(f'Member {message.from_user.id} from the group {message.chat.id} started bot')


# обработчик команды help
@dp.message_handler(commands=['help'])
async def process_help_command(message: types.Message):
    await check_repeated_message(bot, message, last_message_help)

    if message.chat.type == 'private':
        user_logger(message.chat.id)
        await bot.send_message(message.chat.id, settings.help_text)
    else:
        user_logger(message.from_user.id)
        try:
            chat_logger(message.chat.id, message.chat.title, message.chat.username)
        except:
            chat_logger(message.chat.id, message.chat.title)

        await bot.send_message(message.chat.id, settings.help_text)


# обработчик команды event
# вывод списка событий постранично
@dp.message_handler(commands=["event"])
async def event_handler(message: types.Message):
    await check_repeated_message(bot, message, last_message_event)

    events, entity_list, inline_paginator = await page_output(message, last_page, 1, settings.time_zone)

    await bot.send_message(message.chat.id, events, entities=entity_list, reply_markup=inline_paginator)

    if message.chat.type == 'private':
        user_logger(message.chat.id)
        await log(f'User {message.chat.id} requested events list')
    else:
        try:
            chat_logger(message.chat.id, message.chat.title, message.chat.username)
        except:
            chat_logger(message.chat.id, message.chat.title)

        await log(f'Member {message.from_user.id} from the group {message.chat.id} requested events list')


# обработчик команды adm
# вход в панель администратора
@dp.message_handler(commands=["adm"])
async def admin_handler(message: types.Message):
    if message.chat.type == 'private':
        user_logger(message.chat.id)
        if message.chat.id == admin_id and await first_launch(bot, settings, message.chat.id) is True:
            await bot.send_message(message.chat.id, "Теперь вы Админ!")
            await log(f'User {message.chat.id} successfully requested admin panel')
        elif (message.chat.id == admin_id or message.chat.id in get_admin_list()) and \
                await first_launch(bot, settings, message.chat.id) is False:
            await bot.send_message(message.chat.id, "Привет, Админ!")
            await log(f'User {message.chat.id} successfully requested admin panel')
            await admin_panel(bot, message.chat.id, settings)
        else:
            await bot.send_message(message.chat.id, "Вы не Админ!")
            await log(f'User {message.chat.id} unsuccessfully requested admin panel')
    else:
        user_logger(message.from_user.id)
        try:
            chat_logger(message.chat.id, message.chat.title, message.chat.username)
        except:
            chat_logger(message.chat.id, message.chat.title)
        await bot.send_message(message.chat.id, "🤨")
        await log(f'Member {message.from_user.id} from the group {message.chat.id} requested admin panel')


# обработчик команды mod
# вход в панель модератора
# (по сравнению с админом, функционал подрезан до создания, удаления и редактирования событий)
@dp.message_handler(commands=["mod"])
async def moder_handler(message: types.Message):
    if message.chat.type == 'private':
        user_logger(message.chat.id)
        if message.chat.id in get_moder_list():
            await bot.send_message(message.chat.id, "Привет, Модератор!")
            await log(f'User {message.chat.id} successfully requested moderator panel')
            await moder_panel(bot, message.chat.id, settings)
        else:
            await bot.send_message(message.chat.id, "Вы не Модератор!")
            await log(f'User {message.chat.id} unsuccessfully requested moderator panel')
    else:
        user_logger(message.from_user.id)
        try:
            chat_logger(message.chat.id, message.chat.title, message.chat.username)
        except:
            chat_logger(message.chat.id, message.chat.title)
        await bot.send_message(message.chat.id, "🤨")
        await log(f'Member {message.from_user.id} from the group {message.chat.id} requested admin panel')


# обработчик входных данных из сообщений
# обработка команд для админ панели
# обработка команд для мод панели
@dp.message_handler(content_types=["text"])
async def actions_handler(message: types.Message):
    if message.chat.type == 'private':
        if message.chat.id == admin_id or message.chat.id in get_admin_list():
            await in_admin_panel(bot, message.chat.id, settings, message)
        elif message.chat.id in get_moder_list():
            await in_moder_panel(bot, message.chat.id, settings, message)
    else:
        pass


# обработчик инлайн событий (функция пустышка!!!)
@dp.inline_handler(lambda query: len(query.query) > 0)
async def query_text(query):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(text="Нажми меня", callback_data="test"))
    results = []
    single_msg = types.InlineQueryResultArticle(
        id="1", title="Press me",
        input_message_content=types.InputTextMessageContent(message_text="Я – сообщение из инлайн-режима"),
        reply_markup=kb
    )
    results.append(single_msg)
    await bot.answer_inline_query(query.id, results)


# обработчик коллбэков от инлайн кнопок
@dp.callback_query_handler(lambda c: True)
async def callback(callback_query: types.CallbackQuery):
    """
    Для приватных сообщений обрабатывается коллбэк для админов и модераторов
    и также для перелистывания страниц (forward, backward).
    Для сообщений в группе идёт обработка команд только для перелистывания страниц (forward, backward).
    """
    if callback_query.message:
        if callback_query.message.chat.type == 'private':
            if callback_query.message.chat.id in get_admin_list():
                await admin_inline(bot, callback_query.data, callback_query.message.chat.id,
                                   callback_query.message.message_id)
            elif callback_query.message.chat.id in get_moder_list():
                await moder_inline(bot, callback_query.data, callback_query.message.chat.id,
                                   callback_query.message.message_id)

            if callback_query.data == "forward":
                page_num = last_page.last_page[callback_query.message.message_id - 1] + 1

                if callback_query.message.message_id - 1 in last_page.last_page.keys() and page_num != 7:
                    last_page.last_page[callback_query.message.message_id - 1] += 1
                    page_num = last_page.last_page[callback_query.message.message_id-1]

                    events, entity_list, inline_paginator = \
                        await page_output(callback_query.message, last_page, page_num, settings.time_zone)

                    await bot.edit_message_text(chat_id=callback_query.message.chat.id,
                                                message_id=callback_query.message.message_id,
                                                text=events, entities=entity_list, reply_markup=inline_paginator)
                elif callback_query.message.message_id-1 in last_page.last_page.keys() and page_num == 7:
                    last_page.last_page[callback_query.message.message_id - 1] = 1
                    page_num = last_page.last_page[callback_query.message.message_id - 1]

                    events, entity_list, inline_paginator = \
                        await page_output(callback_query.message, last_page, page_num, settings.time_zone)

                    await bot.edit_message_text(chat_id=callback_query.message.chat.id,
                                                message_id=callback_query.message.message_id,
                                                text=events, entities=entity_list, reply_markup=inline_paginator)

            if callback_query.data == "backward":
                page_num = last_page.last_page[callback_query.message.message_id-1] - 1

                if callback_query.message.message_id - 1 in last_page.last_page.keys() and page_num != 0:
                    last_page.last_page[callback_query.message.message_id - 1] -= 1
                    page_num = last_page.last_page[callback_query.message.message_id - 1]

                    events, entity_list, inline_paginator = \
                        await page_output(callback_query.message, last_page, page_num, settings.time_zone)

                    await bot.edit_message_text(chat_id=callback_query.message.chat.id,
                                                message_id=callback_query.message.message_id,
                                                text=events, entities=entity_list, reply_markup=inline_paginator)
                elif callback_query.message.message_id - 1 in last_page.last_page.keys() and page_num == 0:
                    last_page.last_page[callback_query.message.message_id - 1] = 6
                    page_num = last_page.last_page[callback_query.message.message_id - 1]

                    events, entity_list, inline_paginator = \
                        await page_output(callback_query.message, last_page, page_num, settings.time_zone)

                    await bot.edit_message_text(chat_id=callback_query.message.chat.id,
                                                message_id=callback_query.message.message_id,
                                                text=events, entities=entity_list, reply_markup=inline_paginator)

            await bot.answer_callback_query(callback_query.id)

        else:
            if callback_query.data == "forward":
                page_num = last_page.last_page[callback_query.message.message_id - 1] + 1

                if callback_query.message.message_id - 1 in last_page.last_page.keys() and page_num != 7:
                    last_page.last_page[callback_query.message.message_id - 1] += 1
                    page_num = last_page.last_page[callback_query.message.message_id - 1]

                    events, entity_list, inline_paginator = \
                        await page_output(callback_query.message, last_page, page_num, settings.time_zone)

                    await bot.edit_message_text(chat_id=callback_query.message.chat.id,
                                                message_id=callback_query.message.message_id,
                                                text=events, entities=entity_list, reply_markup=inline_paginator)
                elif callback_query.message.message_id - 1 in last_page.last_page.keys() and page_num == 7:
                    last_page.last_page[callback_query.message.message_id - 1] = 1
                    page_num = last_page.last_page[callback_query.message.message_id - 1]

                    events, entity_list, inline_paginator = \
                        await page_output(callback_query.message, last_page, page_num, settings.time_zone)

                    await bot.edit_message_text(chat_id=callback_query.message.chat.id,
                                                message_id=callback_query.message.message_id,
                                                text=events, entities=entity_list, reply_markup=inline_paginator)

            if callback_query.data == "backward":
                page_num = last_page.last_page[callback_query.message.message_id - 1] - 1

                if callback_query.message.message_id - 1 in last_page.last_page.keys() and page_num != 0:
                    last_page.last_page[callback_query.message.message_id - 1] -= 1
                    page_num = last_page.last_page[callback_query.message.message_id - 1]

                    events, entity_list, inline_paginator = \
                        await page_output(callback_query.message, last_page, page_num, settings.time_zone)

                    await bot.edit_message_text(chat_id=callback_query.message.chat.id,
                                                message_id=callback_query.message.message_id,
                                                text=events, entities=entity_list, reply_markup=inline_paginator)
                elif callback_query.message.message_id - 1 in last_page.last_page.keys() and page_num == 0:
                    last_page.last_page[callback_query.message.message_id - 1] = 6
                    page_num = last_page.last_page[callback_query.message.message_id - 1]

                    events, entity_list, inline_paginator = \
                        await page_output(callback_query.message, last_page, page_num, settings.time_zone)

                    await bot.edit_message_text(chat_id=callback_query.message.chat.id,
                                                message_id=callback_query.message.message_id,
                                                text=events, entities=entity_list, reply_markup=inline_paginator)

            await bot.answer_callback_query(callback_query.id)

    elif callback_query.inline_message_id:
        if callback_query.data == "test":
            await bot.edit_message_text(inline_message_id=callback_query.inline_message_id,
                                        text="INLINE MODE")


# проверка и удаление старых событий
async def check_old_events():
    con = sqlite3.connect(files.main_db)
    cursor = con.cursor()
    events_list = Event_List()

    try:
        cursor.execute("SELECT name, description, date, name_entities, description_entities, "
                       "type_event FROM events;")
    except:
        cursor.execute("CREATE TABLE events (id INT, name TEXT, "
                       "description TEXT, date DATETIME, name_entities JSON, description_entities JSON, "
                       "type_event TEXT);")
    else:
        now = pendulum.now(settings.time_zone)

        for name, description, date, name_entities, description_entities, type_event in cursor.fetchall():
            if date == 'TBA':
                events_list.events_unsorted.update({(name, description, date, name_entities,
                                                     description_entities, type_event): 'TBA'})
            else:
                date_formatted = pendulum.from_format(date, "DD.MM.YYYY HH:mm", tz=settings.time_zone)
                delta = date_formatted - now
                delta = divmod(delta.total_seconds(), 3600)
                events_list.events_unsorted.update({(name, description, date, name_entities,
                                                     description_entities, type_event): int(delta[0])})

        for events_key, events_value in events_list.events_unsorted.items():
            name = events_key[0]

            if events_value == 'TBA':
                continue
            if events_value < -72:  # число указано в часах (3 дня есть 72 часа)
                cursor.execute("DELETE FROM events WHERE name = " + "'" + str(name) + "';")
                con.commit()

        con.close()


# проверка приближающихся событий (каждую минуту проверяется, остается ли 59 минут до события)
async def check_hot_events():
    if settings.hot_event_setting:
        con = sqlite3.connect(files.main_db)
        cursor = con.cursor()

        try:
            cursor.execute("SELECT name, description, date, name_entities, description_entities, "
                           "type_event FROM events;")
        except:
            cursor.execute("CREATE TABLE events (id INT, name TEXT, "
                           "description TEXT, date DATETIME, name_entities JSON, description_entities JSON, "
                           "type_event TEXT);")
        else:
            now = pendulum.now(settings.time_zone)

            for name, description, date, name_entities, description_entities, type_event in cursor.fetchall():
                if date == 'TBA':
                    continue
                else:
                    date_formatted = pendulum.from_format(date, "DD.MM.YYYY HH:mm", tz=settings.time_zone)
                    delta = date_formatted - now
                    delta = divmod(delta.total_seconds(), 60)
                    event = (name, description, date, name_entities, description_entities, type_event)

                    if delta[0] == 59:  # число указано в минутах
                        await hot_notification(bot, event)

            con.close()


# расписание задач
async def scheduler():
    """
    Регистратор задач для:
        -очистки старых событий и удаление их
        -проверка наличия событий, которым остаётся меньше часа до начала
    """
    aioschedule.every().hour.do(check_old_events)
    aioschedule.every(1).minutes.do(check_hot_events)

    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(1)


# функция при запуске боте
async def on_startup(_):
    asyncio.create_task(scheduler())

    get_list = 0
    # for user in user_logger(get_list):
    #     try:
    #         await bot.send_message(int(user), "Я снова в строю!")
    #         await log(f"User {int(user)} got 'Startup' message")
    #     except:
    #         await log(f"User {int(user)} didn't get 'Startup' message")


# функция при запуске боте
async def on_shutdown(_):
    get_list = 0
    # for user in user_logger(get_list):
    #     try:
    #         await bot.send_message(int(user), "Ушел на обновление. Скоро буду!")
    #         await log(f"User {int(user)} got 'Shutdown' message")
    #     except:
    #         await log(f"User {int(user)} didn't get 'Shutdown' message")


# входная точка программы
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=False, on_startup=on_startup, on_shutdown=on_shutdown)
