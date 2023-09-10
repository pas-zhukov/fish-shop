from urllib.parse import urljoin
from io import BytesIO
from decimal import Decimal

import requests


BASE_STARAPI_URL = 'http://localhost:1337/'


def get_products(api_token: str) -> list[dict]:
    api_url = 'http://localhost:1337/api/products/'
    headers = {
        'Authorization': f'bearer {api_token}'
    }
    response = requests.get(api_url, headers=headers)
    response.raise_for_status()
    return response.json()['data']


def get_product_detail(product_id: int | str, api_token: str, with_img: bool = True) -> dict:
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
    api_url = f'http://localhost:1337/api/products/{product_id}/'
    headers = {
        'Authorization': f'bearer {api_token}'
    }
    params = {
        'populate': 'Image' if with_img else None
    }
    response = requests.get(api_url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()['data']['attributes']


def get_product_img(img_url: str) -> BytesIO:
    full_img_url = urljoin(BASE_STARAPI_URL, img_url)
    response = requests.get(full_img_url)
    response.raise_for_status()
    image = BytesIO(response.content)
    return image


def get_or_create_cart(user_id: int | str, api_token: str) -> dict:
    """Get cart of a specific user.

    Args:
        user_id(int): ID of the user for whom you want to create or get a cart
        api_token(str): STRAPI Token
    Return:
        int: Cart of a specified user
    """
    api_url = f'http://localhost:1337/api/carts/'
    headers = {
        'Authorization': f'bearer {api_token}'
    }
    params = {
        'populate': 'ordered_products',
        'filters[user_tg_id][$eq]': user_id
    }
    response = requests.get(api_url, headers=headers, params=params)
    response.raise_for_status()
    carts = response.json()['data']
    if carts:
        return carts[0]
    create_json = {
        'data': {
            'user_tg_id': user_id
        }
    }
    create_response = requests.post(api_url, headers=headers, json=create_json)
    create_response.raise_for_status()
    return create_response.json()['data']


def create_ordered_product(product_id: int | str,
                           api_token: str,
                           cart_id: int | str = None,
                           amount: float = 1.0,
                           fixed_price: Decimal = None) -> dict:
    """Create OrderedProduct from Product.

    Creates OrderedProduct based on selected Product
    with specified amount and price (if needed).

    Args:
        product_id(int | str): Product ID.
        api_token(str): STRAPI Token.
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
    api_url = f'http://localhost:1337/api/ordered-products/'
    headers = {
        'Authorization': f'bearer {api_token}'
    }
    if not fixed_price:
        product = get_product_detail(product_id, api_token, with_img=False)
        fixed_price = product['Price']
    create_json = {
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
                                    json=create_json)
    create_response.raise_for_status()
    return create_response.json()['data']


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


if __name__ == '__main__':
    import os
    from dotenv import load_dotenv
    from pprint import pprint
    load_dotenv()
    token = os.getenv('STARAPI_TOKEN')
    car = get_or_create_cart(99, token)
    car_id = car['id']
    or_pro = create_ordered_product(2, token, car_id)

    pprint(or_pro)
    #
    # print(urljoin('http://localhost:1337/', '/uploads/medium_maratmqutkdw_518eda9db2.jpg'))
