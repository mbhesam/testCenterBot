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
import requests
from telegram_bot_calendar import DetailedTelegramCalendar
from telegram_bot_calendar.detailed import STEPS,PREV_STEPS,PREV_ACTIONS,SELECT,NOTHING,YEAR
from telegram_bot_calendar.base import *
from datetime import date
from dateutil.relativedelta import relativedelta

def load_cities_by_state_and_country(state_code, country_code):
    with open('data/cities.yml', 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    return [
        city for city in data['city']
        if city['state_code'] == state_code and city['country_code'] == country_code
    ]
def load_countries():
    with open('data/countries.yml', 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
        return data['country']


def load_states_by_country_code(iso2_code: str):
    with open("data/states.yml", "r", encoding="utf-8") as f:
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

def is_integer_and_length_enough(s):
    if s.isdigit() and len(s) == 10:
        return True
    return False

def submit_off_code_sync(phone_number, off_percent, product_ids):
    try:
        print("Submitting discount code request...")
        # Prepare the data exactly as in the curl command
        data = {
            'api_key': WEBSITE_API_KEY,
            'discount_type': 'percent',
            'username': phone_number,
            'discount_percent': str(off_percent),  # Ensure it's string as in curl
            'usage_limit': '1',
            'expiry_date': '2025-08-01'
        }

        # Add product_ids as separate key-value pairs
        if isinstance(product_ids, (list, tuple)):
            for i, pid in enumerate(product_ids):
                data[f'product_ids[]'] = str(pid)  # Same key for each product ID
        else:
            data['product_ids[]'] = str(product_ids)

        response = requests.post(
            url=WEBSITE_API_URL,
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            data=data,  # Using data instead of json
            timeout=10.0
        )

        print(f"Response status: {response.status_code}")  # Debugging
        print(f"Response text: {response.text}")  # Debugging

        response.raise_for_status()
        response_obj = response.json()

        if response_obj.get('status') == 'success':
            return response_obj['coupon']['code']
        raise ValueError(f"API request failed: {response_obj.get('message', 'Unknown error')}")

    except requests.exceptions.HTTPError as e:
        print(f"HTTP error {e.response.status_code}: {e.response.text}")
        return None
    except Exception as e:
        print(f"Error submitting off code: {str(e)}")
        return None


def approve_off_code_sync(grade, phone_number):
    """Synchronous version"""
    if grade == 'A':
        return submit_off_code_sync(phone_number, GRADE_A_OFF, PRODUCT_IDS_A)
    elif grade == 'B':
        return submit_off_code_sync(phone_number, GRADE_B_OFF, PRODUCT_IDS_B)
    elif grade == 'S':
        return submit_off_code_sync(phone_number, GRADE_S_OFF, PRODUCT_IDS_S)
    print(f"Invalid grade: {grade}")
    return None

async def submit_off_code(phone_number, off_percent, product_ids):
    try:
        print("Submitting discount code request...")
        data = {
            'api_key': WEBSITE_API_KEY,
            'discount_type': 'percent',
            'username': phone_number,
            'discount_percent': off_percent,
            'usage_limit': '1',
            'expiry_date': '2025-08-01',
            'product_ids[]': product_ids
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url=WEBSITE_API_URL,
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                data=data,
                timeout=10.0  # Added timeout for safety
            )
            response.raise_for_status()
            response_obj = response.json()

            if response_obj.get('status') == 'success':
                return response_obj['coupon']['code']
            raise ValueError(f"API request failed: {response_obj.get('message', 'Unknown error')}")

    except httpx.HTTPStatusError as e:
        print(f"HTTP error {e.response.status_code}: {e.response.text}")
        return None
    except Exception as e:
        print(f"Error submitting off code: {str(e)}")
        return None


async def approve_off_code(grade, phone_number):
    """Async version that should be called from async context"""
    if grade == 'A':
        return await submit_off_code(phone_number, GRADE_A_OFF, PRODUCT_IDS_A)
    elif grade == 'B':
        return await submit_off_code(phone_number, GRADE_B_OFF, PRODUCT_IDS_B)
    elif grade == 'S':
        return await submit_off_code(phone_number, GRADE_S_OFF, PRODUCT_IDS_S)
    print(f"Invalid grade: {grade}")
    return None


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

class MyStyleCalendar(DetailedTelegramCalendar):
    prev_button = "⬅️"
    next_button = "➡️"
    size_year = 6
    size_year_column = 12

    def _build_years(self, *args, **kwargs):
        years_num = self.size_year * self.size_year_column

        start = self.current_date - relativedelta(years=years_num)
        years = self._get_period(YEAR, start, years_num)
        years_buttons = rows(
            [
                self._build_button(d.year if d else self.empty_year_button, SELECT if d else NOTHING, YEAR, d,
                                   is_random=self.is_random)
                for d in years
            ],
            self.size_year
        )

        nav_buttons = self._build_nav_buttons(YEAR, diff=relativedelta(years=years_num),
                                              mind=max_date(start, YEAR),
                                              maxd=min_date(start + relativedelta(years=years_num - 1), YEAR))

        self._keyboard = self._build_keyboard(years_buttons + nav_buttons)
