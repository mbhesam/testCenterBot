from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
    ContextTypes,
    CallbackQueryHandler,
    MessageHandler,
    filters
)
from common import (
    WELCOME_MESSAGE,
    INFO_QUESTIONS,
    START_BUTTON,
    START_EXAM_BUTTON,
    NOT_COMPELETED_INFO,
    ALREADY_SUBMITTED,
    PREPARING_QUESTIONS,
    FAILED_FETCH_DATA,
    END_EXAM_WITHOUT_OFF,
    END_EXAM_TIME
)
from utils import (
    fetch_questions,
    check_grade
)
from users_data import (
    clear_user_data,
    get_user_data,
    save_user_data,
    get_exam_data,
    save_exam_data,
    clear_exam_data
)
from config import EXAM_DURATION_SECONDS
import json
import time
import math

# States
STATES = {
    'start': 0,
    'get_info': 1,
    'start_exam': 2,
}

# /start
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.effective_user.username
    user_data = get_user_data(username=username)
    await update.message.reply_text(WELCOME_MESSAGE)
    if user_data.get('status') == 'ready_exam':
        await update.message.reply_text(ALREADY_SUBMITTED)
        return STATES['start_exam']
    _, fq = INFO_QUESTIONS[0]
    await update.message.reply_text(fq)  # ask for phone number
    user_data['status'] = 'collecting_phone'
    save_user_data(username=username, data=user_data)
    return STATES['get_info']

# Info collection
async def get_info_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.effective_user.username
    user_data = get_user_data(username=username)

    if user_data.get('status') == 'collecting_phone':
        user_data['info']['phone'] = update.message.text
        _, sq = INFO_QUESTIONS[1]
        await update.message.reply_text(sq)  # ask for suggester
        user_data['status'] = 'collecting_suggester'
        save_user_data(username=username, data=user_data)
        return STATES['get_info']

    elif user_data.get('status') == 'collecting_suggester':
        user_data['info']['suggester'] = update.message.text
        user_data['status'] = 'ready_exam'
        save_user_data(username=username, data=user_data)

        await update.message.reply_text(
            f"""
    ✅ ممنونم دوست عزیز
    📞 شماره همراه ثبت شده:
    {user_data['info']['phone']} 
    💡 معرف:
    {user_data['info']['suggester']}
                """,
            reply_markup=ReplyKeyboardMarkup([[START_EXAM_BUTTON, START_BUTTON]], one_time_keyboard=True,
                                             resize_keyboard=True)
        )
        return STATES['start_exam']

async def start_exam_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.effective_user.username
    clear_exam_data(username=username)
    user_data = get_user_data(username=username)
    if user_data['status'] != 'ready_exam':
        await update.message.reply_text(NOT_COMPELETED_INFO)
        return STATES['get_info']

    await update.message.reply_text(PREPARING_QUESTIONS)
    # Fetch questions from API
    try:
        data = await fetch_questions()
        await send_question(update, context, selected_data=data)
    except Exception as e:
        print(e)
        await update.message.reply_text(FAILED_FETCH_DATA)
        return ConversationHandler.END


async def send_question(update: Update, context: ContextTypes.DEFAULT_TYPE, selected_data):
    username = update.effective_user.username
    exam_data = {}
    current_time = time.time()
    exam_data['data'] = selected_data
    exam_data['current_question'] = 0
    exam_data['score'] = 0
    exam_data['user_answers'] = []
    exam_data['state'] = 'in_exam'
    exam_data['current_selections'] = []
    exam_data['start_time'] = current_time
    exam_data['end_time'] = current_time + EXAM_DURATION_SECONDS
    save_exam_data(username, exam_data)
    await send_current_question(update, context, username)

