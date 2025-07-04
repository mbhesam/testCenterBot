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
from telegram_bot_calendar import DetailedTelegramCalendar, LSTEP
from datetime import datetime, date
from common import (
    WELCOME_MESSAGE,
    FAILED_CODE_MELLI,
    INFO_QUESTIONS,
    START_BUTTON,
    START_EXAM_BUTTON,
    NOT_COMPELETED_INFO,
    ALREADY_SUBMITTED,
    PREPARING_QUESTIONS,
    FAILED_FETCH_DATA,
    END_EXAM_WITHOUT_OFF,
    END_EXAM_TIME,
    FULL_INFO_QUESTIONS,
    GET_STATIC_INFO_BUTTON, CALLENDER_FAILED, COUNTRY_FAILED, STATE_FAILED, CITY_FAILED, COMPLETE_INFO,
    SHARE_SUGGESTION, share_bot_template, CHECK_SHARE_COUNT, NOT_ENOUGH_SHARE_COUNT, ENOUGH_SHARE_COUNT,
    CONFIRM_STATIC_INFO
)
from utils import (
    fetch_questions,
    check_grade,
    is_integer,
    load_countries,
    load_states_by_country_code,
    load_cities_by_state_and_country,
    approve_off_code, approve_off_code_sync
)
from users_data import (
    clear_user_data,
    get_user_data,
    save_user_data,
    get_exam_data,
    save_exam_data,
    clear_exam_data, clear_share_count
)
from config import EXAM_DURATION_SECONDS
import json
import time
import math

# States
STATES = {
    'start': 0,
    'get_info': 1,
    'get_static_info': 2,
    'awaiting_birthday': 3,
    'country_selection': 4,
    'state_selection': 5,
    'city_selection': 6,
    'start_exam': 7,
}

# /start
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.effective_user.username
    user_data = get_user_data(username=username)
    await update.message.reply_text(WELCOME_MESSAGE)
    print(user_data.get('status'))
    if user_data.get('status') == 'ready_exam':
        await update.message.reply_text(ALREADY_SUBMITTED,
                     reply_markup=ReplyKeyboardMarkup([[START_EXAM_BUTTON, GET_STATIC_INFO_BUTTON], [CHECK_SHARE_COUNT, START_BUTTON]], resize_keyboard=True, one_time_keyboard=True))
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
        # 🎯 Update share_off_count for the suggester
        suggester_username = user_data['info']['suggester']
        suggester_data = get_user_data(username=suggester_username)
        suggester_data['share_off_count'] = suggester_data.get('share_off_count', 0) + 1
        save_user_data(username=suggester_username, data=suggester_data)
        await update.message.reply_text(
            f"""
    ✅ ممنونم دوست عزیز
    📞 شماره همراه ثبت شده:
    {user_data['info']['phone']} 
    💡 معرف:
    {user_data['info']['suggester']}
                """,
            reply_markup=ReplyKeyboardMarkup([[START_EXAM_BUTTON, GET_STATIC_INFO_BUTTON, START_BUTTON]], one_time_keyboard=True,
                                             resize_keyboard=True)
        )
        return STATES['start_exam']

