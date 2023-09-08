import logging
import redis
from environs import Env

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Filters, Updater, CallbackContext
from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler

from api_funcs import get_products, get_product_detail, get_product_img


logger = logging.getLogger(__name__)


def main():
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        level=logging.INFO)
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
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        update.message.reply_text(text='Выбери товар.', reply_markup=reply_markup)
    else:
        update.callback_query.message.reply_text(text='Выбери товар.', reply_markup=reply_markup)
        update.callback_query.delete_message()
    return 'HANDLE_MENU'


def select_menu_item(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    product_detail = get_product_detail(query.data, context.bot_data['starapi_token'])
    image = get_product_img(product_detail['Image']['data']['attributes']['url'])

    keyboard = [
        [InlineKeyboardButton('Назад', callback_data='cancel')]
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
        'HANDLE_DESCRIPTION': detail_result
    }
    state_handler = states_functions[user_state]

    try:
        next_state = state_handler(update, context)
        redis_db.set(chat_id, next_state)
    except Exception as err:
        print(err)


if __name__ == '__main__':
    main()
