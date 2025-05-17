from telegram.ext import ApplicationBuilder, PicklePersistence
from config import BOT_TOKEN, PROXY_URL, PROXY_REQUEST_TIME_OUT
if __name__ == "__main__":
    persistence = PicklePersistence(filepath='conversations/conversations')
    application = ApplicationBuilder().token(
        BOT_TOKEN
    ).get_updates_proxy_url(
        PROXY_URL
    ).proxy_url(
        PROXY_URL
    ).persistence(persistence).build()
    application.add_handler(main_handler)
    application.run_polling(
        timeout=PROXY_REQUEST_TIME_OUT,
        pool_timeout=PROXY_REQUEST_TIME_OUT,
        read_timeout=PROXY_REQUEST_TIME_OUT,
        write_timeout=PROXY_REQUEST_TIME_OUT,
        connect_timeout=PROXY_REQUEST_TIME_OUT,
    )