async def check_share_count_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.effective_user.username
    user_data = get_user_data(username=username)
    if user_data['share_off_count'] >= 3:
        await update.message.reply_text(
            f" تعداد افرادی که شما رو به عنوان معرف مشخص کردند: {user_data['share_off_count']}")
        await update.message.reply_text(ENOUGH_SHARE_COUNT)
        off_code = await approve_off_code(grade='S', phone_number=user_data['info']['phone'])
        await update.message.reply_text(off_code)
        clear_share_count(username=username)
        return STATES['start_exam']
    await update.message.reply_text(f" تعداد افرادی که شما رو به عنوان معرف مشخص کردند: {user_data['share_off_count']}")
    await update.message.reply_text(NOT_ENOUGH_SHARE_COUNT)
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
    keyboard.append([InlineKeyboardButton(text="📨 اشتراک‌گذاری سوال", callback_data=f"share|{username}")])

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
            user_data['test_off_count'] += 1
            clear_exam_data(username=username)
            save_user_data(username=username, data=user_data)
            if user_data['test_off_count'] >= 4:
                await update.callback_query.message.reply_text(END_EXAM_WITHOUT_OFF)
                return STATES['start']
            off_code = await approve_off_code(grade=exam_grade, phone_number=user_data['info']['phone'])
            print(off_code)
            return STATES['start_exam']
        await update.message.reply_text(SHARE_SUGGESTION)
        await update.message.reply_text(share_bot_template(username))
        return STATES['start_exam']
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

    elif action == 'share':
        index = exam_data['current_question']
        question_data = exam_data['data'][index]
        question_text = question_data['question']
        options = json.loads(question_data['options'])

        text = f"❓ {question_text}\n\n" + "\n".join([f"{i + 1}. {opt}" for i, opt in enumerate(options)])
        text += "\n\n📝 پاسخ خود را در ربات وارد کنید."

        await update.callback_query.message.reply_text(text)

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
                    user_data['test_off_count'] += 1
                    clear_exam_data(username=username)
                    save_user_data(username=username, data=user_data)
                    if user_data['test_off_count'] >= 10:
                        await update.callback_query.message.reply_text(END_EXAM_WITHOUT_OFF)
                        print("not get off code")
                        return STATES['start']
                    off_code = await approve_off_code(grade=exam_grade, phone_number=user_data['info']['phone'])
                    print(off_code)
                    return STATES['start_exam']
                await update.message.reply_text(SHARE_SUGGESTION)
                await update.message.reply_text(share_bot_template(username))
                return STATES['start_exam']
        except Exception as e:
            print(f"Error handling submit: {e}")
            await query.answer(FAILED_FETCH_DATA)


async def get_static_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.effective_user.username
    user_data = get_user_data(username=username)
    # Initialize progress tracking if not exists
    print('question_index' not in context.user_data)
    if 'question_index' not in context.user_data:
        print('no question index')
        context.user_data['question_index'] = 0
        full_questions = FULL_INFO_QUESTIONS.split("\n")
        context.user_data['full_questions'] = full_questions
        await update.message.reply_text(full_questions[0])
        return STATES['get_static_info']

    # Process the answer
    question_index = context.user_data['question_index']
    full_questions = context.user_data['full_questions']

    # Store answer based on current question
    if question_index == 0:
        user_data['info']['first_name'] = update.message.text
    elif question_index == 1:
        user_data['info']['last_name'] = update.message.text
    elif question_index == 2:
        user_data['info']['code_melli'] = update.message.text
        if not is_integer(user_data['info']['code_melli']):
            await update.message.reply_text(FAILED_CODE_MELLI)
            context.user_data['question_index'] = 1
    elif question_index == 3:
        user_data['info']['email'] = update.message.text

    # Move to next question or finish
    context.user_data['question_index'] += 1

    if context.user_data['question_index'] < len(full_questions) - 4:
        await update.message.reply_text(full_questions[context.user_data['question_index']])
        return STATES['get_static_info']
    else:
        return await birth_selection(update, context)


async def birth_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Initialize calendar with consistent settings
    calendar = DetailedTelegramCalendar(
        calendar_id=1,
        min_date=date(1930, 1, 1),
        max_date=date.today()
    )
    markup, step = calendar.build()
    q4 = FULL_INFO_QUESTIONS.split("\n")[4]
    await update.message.reply_text(
        f'{q4} {LSTEP[step]}:',
        reply_markup=markup
    )
    return STATES['awaiting_birthday']


async def handle_calendar_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    username = query.from_user.username
    user_data = get_user_data(username=username)

    if not user_data:
        await query.edit_message_text(FAILED_FETCH_DATA)
        return STATES['start_exam']

    try:
        calendar = DetailedTelegramCalendar(calendar_id=1)
        date, key, step = calendar.process(query.data)
        if not date:
            # Rebuild calendar for next step
            new_markup, new_step = calendar.build()
            await query.edit_message_text(
                f"Select {LSTEP[new_step]}:",
                reply_markup=new_markup
            )
            return STATES['awaiting_birthday']
        # Date selected successfully
        formatted_date = date.strftime("%Y-%m-%d")
        user_data['info']['birth_date'] = formatted_date
        save_user_data(username=username, data=user_data)

        await query.edit_message_text(
            f" 👏 اطلاعات تاریخ تولد شما ثبت شد:\n {formatted_date}\n"
        )
        return await country_selection(update, context)

    except Exception as e:
        print(f"Calendar error: {str(e)}")
        await query.edit_message_text(
            CALLENDER_FAILED
        )
        return STATES['awaiting_birthday']


