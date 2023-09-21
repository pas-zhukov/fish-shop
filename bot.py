import logging

import redis
import requests
from environs import Env
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Filters, Updater, CallbackContext
from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler

from strapi_api import get_products, get_product_detail, get_product_img
from strapi_api import get_or_create_cart, create_ordered_product, get_cart_ordered_products
from strapi_api import remove_ordered_product
from strapi_api import get_or_create_customer, save_customer_email

logger = logging.getLogger(__name__)


def main():
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    env = Env()
    env.read_env()
    tg_bot_token = env.str('TG_BOT_TOKEN')
    strapi_token = env.str('STRAPI_TOKEN')
    strapi_host = env.str('STRAPI_HOST', 'http://localhost:1337/')
    strapi_product_name = env.str('PRODUCT', 'product')
    strapi_product_name_plural = env.str('PRODUCT_PLURAL', 'products')
    strapi_ordered_product_name_plural = env.str('ORDERED_PRODUCT_PLURAL', 'ordered-products')
    strapi_cart_name_plural = env.str('CART_PLURAL', 'carts')
    strapi_customer_name_plural = env.str('CUSTOMER_PLURAL', 'customers')

    redis_db = redis.Redis(host=env.str('REDIS_DB_HOST'),
                           port=env.int('REDIS_DB_PORT'),
                           password=env.str('REDIS_DB_PASSWORD'),
                           decode_responses=True)

    updater = Updater(tg_bot_token)
    dispatcher = updater.dispatcher

    dispatcher.bot_data['redis_db'] = redis_db
    dispatcher.bot_data['strapi_token'] = strapi_token
    dispatcher.bot_data['strapi_host'] = strapi_host
    dispatcher.bot_data['models_config'] = {
        'strapi_product_name': strapi_product_name,
        'strapi_product_name_plural': strapi_product_name_plural,
        'strapi_ordered_product_name_plural': strapi_ordered_product_name_plural,
        'strapi_cart_name_plural': strapi_cart_name_plural,
        'strapi_customer_name_plural': strapi_customer_name_plural
    }

    dispatcher.add_handler(CallbackQueryHandler(handle_users_reply))
    dispatcher.add_handler(MessageHandler(Filters.text, handle_users_reply))
    dispatcher.add_handler(CommandHandler('start', handle_users_reply))

    updater.start_polling()
    updater.idle()


def start(update: Update, context: CallbackContext):
    """Хэндлер для состояния START."""
    hostname = context.bot_data['strapi_host']
    models_config = context.bot_data['models_config']
    products = get_products(context.bot_data['strapi_token'], hostname, models_config)
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

    api_token = context.bot_data['strapi_token']
    hostname = context.bot_data['strapi_host']
    models_config = context.bot_data['models_config']
    user_cart = get_or_create_cart(query.message.chat_id, hostname, models_config, api_token)
    ordered_products = get_cart_ordered_products(user_cart, api_token, hostname, models_config, as_text=False)
    cart_text = get_cart_ordered_products(user_cart, api_token, hostname, models_config, as_text=True)

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
    hostname = context.bot_data['strapi_host']
    models_config = context.bot_data['models_config']

    query = update.callback_query
    query.answer()
    if query.data == 'cancel':
        query.answer()
        return start(update, context)
    if query.data.startswith('remove_item'):
        ordered_product_id = query.data.split(';')[1]
        remove_ordered_product(ordered_product_id, context.bot_data['starapi_token'], hostname, models_config)
        return cart(update, context)
    if query.data == 'payment':
        return request_an_email(update, context)


def request_an_email(update: Update, context: CallbackContext):
    update.callback_query.message.reply_text(text='Для оплаты введите Ваш адрес электронной почты.')
    update.callback_query.delete_message()
    return 'WAITING_EMAIL'


def process_email(update: Update, context: CallbackContext):
    api_token = context.bot_data['strapi_token']
    hostname = context.bot_data['strapi_host']
    models_config = context.bot_data['models_config']
    users_email = update.message.text
    customer_id = get_or_create_customer(update.message.chat_id, api_token, hostname, models_config)['id']
    try:
        customer = save_customer_email(customer_id, users_email, api_token, hostname, models_config)
        update.message.reply_text('Заказ принят! Ожидайте обращения нашего менеджера на Ваш e-mail!')
        return start(update, context)
    except requests.exceptions.HTTPError:
        update.message.reply_text('E-mail введён некорректно! Повторите ввод.')
        return 'WAITING_EMAIL'


def select_menu_item(update: Update, context: CallbackContext):
    hostname = context.bot_data['strapi_host']
    models_config = context.bot_data['models_config']

    query = update.callback_query
    if query.data == 'cart':
        return cart(update, context)
    query.answer()

    product_detail = get_product_detail(query.data, context.bot_data['starapi_token'], hostname, models_config)
    image = get_product_img(product_detail['Image']['data']['attributes']['url'], hostname)

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
        api_token = context.bot_data['strapi_token']
        hostname = context.bot_data['strapi_host']
        models_config = context.bot_data['models_config']
        user_cart = get_or_create_cart(query.message.chat_id, hostname, models_config, api_token)
        ordered_product = create_ordered_product(product_id, api_token, hostname, models_config, cart_id=user_cart['id'])
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
