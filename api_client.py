import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('TENANTOS_API_KEY')
API_URL = os.getenv('TENANTOS_API_URL', 'https://manage.linveo.com/api')


def get_headers():
    return {
        'Authorization': f'Bearer {API_KEY}',
        'Accept': 'application/json'
    }


def fetch_servers():
    response = requests.get(f'{API_URL}/servers', headers=get_headers())
    response.raise_for_status()

    data = response.json()
    return data.get('result', [])


def fetch_server_inventory(server_id):
    response = requests.get(f'{API_URL}/servers/{server_id}/inventory', headers=get_headers())
    response.raise_for_status()

    data = response.json()
    return data.get('result', [])
