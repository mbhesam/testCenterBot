import redis
from telegramBot.config import (
    REDIS_HOST,
    REDIS_PORT,
    REDIS_USERNAME,
    REDIS_PASSWORD
)
import json

# Redis setup
redis_client = redis.Redis(host=REDIS_HOST,port=REDIS_PORT,
                           username=REDIS_USERNAME, password=REDIS_PASSWORD, db=0, decode_responses=True)

def get_user_key(username):
    return f"user:{username}"

def get_user_data(username):
    data = redis_client.get(get_user_key(username))
    return json.loads(data) if data else {'status': 'start', 'info': {}, 'test_off_count': 0, 'share_off_count': 0, 'info_complete': False}

def save_user_data(username, data):
    redis_client.set(get_user_key(username), json.dumps(data))
def clear_user_data(username):
    redis_client.delete(get_user_key(username))
def get_exam_key(username):
    return f"exam:{username}"
def get_exam_data(username):
    data = redis_client.get(get_exam_key(username))
    if data:
        return json.loads(data)
    return {
        'data': [],
        'state': 'in_exam',
        'current_question': 0,
        'current_selections': [],
        'user_answers': [],
        'score': 0
    }

def save_exam_data(username, data):
    redis_client.set(get_exam_key(username), json.dumps(data))
def clear_exam_data(username):
    redis_client.delete(get_exam_key(username))

def clear_share_count(username):
    user_data = get_user_data(username=username)
    user_data['share_off_count'] = 0
    redis_client.set(get_exam_key(username), json.dumps(user_data))
