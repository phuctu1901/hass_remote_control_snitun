import asyncio
import os
from datetime import datetime, timedelta


import logging
import sys
import http
log_file = str(datetime.utcnow().strftime('%m_%d_%Y')) + '.log'
logging.basicConfig(filename=log_file, format='%(levelname)s | %(asctime)s | %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', level=logging.DEBUG)

_LOGGER = logging.getLogger(__name__)


import json
import time
import random

from unittest.mock import patch
from snitun.exceptions import SniTunInvalidPeer
from snitun.server.peer import Peer
from snitun.server.peer_manager import PeerManager
from cryptography.fernet import Fernet, MultiFernet
from jose import jwk, jwt
from jose.utils import base64url_decode
import string
from aiohttp import web
from dotenv import load_dotenv

load_dotenv()

FERNET_TOKENS = [
    "XIKL24X0Fu83UmPLmWkXOBvvqsLq41tz2LljwafDyZw=",
    "ep1FyYA6epwbFxrtEJ2dii5BGvTx5-xU1oUCrF61qMA=",
    "POI93oiBlBWkerhMN9oLoURZdqbqC7ItIwsuo6GepOA=",
    "IeG7_fUGD5uWwl971hZsc0QKiWuxuWJl2KljaVKLM0o=",
    "NYdjm7cgRzR6hHkn7M48t2TzjDV-H23Y4_z07GiZMxw=",
    "7MGjNQCs4Uc6z_xWZj2w1w-OTaKwB2pdZaiz93FCjvA="
]

app_client_id = os.getenv('APP_CLIENT_ID')
cloudflare_api_token = os.getenv('CLOUDFLARE_API_TOKEN')
cloudflare_zone = os.getenv('CLOUDFLARE_ZONE')
hass_basedomain=os.getenv('HASSCLOUD_BASEDOMAIN')
snitun_server=os.getenv('SNITUN_SERVER')
 
cloudflare_request_header = {
'Content-Type': 'application/json',
'Authorization': f'Bearer {cloudflare_api_token}'
}



with open("jwks.json") as f:
  response = f.read()

keys = json.loads(response)['keys']
def lambda_handler(token):
    try:
        # get the kid from the headers prior to verification
        headers = jwt.get_unverified_headers(token)
        kid = headers['kid']
        # search for the kid in the downloaded public keys
        key_index = -1
        for i in range(len(keys)):
            if kid == keys[i]['kid']:
                key_index = i
                break
        if key_index == -1:
            return False
        # construct the public key
        public_key = jwk.construct(keys[key_index])
        # get the last two sections of the token,
        # message and signature (encoded in base64)
        message, encoded_signature = str(token).rsplit('.', 1)
        # decode the signature
        decoded_signature = base64url_decode(encoded_signature.encode('utf-8'))
        # verify the signature
        if not public_key.verify(message.encode("utf8"), decoded_signature):
            return False
        # since we passed the verification, we can now safely
        # use the unverified claims
        claims = jwt.get_unverified_claims(token)
        # additionally we can verify the token expiration
        if time.time() > claims['exp']:
            return False
        # and the Audience  (use claims['client_id'] if verifying an access token)
        if claims['aud'] != app_client_id:
            return False
        # now we can use the claims
        return claims
    except:
        return False
     


manager = PeerManager(FERNET_TOKENS, throttling=500)
def create_peer_config(
    valid: int, hostname: str, aes_key: bytes, aes_iv: bytes
) -> bytes:
    """Create a fernet token."""
    fernet = MultiFernet([Fernet(key) for key in FERNET_TOKENS])

    return fernet.encrypt(
        json.dumps(
            {
                "valid": valid,
                "hostname": hostname,
                "aes_key": aes_key,
                "aes_iv": aes_iv,
            }
        ).encode()
    )

async def challenge_txt(request):
    try:
        token =   request.headers.get('Authorization', None)
        resp = lambda_handler(token)

    except:
        return web.json_response(status=401)

    if resp == False:

        data_err = {
                "message": "The incoming token has expired"
            }

        data_err = json.dumps(data_err)
        return web.json_response(status=401, body=data_err)
    
    domain = get_and_create_domain(resp["email"])
    request = await request.json()

    value = request["txt"]
    conn = http.client.HTTPSConnection("api.cloudflare.com")
    payload = {
        "type": "TXT",
        "name": f"_acme-challenge.{domain}",
        "content": f"{value}",
        "ttl": 60,
        "priority": 100,
        "proxied": False
    }
    payload = json.dumps(payload)
    try:
        conn.request("POST", f"/client/v4/zones/{cloudflare_zone}/dns_records", payload, cloudflare_request_header)
        res = conn.getresponse()
        data = res.read()
        data_2 = data.decode("utf-8")
        if (res.status == 200):
            s = json.loads(data_2)
            result = s['result']
            id = result['id']
        return web.Response(status=res.status, body=data)
    except:
        return web.json_response(status=500)
    

