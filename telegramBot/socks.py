from telegramBot.config import (
    PROXY_URL
)
import socks
import socket

# Parse proxy URL
from urllib.parse import urlparse
def connect_socks():
    proxy = urlparse(PROXY_URL)

    socks.set_default_proxy(
        socks.SOCKS5 if proxy.scheme == "socks5" else socks.SOCKS5,
        proxy.hostname,
        proxy.port,
        username=proxy.username,
        password=proxy.password
    )
    socket.socket = socks.socksocket