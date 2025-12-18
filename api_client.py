import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('TENANTOS_API_KEY')
API_URL = os.getenv('TENANTOS_API_URL', 'https://manage.linveo.com/api')


def fetch_servers():
    headers = {
        'Authorization': f'Bearer {API_KEY}',
        'Accept': 'application/json'
    }

    response = requests.get(f'{API_URL}/servers', headers=headers)
    response.raise_for_status()

    data = response.json()
    return data.get('result', [])