async def country_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    countries = load_countries()

    keyboard = []
    row = []
    for idx, country in enumerate(countries):
        button = InlineKeyboardButton(country['name'], callback_data=f"country_{country['iso2']}")
        row.append(button)
        if len(row) == 3:  # 3 buttons per row
            keyboard.append(row)
            row = []
    if row:  # Append remaining buttons
        keyboard.append(row)
    q5 = FULL_INFO_QUESTIONS.split("\n")[5]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        await update.message.reply_text(f"{q5}", reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.message.reply_text(f"{q5}", reply_markup=reply_markup)
    return STATES["country_selection"]

async def handle_country_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    username = query.from_user.username
    user_data = get_user_data(username=username)
    iso2 = query.data.split("_")[1]
    countries = load_countries()
    country = next((c for c in countries if c['iso2'] == iso2), None)
    if country:
        await query.edit_message_text(f" انتخاب شما کشور: {country['name']} {country['emoji']}")
        # You can also store it in user_data or DB
        context.user_data['country'] = country
        user_data['info']['country'] = country['name']
        save_user_data(username=username, data=user_data)
        return await state_selection(update, context)
    else:
        await query.edit_message_text(COUNTRY_FAILED)
        return STATES['start_exam']


async def state_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    country = context.user_data.get('country')
    if not country:
        await update.message.reply_text(COUNTRY_FAILED)
        return

    iso2_code = country['iso2']
    states = load_states_by_country_code(iso2_code)

    if not states:
        await update.message.reply_text(STATE_FAILED)
        return

    keyboard = []
    row = []
    for idx, state in enumerate(states):
        button = InlineKeyboardButton(state['name'], callback_data=f"state_{state['state_code']}")
        row.append(button)
        if len(row) == 3:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    reply_markup = InlineKeyboardMarkup(keyboard)
    q6 = FULL_INFO_QUESTIONS.split("\n")[6]
    if update.message:
        await update.message.reply_text(f"{q6}", reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.message.reply_text(f"{q6}", reply_markup=reply_markup)
    return STATES['state_selection']

async def handle_state_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    username = query.from_user.username
    user_data = get_user_data(username=username)
    state_code = query.data.split("_")[1]
    selected_country = context.user_data.get('country')
    if not selected_country:
        await query.edit_message_text(STATE_FAILED)
        return

    states = load_states_by_country_code(selected_country['iso2'])
    state = next((s for s in states if s['state_code'] == state_code), None)

    if state:
        context.user_data['state'] = state
        await query.edit_message_text(f" انتخاب استان: {state['name']}")
        time.sleep(3)
        user_data['info']['state'] = state['name']
        await query.edit_message_text(CONFIRM_STATIC_INFO)
        time.sleep(3)
        if user_data['info_complete']:
            save_user_data(username=username, data=user_data)
            return STATES['start_exam']
        off_code = approve_off_code_sync(grade='S', phone_number=user_data['info']['phone'])
        print(off_code)
        await query.edit_message_text(off_code)
        user_data['info_complete'] = True
        save_user_data(username=username, data=user_data)
        return STATES['start_exam']
    else:
        await query.edit_message_text(STATE_FAILED)
        return STATES['start_exam']

# async def city_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     state = context.user_data.get('state')
#     country = context.user_data.get('country')
#     if not state or not country:
#         await update.callback_query.message.reply_text(CITY_FAILED)
#         return STATES['start_exam']
#
#     state_code = state['state_code']
#     country_code = country['iso2']
#
#     cities = load_cities_by_state_and_country(state_code, country_code)
#
#     if not cities:
#         await update.callback_query.message.reply_text(CITY_FAILED)
#         return STATES['start_exam']
#
#     keyboard = []
#     row = []
#     for idx, city in enumerate(cities):
#         button = InlineKeyboardButton(city['name'], callback_data=f"city_{city['id']}")
#         row.append(button)
#         if len(row) == 3:
#             keyboard.append(row)
#             row = []
#     if row:
#         keyboard.append(row)
#
#     reply_markup = InlineKeyboardMarkup(keyboard)
#
#     await update.callback_query.message.reply_text(
#         f"شهر خود را در استان {state['name']} انتخاب کنید:",
#         reply_markup=reply_markup
#     )
#     return STATES['city_selection']
#
# async def handle_city_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     query = update.callback_query
#     await query.answer()
#     city_id = int(query.data.split("_")[1])
#     state = context.user_data.get('state')
#     country = context.user_data.get('country')
#     username = query.from_user.username
#     user_data = get_user_data(username=username)
#
#     cities = load_cities_by_state_and_country(state['state_code'], country['iso2'])
#     city = next((c for c in cities if c['id'] == city_id), None)
#
#     if city:
#         context.user_data['city'] = city
#         user_data['info']['city'] = city['name']
#         save_user_data(username=username, data=user_data)
#         await query.edit_message_text(f" انتخاب شهر: {city['name']}")
#         await update.message.reply_text(COMPLETE_INFO)
#         return STATES['start_exam']
#     else:
#         await query.edit_message_text(CITY_FAILED)
#         return STATES['start_exam']

main_handler = ConversationHandler(
    entry_points=[
        MessageHandler(filters.Regex(f"^(/start|{START_BUTTON})$"), start_handler),
    ],
    states={
        STATES['start']: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, start_handler),
        ],
        STATES['get_info']: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, get_info_handler),
        ],
        STATES['get_static_info']: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, get_static_info),  # Removed parentheses
        ],
        STATES['awaiting_birthday']: [
            MessageHandler(filters.Regex(f"^(/get_static_info|{GET_STATIC_INFO_BUTTON})$"), get_static_info),
            MessageHandler(filters.Regex(f"^(/start_exam|{START_EXAM_BUTTON})$"), start_exam_handler),
            CallbackQueryHandler(handle_calendar_callback)
        ],
        STATES['country_selection']: [
            MessageHandler(filters.Regex(f"^(/get_static_info|{GET_STATIC_INFO_BUTTON})$"), get_static_info),
            MessageHandler(filters.Regex(f"^(/start_exam|{START_EXAM_BUTTON})$"), start_exam_handler),
            CallbackQueryHandler(handle_country_choice, pattern=r"^country_"),
        ],
        STATES['state_selection']: [
            MessageHandler(filters.Regex(f"^(/get_static_info|{GET_STATIC_INFO_BUTTON})$"), get_static_info),
            MessageHandler(filters.Regex(f"^(/start_exam|{START_EXAM_BUTTON})$"), start_exam_handler),
            CallbackQueryHandler(handle_state_choice, pattern=r"^state_"),
        ],
        # STATES['city_selection']: [
        #     MessageHandler(filters.Regex(f"^{GET_STATIC_INFO_BUTTON}$"), get_static_info),
        #     MessageHandler(filters.Regex(f"^{START_EXAM_BUTTON}$"), start_exam_handler),
        #     CallbackQueryHandler(handle_city_choice, pattern=r"^city_"),
        #],
        STATES['start_exam']: [
            MessageHandler(filters.Regex(f"^(/check_share_count|{CHECK_SHARE_COUNT})$"), check_share_count_handler),
            MessageHandler(filters.Regex(f"^(/get_static_info|{GET_STATIC_INFO_BUTTON})$"), get_static_info),
            MessageHandler(filters.Regex(f"^(/start_exam|{START_EXAM_BUTTON})$"), start_exam_handler),
            # MessageHandler(filters.Regex(f"^(/check_share_count|{CHECK_SHARE_COUNT})$"), check_share_count_handler),
            CallbackQueryHandler(handle_callback),  # Optional here
        ],
    },
    fallbacks=[
        MessageHandler(filters.Regex(f"^(/start|{START_BUTTON})$"), start_handler),
    ],
)