async def send_current_question(update: Update, context: ContextTypes.DEFAULT_TYPE, username):
    exam_data = get_exam_data(username)
    index = exam_data['current_question']
    question_data = exam_data['data'][index]
    question_text = question_data['question']
    options = json.loads(question_data['options'])
    # Time left
    current_time = time.time()
    remaining_seconds = int(exam_data['end_time'] - current_time)
    if remaining_seconds < 0:
        remaining_seconds = 0
    remaining_minutes = math.ceil(remaining_seconds / 60)
    time_info = f"\n⏳ زمان باقی‌مانده: {remaining_minutes} دقیقه"

    # Multi-select support
    current_selection = exam_data.get('current_selections', [])
    exam_data['current_selections'] = current_selection
    save_exam_data(username, exam_data)

    keyboard = [
        [InlineKeyboardButton(text=(f"✅ {opt}" if i in current_selection else opt),
                              callback_data=f"opt|{username}|{i}")]
        for i, opt in enumerate(options)
    ]
    keyboard.append([InlineKeyboardButton(text="✅ ثبت پاسخ ها", callback_data=f"submit|{username}")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    full_text = question_text + time_info
    if update.callback_query:
        await update.callback_query.message.edit_text(full_text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(full_text, reply_markup=reply_markup)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split('|')
    action = parts[0]
    username = parts[1]
    exam_data = get_exam_data(username)
    user_data = get_user_data(username=username)

    current_time = time.time()
    if current_time > exam_data.get('end_time', current_time + 1):
        # Time's up
        exam_data['state'] = 'finished'
        save_exam_data(username, exam_data)
        exam_grade, grade_message, get_off = check_grade(score=exam_data['score'])
        await update.callback_query.message.reply_text(END_EXAM_TIME + f"📝 نمره آزمون شما: {exam_data['score']}\n" + grade_message)

        if get_off:
            user_data['off_count'] += 1
            clear_exam_data(username=username)
            save_user_data(username=username, data=user_data)
            if user_data['off_count'] >= 4:
                await update.callback_query.message.reply_text(END_EXAM_WITHOUT_OFF)
                return STATES['start']
        return

    # Proceed with handling if still in time
    index = exam_data['current_question']

    if action == 'opt':
        opt_index = int(parts[2])
        if opt_index in exam_data['current_selections']:
            exam_data['current_selections'].remove(opt_index)
        else:
            exam_data['current_selections'].append(opt_index)
        save_exam_data(username, exam_data)
        await send_current_question(update, context, username)

    elif action == 'submit':
        try:
            user_selected = set(exam_data['current_selections'])
            correct_answers = set(json.loads(exam_data['data'][index]['answers']))
            if user_selected == correct_answers:
                exam_data['score'] += 1

            exam_data['user_answers'].append(list(user_selected))
            exam_data['current_question'] += 1
            exam_data['current_selections'] = []

            if exam_data['current_question'] < len(exam_data['data']):
                save_exam_data(username, exam_data)
                await send_current_question(update, context, username)
            else:
                exam_data['state'] = 'finished'
                save_exam_data(username, exam_data)
                exam_grade, grade_message, get_off = check_grade(score=exam_data['score'])
                await update.callback_query.message.reply_text(f"📝 نمره آزمون شما: {exam_data['score']}" + grade_message)
                if get_off:
                    user_data['off_count'] += 1
                    clear_exam_data(username=username)
                    save_user_data(username=username, data=user_data)
                    if user_data['off_count'] >= 4:
                        await update.callback_query.message.reply_text(END_EXAM_WITHOUT_OFF)
                        return STATES['start']
        except Exception as e:
            print(f"Error handling submit: {e}")
            await query.answer(FAILED_FETCH_DATA)

main_handler = ConversationHandler(
    entry_points=[
        MessageHandler(filters.Regex(f"^{START_BUTTON}$"), start_handler)
    ],
    states={
        STATES['start']: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, start_handler),
        ],
        STATES['get_info']: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, get_info_handler),
        ],
        STATES['start_exam']: [
            MessageHandler(filters.Regex(f"^{START_EXAM_BUTTON}$"), start_exam_handler),
            CallbackQueryHandler(handle_callback),  # Optional here
        ],
    },
    fallbacks=[
        MessageHandler(filters.Regex(f"^{START_BUTTON}$"), start_handler),
    ],
)