import logging

import redis
import requests
from environs import Env
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Filters, Updater, CallbackContext
from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler

from api_funcs import get_products, get_product_detail, get_product_img
from api_funcs import get_or_create_cart, create_ordered_product, get_cart_ordered_products
from api_funcs import remove_ordered_product
from api_funcs import get_or_create_customer, save_customer_email

logger = logging.getLogger(__name__)


def main():
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    env = Env()
    env.read_env()
    tg_bot_token = env.str('TG_BOT_TOKEN')
    starapi_token = env.str('STARAPI_TOKEN')

    redis_db = redis.Redis(host=env.str('REDIS_DB_HOST'),
                           port=env.int('REDIS_DB_PORT'),
                           password=env.str('REDIS_DB_PASSWORD'),
                           decode_responses=True)

    updater = Updater(tg_bot_token)
    dispatcher = updater.dispatcher

    dispatcher.bot_data['redis_db'] = redis_db
    dispatcher.bot_data['starapi_token'] = starapi_token

    dispatcher.add_handler(CallbackQueryHandler(handle_users_reply))
    dispatcher.add_handler(MessageHandler(Filters.text, handle_users_reply))
    dispatcher.add_handler(CommandHandler('start', handle_users_reply))

    updater.start_polling()
    updater.idle()


def start(update: Update, context: CallbackContext):
    """Хэндлер для состояния START."""
    products = get_products(context.bot_data['starapi_token'])
    keyboard = [
        [InlineKeyboardButton(product['attributes']['Title'], callback_data=product['id'])] for product in products
    ]
    keyboard += [[InlineKeyboardButton('Моя корзина', callback_data='cart')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        update.message.reply_text(text='Привет! Выбери товар.', reply_markup=reply_markup)
    else:
        update.callback_query.message.reply_text(text='Выбрать товар или посмотреть корзину.', reply_markup=reply_markup)
        update.callback_query.delete_message()
    return 'HANDLE_MENU'


def cart(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    api_token = context.bot_data['starapi_token']
    user_cart = get_or_create_cart(query.message.chat_id, api_token)
    ordered_products = get_cart_ordered_products(user_cart, api_token, as_text=False)
    cart_text = get_cart_ordered_products(user_cart, api_token, as_text=True)

    keyboard = [[InlineKeyboardButton(f'Отказаться от {product["title"]} {product["amount"]}',
                                     callback_data=f'remove_item;{product["id"]}')] for product in ordered_products]
    keyboard += [
        [InlineKeyboardButton('В меню', callback_data='cancel')],
        [InlineKeyboardButton('Оплатить', callback_data='payment')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.callback_query.message.reply_text(cart_text, reply_markup=reply_markup)
    update.callback_query.delete_message()
    return 'HANDLE_CART'


def select_cart_item(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    if query.data == 'cancel':
        query.answer()
        return start(update, context)
    if query.data.startswith('remove_item'):
        ordered_product_id = query.data.split(';')[1]
        remove_ordered_product(ordered_product_id, context.bot_data['starapi_token'])
        return cart(update, context)
    if query.data == 'payment':
        return request_an_email(update, context)


def request_an_email(update: Update, context: CallbackContext):
    update.callback_query.message.reply_text(text='Для оплаты введите Ваш адрес электронной почты.')
    update.callback_query.delete_message()
    return 'WAITING_EMAIL'


def process_email(update: Update, context: CallbackContext):
    api_token = context.bot_data['starapi_token']
    users_email = update.message.text
    customer_id = get_or_create_customer(update.message.chat_id, api_token)['id']
    try:
        customer = save_customer_email(customer_id, users_email, api_token)
        update.message.reply_text('Заказ принят! Ожидайте обращения нашего менеджера на Ваш e-mail!')
        return start(update, context)
    except requests.exceptions.HTTPError:
        update.message.reply_text('E-mail введён некорректно! Повторите ввод.')
        return 'WAITING_EMAIL'


def select_menu_item(update: Update, context: CallbackContext):
    query = update.callback_query
    if query.data == 'cart':
        return cart(update, context)
    query.answer()

    product_detail = get_product_detail(query.data, context.bot_data['starapi_token'])
    image = get_product_img(product_detail['Image']['data']['attributes']['url'])

    keyboard = [
        [InlineKeyboardButton('Добавить в корзину', callback_data=f'add_to_cart;{query.data}')],
        [InlineKeyboardButton('Моя корзина', callback_data='cart')],
        [InlineKeyboardButton('Назад', callback_data='cancel')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.callback_query.message.reply_photo(image, caption=product_detail['Description'], reply_markup=reply_markup)
    query.delete_message()
    return 'HANDLE_DESCRIPTION'


def detail_result(update: Update, context: CallbackContext):
    query = update.callback_query
    if query.data == 'cancel':
        query.answer()
        return start(update, context)
    elif query.data == 'cart':
        query.answer()
        return cart(update, context)
    elif query.data.startswith('add_to_cart'):
        query.answer()
        product_id = int(query.data.split(';')[1])
        api_token = context.bot_data['starapi_token']
        user_cart = get_or_create_cart(query.message.chat_id, api_token)
        ordered_product = create_ordered_product(product_id, api_token, cart_id=user_cart['id'])
        return start(update, context)


def handle_users_reply(update: Update, context: CallbackContext):
    """
    Функция, которая запускается при любом сообщении от пользователя и решает как его обработать.
    Эта функция запускается в ответ на эти действия пользователя:
        * Нажатие на inline-кнопку в боте
        * Отправка сообщения боту
        * Отправка команды боту
    Она получает стейт пользователя из базы данных и запускает соответствующую функцию-обработчик (хэндлер).
    Функция-обработчик возвращает следующее состояние, которое записывается в базу данных.
    Если пользователь только начал пользоваться ботом, Telegram форсит его написать "/start",
    поэтому по этой фразе выставляется стартовое состояние.
    Если пользователь захочет начать общение с ботом заново, он также может воспользоваться этой командой.
    """
    redis_db = context.bot_data['redis_db']
    if update.message:
        user_reply = update.message.text
        chat_id = update.message.chat_id
    elif update.callback_query:
        user_reply = update.callback_query.data
        chat_id = update.callback_query.message.chat_id
    else:
        return
    if user_reply == '/start':
        user_state = 'START'
    else:
        user_state = redis_db.get(chat_id)

    states_functions = {
        'START': start,
        'HANDLE_MENU': select_menu_item,
        'HANDLE_DESCRIPTION': detail_result,
        'HANDLE_CART': select_cart_item,
        'WAITING_EMAIL': process_email
    }
    state_handler = states_functions[user_state]

    try:
        next_state = state_handler(update, context)
        redis_db.set(chat_id, next_state)
    except Exception as err:
        print(err)
        raise err


if __name__ == '__main__':
    main()
