from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)
from common import (
    WELCOME_MESSAGE,
    INFO_QUESTIONS,
    START_BUTTON,
    START_EXAM_BUTTON
)

from users_data import (
    clear_user_data,
    get_user_data,
    save_user_data
)
# States
STATES = {
    'get_info': 0,
    'start_exam': 1,
}


# /start
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.effective_user.username
    clear_user_data(username)  # Reset progress

    await update.message.reply_text(
        WELCOME_MESSAGE,
        reply_markup=ReplyKeyboardRemove()
    )

    # Immediately move to first question
    user_data = {'step': 0, 'answers': {}}
    save_user_data(username, user_data)

    _, first_question = INFO_QUESTIONS[0]
    keyboard = ReplyKeyboardMarkup([[START_BUTTON]], resize_keyboard=True, one_time_keyboard=False)
    await update.message.reply_text(first_question, reply_markup=keyboard)
    return STATES['get_info']


# Info collection
async def get_info_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.effective_user.username
    user_data = get_user_data(username)

    step = user_data['step']
    key, _ = INFO_QUESTIONS[step]
    user_data['answers'][key] = update.message.text

    step += 1
    if step < len(INFO_QUESTIONS):
        user_data['step'] = step
        save_user_data(username, user_data)

        _, next_question = INFO_QUESTIONS[step]
        keyboard = ReplyKeyboardMarkup([[START_BUTTON]], resize_keyboard=True)
        await update.message.reply_text(next_question, reply_markup=keyboard)
        return STATES['get_info']
    else:
        phone = user_data['answers'].get('phone', 'N/A')
        suggester = user_data['answers'].get('suggester', 'N/A')
        await update.message.reply_text(
            f"""
            ✅ ممنونم دوست عزیز
            📞 شماره همراه ثبت شده:
            {phone} 
            💡معرف:
            {suggester}
            """,
            reply_markup=ReplyKeyboardMarkup([[START_EXAM_BUTTON, START_BUTTON]], one_time_keyboard=True)
        )
        return STATES['start_exam']


# Exam start
async def start_exam_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.effective_user.username
    clear_user_data(username)
    await update.message.reply_text("📝 Starting your exams...")
    return ConversationHandler.END

main_handler = ConversationHandler(
    entry_points=[
        MessageHandler(filters.Regex(f"^{START_BUTTON}$"), start_handler)
    ],
    states={
        STATES['get_info']: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, get_info_handler),
            MessageHandler(filters.Regex(f"^{START_BUTTON}$"), start_handler),
        ],
        STATES['start_exam']: [
            MessageHandler(filters.Regex(f"^{START_EXAM_BUTTON}$"), start_exam_handler),
            MessageHandler(filters.Regex(f"^{START_BUTTON}$"), start_handler),
        ],
    },
    fallbacks=[
        MessageHandler(filters.Regex(f"^{START_BUTTON}$"), start_handler),
    ],
)