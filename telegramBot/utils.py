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

def check_grade(score=-1):
    if score == -1:
        return 'S',GRADE_S_MESSAGE,True
    elif score >= 8:
        return 'A',GRADE_A_MESSAGE,True
    elif score >= 6 and score < 8:
        return 'B',GRADE_B_MESSAGE,True
    else:
        return 'C',GRADE_C_MESSAGE,False

def approve_off_code(grade):
    if grade == 'A':
        submit_off_code(GRADE_A_OFF, PRODUCT_IDS_A)

async def submit_off_code(off_percent, product_ids):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                WEBSITE_API_KEY,
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded'
                },
                json={}
            )
            response.raise_for_status()
            response_obj = response.json()


    except Exception as e:
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
