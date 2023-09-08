from urllib.parse import urljoin
from io import BytesIO

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


if __name__ == '__main__':
    import os
    from dotenv import load_dotenv
    load_dotenv()
    token = os.getenv('STARAPI_TOKEN')
    products = get_product_detail(1, token)
    from pprint import pprint
    pprint(products)
    #
    # print(urljoin('http://localhost:1337/', '/uploads/medium_maratmqutkdw_518eda9db2.jpg'))
