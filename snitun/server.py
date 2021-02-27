import asyncio
import os
import logging
import sys
import json

from datetime import datetime, timedelta

from unittest.mock import patch
from snitun.exceptions import SniTunInvalidPeer
from snitun.server.peer import Peer
from snitun.server.peer_manager import PeerManager
from cryptography.fernet import Fernet, MultiFernet

from aiohttp import web

from snitun.server.listener_sni import SNIProxy

log_file = str(datetime.utcnow().strftime('%m_%d_%Y')) + '.log'
logging.basicConfig(filename=log_file, format='%(levelname)s | %(asctime)s | %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', level=logging.DEBUG)
_LOGGER = logging.getLogger(__name__)

from snitun.server.run import SniTunServer, SniTunServerSingle

FERNET_TOKENS = [
    "XIKL24X0Fu83UmPLmWkXOBvvqsLq41tz2LljwafDyZw=",
    "ep1FyYA6epwbFxrtEJ2dii5BGvTx5-xU1oUCrF61qMA=",
    "POI93oiBlBWkerhMN9oLoURZdqbqC7ItIwsuo6GepOA=",
    "IeG7_fUGD5uWwl971hZsc0QKiWuxuWJl2KljaVKLM0o=",
    "NYdjm7cgRzR6hHkn7M48t2TzjDV-H23Y4_z07GiZMxw=",
    "7MGjNQCs4Uc6z_xWZj2w1w-OTaKwB2pdZaiz93FCjvA="
]

async def initialize_server():
    server = SniTunServerSingle(
        FERNET_TOKENS,host='0.0.0.0', port=443,throttling=500
        )
    await server.start()
    while True:
        await asyncio.sleep(0.1)
async def main():
    await initialize_server()

loop = asyncio.get_event_loop()
result = loop.run_until_complete(main())