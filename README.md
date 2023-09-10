# Бот магазина Рыбы

Бот для заказа рыбы на базе CRM [STRAPI](https://strapi.io/)

![fish_shop_preview](https://github.com/pas-zhukov/fish-shop/assets/117192371/8230122c-0e47-4624-b7fd-b6e171c27fcb)


# Развертывание бота

Первым делом, скачайте код:

```shell
git clone https://github.com/pas-zhukov/fish-shop.git
```

Установите зависимости командой:

```shell
pip install -r requirements.txt
```

## Подготовка CRM

Для работы необходимо запустить на компьютере разработческую версию CRM STRAPI, которая будет развернута по адресу http://localhost:1337/.

Создайте следующие модели с перечисленными полями (в админке по адресу http://localhost:1337/admin/plugins/content-type-builder/):

**Product:**
- Title (Text)
- Description (Rich Text)
- Image (Media)
- Price (Decimal Number)

**Cart:**
- total_price (decimal Number)
- user_tg_id (Integer Number)

**OrderedProduct:**
- product (relation with Product)
- amount (Float Number)
- fixed_price (Decimal Number)
- cart (relation with Cart)

**Customer:**
- telegram_id (Integer Number)
- email (Email)

Заполните 2-3 штуки Products и можно приступать к тестированию бота.

## Переменные окружения

Для работы Вам понадобится БД Redis. Получить можно после регистрации тут: https://redislabs.com/ (нужен VPN).

Для работы ботов необходимо в корне с программой создать файл `.env` и заполнить его следующим содержимым:
```shell
TG_BOT_TOKEN=<API-токен Вашего Телеграм-бота>
STARAPI_TOKEN=<API-токен STRAPI, получить можно в админке CRM>
REDIS_DB_HOST=<Адрес базы данных Redis>
REDIS_DB_PORT=<Порт БД Redis>
REDIS_DB_PASSWORD=<Пароль БД Redis>
```

## Запуск

Для запуска Телеграм бота используйте следующую команду:

```shell
python bot.py
```

# Цели проекта

Код написан в учебных целях.
