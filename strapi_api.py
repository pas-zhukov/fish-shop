from urllib.parse import urljoin
from io import BytesIO
from decimal import Decimal
import posixpath

import requests


def get_products(api_token: str, hostname: str, models_config: dict) -> list[dict]:
    product_model_plural = models_config['strapi_product_name_plural']
    api_hand = posixpath.join('/api/', product_model_plural)
    api_url = urljoin(hostname, api_hand)
    headers = {
        'Authorization': f'bearer {api_token}'
    }
    response = requests.get(api_url, headers=headers)
    response.raise_for_status()
    return response.json()['data']


def get_ordered_products(api_token: str,
                         hostname: str,
                         models_config: dict,
                         ids: list[int] = None) -> list[dict]:
    ordered_product_model_plural = models_config['strapi_ordered_product_name_plural']
    api_hand = posixpath.join('/api/', ordered_product_model_plural)
    api_url = urljoin(hostname, api_hand)
    headers = {
        'Authorization': f'bearer {api_token}'
    }
    params = {
        'populate': f'{models_config["strapi_product_name"]}',
        'filters[id][$eq]': ids
    }
    response = requests.get(api_url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()['data']


def get_product_detail(product_id: int | str,
                       api_token: str,
                       hostname: str,
                       models_config: dict,
                       with_img: bool = True) -> dict:
    """Get product detailed info.

    Examples:
        >>> get_product_detail(2, token, with_img=False)
        {
          'Description': 'Дикий лосось "Стейк рыбацкий" с/м 600г',
          'Price': 420,
          'Title': 'Дикий лосось «Стейк рыбацкий» свежемороженый 600 г',
          'createdAt': '2023-09-08T09:30:41.000Z',
          'publishedAt': '2023-09-08T09:30:42.652Z',
          'updatedAt': '2023-09-08T09:30:42.656Z'
        }
    """
    product_model_plural = models_config['strapi_product_name_plural']
    api_hand = posixpath.join('/api/', product_model_plural, product_id)
    api_url = urljoin(hostname, api_hand)
    headers = {
        'Authorization': f'bearer {api_token}'
    }
    params = {
        'populate': 'Image' if with_img else None
    }
    response = requests.get(api_url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()['data']['attributes']


def get_product_img(img_url: str,
                    hostname: str) -> BytesIO:
    full_img_url = urljoin(hostname, img_url)
    response = requests.get(full_img_url)
    response.raise_for_status()
    image = BytesIO(response.content)
    return image


def get_or_create_cart(user_id: int | str,
                       hostname: str,
                       models_config: dict,
                       api_token: str) -> dict:
    """Get cart of a specific user.

    Args:
        user_id(int): ID of the user for whom you want to create or get a cart
        hostname: STRAPI host url
        cart_model_plural: cart model plural name
        api_token(str): STRAPI Token
    Return:
        int: Cart of a specified user
    """
    cart_model_plural = models_config['strapi_cart_name_plural']
    api_hand = posixpath.join('/api/', cart_model_plural)
    api_url = urljoin(hostname, api_hand)
    headers = {
        'Authorization': f'bearer {api_token}'
    }
    params = {
        'populate': [f'models_config["strapi_ordered_product_name_plural"]', f'{models_config["strapi_product_name_plural"]}'],
        'filters[user_tg_id][$eq]': user_id
    }
    response = requests.get(api_url, headers=headers, params=params)
    response.raise_for_status()
    carts = response.json()['data']
    if carts:
        return carts[0]
    new_cart = {
        'data': {
            'user_tg_id': user_id
        }
    }
    create_response = requests.post(api_url, headers=headers, json=new_cart)
    create_response.raise_for_status()
    return create_response.json()['data']


def get_cart_ordered_products(cart: dict,
                              api_token: str,
                              hostname: str,
                              models_config: dict,
                              as_text: bool = False):
    ordered_products_raw = cart['attributes']['ordered_products']['data']
    ordered_products_ids = [product['id'] for product in ordered_products_raw]
    ordered_products_with_products_raw = get_ordered_products(api_token,
                                                              ids=ordered_products_ids,
                                                              models_config=models_config,
                                                              hostname=hostname)
    ordered_products = [
        {
            'amount': product['attributes']['amount'],
            'fixed_price': product['attributes']['fixed_price'],
            'id': product['id'],
            'title': product['attributes']['product']['data']['attributes']['Title']
        } for product in ordered_products_with_products_raw
    ]
    if not as_text:
        return ordered_products
    texts = [
        f'Товар: {product["title"]}\nКол-во (кг): {product["amount"]}\nЦена за кг: {product["fixed_price"]}\n' for product in ordered_products
    ]
    text = '\n'.join(texts)
    return text


def create_ordered_product(product_id: int | str,
                           api_token: str,
                           hostname: str,
                           models_config: dict,
                           cart_id: int | str = None,
                           amount: float = 1.0,
                           fixed_price: Decimal = None) -> dict:
    """Create OrderedProduct from Product.

    Creates OrderedProduct based on selected Product
    with specified amount and price (if needed).

    Args:
        product_id(int | str): Product ID.
        api_token(str): STRAPI Token.
        hostname: ...
        models_config: ...
        cart_id(int | str): Cart ID to which created OrderedProduct should be connected. None by default.
        amount(float): Product amount. 1 kg by default.
        fixed_price(Decimal): Price that will be fixed for this product in this particular OrderedProduct.
        If no argument passed, Product price will be used.

    Return:
        dict: Created OrderedProduct

    Examples:
        >>> create_ordered_product(2, token, cart_id)
        {
          "attributes":{
            "amount":1,
            "cart":{
              "data":{
                "attributes":{
                  "createdAt":"2023-09-10T07:54:26.730Z",
                  "publishedAt":"2023-09-10T07:54:26.706Z",
                  "total_price":"None",
                  "updatedAt":"2023-09-10T07:54:26.730Z",
                  "user_tg_id":"99"
                },
                "id":4
              }
            },
            "createdAt":"2023-09-10T08:17:45.877Z",
            "fixed_price":420,
            "product":{
              "data":{
                "attributes":{
                  "Description":"Дикий лосось Стейк рыбацкийnс/м 600г",
                  "Price":420,
                  "Title":"Дикий лосось «Стейк рыбацкий» свежемороженый 600 г",
                  "createdAt":"2023-09-08T09:30:41.000Z",
                  "publishedAt":"2023-09-08T09:30:42.652Z",
                  "updatedAt":"2023-09-08T09:30:42.656Z"
                },
                "id":2
              }
            },
            "publishedAt":"2023-09-10T08:17:45.868Z",
            "updatedAt":"2023-09-10T08:17:45.877Z"
          },
          "id":5
        }
    """
    ordered_product_model_plural = models_config['strapi_ordered_product_name_plural']
    api_hand = posixpath.join('/api/', ordered_product_model_plural)
    api_url = urljoin(hostname, api_hand)
    headers = {
        'Authorization': f'bearer {api_token}'
    }
    if not fixed_price:
        product = get_product_detail(product_id, api_token, with_img=False)
        fixed_price = product['Price']
    new_ordered_product = {
        'data': {
            'product': {
                'connect': [product_id, ]
            },
            'cart': {
                'connect': [cart_id, ]
            },
            'amount': amount,
            'fixed_price': fixed_price,
        }
    }
    params = {
        'populate': ['product', 'cart'],
    }
    create_response = requests.post(api_url,
                                    headers=headers,
                                    params=params,
                                    json=new_ordered_product)
    create_response.raise_for_status()
    return create_response.json()['data']


def remove_ordered_product(product_id: int | str,
                           api_token: str,
                           hostname: str,
                           models_config: dict):
    ordered_product_model_plural = models_config['strapi_ordered_product_name_plural']
    api_hand = posixpath.join('/api/', ordered_product_model_plural, product_id)
    api_url = urljoin(hostname, api_hand)
    headers = {
        'Authorization': f'bearer {api_token}'
    }
    response = requests.delete(api_url, headers=headers)
    response.raise_for_status()
    return response.json()


def add_ordered_product_into_cart(ordered_product_id: int | str,
                                  cart_id: int | str,
                                  api_token: str) -> dict:
    """Add OrderedProduct into specific Cart.

    Args:
        ordered_product_id(int | str): OrderedProduct ID, which will be added into Cart
        cart_id(int | str): Cart ID
        api_token(str): STRAPI Token
    Return:
        dict: Updated OrderedProduct
    """
    #  TODO: fill up this function :)
    #  use requests.put!


def get_or_create_customer(user_tg_id: int | str,
                           api_token: str,
                           hostname: str,
                           models_config: dict) -> dict:
    customer_model_plural = models_config['strapi_customer_name_plural']
    api_hand = posixpath.join('/api/', customer_model_plural)
    api_url = urljoin(hostname, api_hand)
    headers = {
        'Authorization': f'bearer {api_token}'
    }
    params = {
        'filters[telegram_id][$eq]': user_tg_id
    }
    response = requests.get(api_url, headers=headers, params=params)
    response.raise_for_status()
    users = response.json()['data']
    if users:
        return users[0]
    new_customer = {
        'data': {
            'telegram_id': user_tg_id,
        }
    }
    create_response = requests.post(api_url, headers=headers, json=new_customer)
    create_response.raise_for_status()
    return create_response.json()['data']


def save_customer_email(customer_id: int | str,
                        email: str,
                        api_token: str,
                        hostname: str,
                        models_config: dict
                        ):
    customer_model_plural = models_config['strapi_customer_name_plural']
    api_hand = posixpath.join('/api/', customer_model_plural, customer_id)
    api_url = urljoin(hostname, api_hand)
    headers = {
        'Authorization': f'bearer {api_token}'
    }
    update_json = {
        'data': {
            'email': email,
        }
    }
    response = requests.put(api_url, headers=headers, json=update_json)
    response.raise_for_status()
    return response.json()['data']
