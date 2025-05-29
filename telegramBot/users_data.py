import redis
from telegramBot.config import (
    REDIS_HOST,
    REDIS_PORT,
    REDIS_USERNAME,
    REDIS_PASSWORD
)
# Redis setup
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

def get_user_key(username):
    return f"user:{username}"

def get_user_data(username):
    data = redis_client.get(get_user_key(username))
    return json.loads(data) if data else {'step': 0, 'answers': {}}

def save_user_data(username, data):
    redis_client.set(get_user_key(username), json.dumps(data))

def clear_user_data(username):
    redis_client.delete(get_user_key(username))