# from telegram.ext import ApplicationBuilder
# from config import (
#     BOT_TOKEN,
#     PROXY_URL,
#     PROXY_REQUEST_TIME_OUT
# )
# from handlers import main_handler
# # Main
# def main():
#     application = ApplicationBuilder().token(
#         BOT_TOKEN
#     ).get_updates_proxy(
#         PROXY_URL
#     ).build()
#     application.add_handler(main_handler)
#     application.run_polling(
#         timeout=PROXY_REQUEST_TIME_OUT,
#     )
#
# if __name__ == '__main__':
#     main()
#
#
#
#
#

from telegram.ext import ApplicationBuilder
from telegram.request import HTTPXRequest
from config import (
    BOT_TOKEN,
    PROXY_URL,
    PROXY_REQUEST_TIME_OUT
)
from telegramBot.handlers import main_handler
from telegramBot.socks import connect_socks

def main():
    print("start")
    application = ApplicationBuilder() \
        .token(BOT_TOKEN) \
        .proxy(PROXY_URL) \
        .get_updates_proxy(PROXY_URL) \
        .pool_timeout(10) \
        .build()
    application.add_handler(main_handler)
    application.run_polling(timeout=10,poll_interval=1,drop_pending_updates=True)
    print("connected")

    # .connect_timeout(5) \
    # .get_updates_connect_timeout(5) \
if __name__ == '__main__':
    main()