async def snitun_token(request):
    """Init a new peer."""
    try:
        token =   request.headers.get('Authorization', None)
        resp = lambda_handler(token)

    except:
        return web.json_response(status=401)

    valid = datetime.utcnow() + timedelta(days=1)
    request = await request.json()

    aes_key = request["aes_key"]
    aes_iv = request["aes_iv"]

    throttling= 500


    if resp == False:

        data_err = {
                "message": "The incoming token has expired"
            }

        data_err = json.dumps(data_err)
        return web.json_response(status=401, body=data_err)
    
    hostname = get_and_create_domain(resp["email"])
    try:
        fernet_token = create_peer_config(valid.timestamp(), hostname, aes_key, aes_iv)
        peer = manager.create_peer(fernet_token)
        manager.add_peer(peer)
        cursor.execute("INSERT INTO peers (hostname,valid, aes_key, aes_iv, throttling) VALUES (?, ?, ?,?,?)", (hostname, valid, aes_key, aes_iv, throttling))
        connection.commit()
        response_obj = {'status':200, 'token': fernet_token.decode(), 'valid':valid.timestamp(), 'throttling':throttling}
        return web.json_response(response_obj, status=200)
    except:
        return web.json_response(status=500)

import sqlite3

connection = sqlite3.connect("server.db")

cursor = connection.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS peers (hostname TEXT, valid datetime, aes_key bytes, aes_iv bytes, throttling integer)")
cursor.execute("CREATE TABLE IF NOT EXISTS users (domain TEXT, email text)")


# curl -X GET "https://api.cloudflare.com/client/v4/zones/cd7d0123e3012345da9420df9514dad0" \
#      -H "Content-Type:application/json" \
#      -H "Authorization: Bearer YQSn-xWAQiiEh9qM58wZNnyQS7FUdoqGIUAbrh7T"


async def get_dns(request):

    conn = http.client.HTTPSConnection("api.cloudflare.com")
    

    conn.request("GET", f"/client/v4/zones/{cloudflare_zone}/dns_records/",headers = cloudflare_request_header)
    res = conn.getresponse()
    data = res.read()
    return web.Response(status=res.status, body=data)

async def challenge_cleanup(request):
    try:
        token =   request.headers.get('Authorization', None)
        resp = lambda_handler(token)

    except:
        return web.json_response(status=401)

    if resp == False:

        data_err = {
                "message": "The incoming token has expired"
            }

        data_err = json.dumps(data_err)
        return web.json_response(status=401, body=data_err)
    
    domain = get_and_create_domain(resp["email"])
         
    conn = http.client.HTTPSConnection("api.cloudflare.com")
    

    conn.request("GET", f"/client/v4/zones/{cloudflare_zone}/dns_records/?type=TXT&name=_acme-challenge.{domain}",headers = cloudflare_request_header)
    res = conn.getresponse()
    data = res.read()

    data = json.loads(data)
    result = data['result']
    count = 0 
    for key in result:
        if key['name'] == f"_acme-challenge.{domain}":
            count += 1
            conn2 = http.client.HTTPSConnection("api.cloudflare.com")
            id = key['id']
        

            conn2.request(f"DELETE", f"/client/v4/zones/{cloudflare_zone}/dns_records/{id}",headers = cloudflare_request_header)
            res = conn2.getresponse()
            data = res.read()

    return web.json_response(status=200)

def id_generator(size=32, chars=string.ascii_lowercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))

def get_and_create_domain(email):
    
    sql_string = f"SELECT domain FROM users where email = '{email}'"

    cursor.execute(sql_string)

    rows = cursor.fetchone()
    
    if (rows):
        return rows[0]
    else:
        domain = id_generator()+f".{hass_basedomain}"
        cursor.execute("INSERT INTO users (domain,email) VALUES (?, ?)", (domain, email))
        connection.commit()
        return domain;



async def register_instance(request):

    try:
        token =   request.headers.get('Authorization', None)
        resp = lambda_handler(token)

    except:
        return web.json_response(status=401)

    if resp == False:

        data_err = {
                "message": "The incoming token has expired"
            }

        data_err = json.dumps(data_err)
        return web.json_response(status=401, body=data_err)
    else:
        domain = get_and_create_domain(resp["email"])
         
        data = {
            "status": 200,
            "domain": domain,
            "email": resp["email"],
            "server": snitun_server
            }
        data = json.dumps(data)
        return web.json_response(status=200, body=data)

async def subscription_info(request):
    data ={
        "status": 200,
        "provider": "true",
        "billing_plan_type": "trial",
        "plan_renewal_date": 1610323200,
        "renewal_active": "false",
        "human_description": "Premium member. Thanks your support.",
        "delete_requested": "false",
        "customer_exists": "false",
        "source": "null",
        "subscription": {
            "status": "trialing",
            "current_period_end": 1610323200,
            "trial_end": 1610323200,
            "cancel_at_period_end": "false",
            "canceled_at": 1607666340
        }
    }

    data = json.dumps(data)

    return web.json_response(status=200, body=data)

app = web.Application()
app.router.add_route('post','/snitun_token', snitun_token)
app.router.add_route('post', '/challenge_txt', challenge_txt)
app.router.add_route('post', '/challenge_cleanup', challenge_cleanup)
app.router.add_route('get', '/get_dns', get_dns)
app.router.add_route('get','/payments/subscription_info', subscription_info)

app.router.add_route('post','/register_instance', register_instance)

web.run_app(app, port=8085)




