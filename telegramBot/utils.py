from config import (
    GRADE_A_OFF,
    GRADE_B_OFF,
    GRADE_S_OFF,
    PRODUCT_IDS_A,
    PRODUCT_IDS_B,
    PRODUCT_IDS_S,
    WEBSITE_API_URL,
    WEBSITE_API_KEY,
)
from common import (
    GRADE_A_MESSAGE,
    GRADE_B_MESSAGE,
    GRADE_C_MESSAGE,
    GRADE_S_MESSAGE,
)
import random
import httpx
import yaml
import asyncio
def load_cities_by_state_and_country(state_code, country_code):
    with open('/home/hesam/projects/testCenterBot/data/cities.yml', 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    return [
        city for city in data['city']
        if city['state_code'] == state_code and city['country_code'] == country_code
    ]
def load_countries():
    with open('/home/hesam/projects/testCenterBot/data/countries.yml', 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
        return data['country']


def load_states_by_country_code(iso2_code: str):
    with open("/home/hesam/projects/testCenterBot/data/states.yml", "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
        all_states = data['state']
        return [state for state in all_states if state['country_code'] == iso2_code]

def check_grade(score=-1):
    if score == -1:
        return 'S',GRADE_S_MESSAGE,True
    elif score >= 8:
        return 'A',GRADE_A_MESSAGE,True
    elif score >= 6 and score < 8:
        return 'B',GRADE_B_MESSAGE,True
    else:
        return 'C',GRADE_C_MESSAGE,False

import requests

def approve_off_code(grade, phone_number):
    if grade == 'A':
        off_code = asyncio.run(submit_off_code(phone_number, GRADE_A_OFF, PRODUCT_IDS_A))
    elif grade == 'B':
        off_code = asyncio.run(submit_off_code(phone_number, GRADE_B_OFF, PRODUCT_IDS_B))
    elif grade == 'S':
        off_code = asyncio.run(submit_off_code(phone_number, GRADE_S_OFF, PRODUCT_IDS_S))
    else:
        off_code = None
    return off_code

async def submit_off_code(phone_number, off_percent, product_ids):
    try:
        print("submitting")
        data = {
            'api_key': WEBSITE_API_KEY,
            'discount_type': 'percent',
            'username': phone_number,
            'discount_percent': off_percent,
            'usage_limit': '1',
            'expiry_date': '2025-08-01',
            'product_ids[]': product_ids  # httpx handles list values automatically
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url=WEBSITE_API_URL,
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded'
                },
                data=data
            )
            response.raise_for_status()
            response_obj = response.json()
            if response_obj.get('status') == 'success':
                return response_obj['coupon']['code']  # Return just the coupon code
            else:
                raise ValueError("API request was not successful")
    except httpx.HTTPStatusError as e:
        print(f"HTTP error occurred: {e.response.status_code} - {e.response.text}")
    except Exception as e:
        print(f"An error occurred: {e}")
        print(f'exception on calling website api:\n{e}')

async def fetch_questions():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            'http://testcenter.hesamhelperdomain.ir/v1/table/test/question/read',
            headers={
                'accept': 'application/json',
                'Content-Type': 'application/json'
            },
            json={}
        )
        response.raise_for_status()
        response_obj = response.json()
        if len(response_obj['data']) < 10:
            print("❌ not enough questions exist")
            return None
        selected_data = random.sample(response_obj['data'], 10)
        return selected_data
