# Rebuild remote-control like Nabucasa cloud for Home Assistant base snitun protocol.


## Vietnamese tutorial: https://techcave.vn/bai-viet/xay-dung-tinh-nang-remote-control-cua-hass-dua-tren-ma-nguon-snitun-chinh-chu


**1. Requirement:**
- Cloudflare account
- Domain
- VPS: CentOS or Ubuntu
- AWS Cognito
- PC (or Raspberry Pi, etc) have Docker and Docker Compose (I'm using Docker-compose 1.28.5)

**2. Setup:**

Open file `.env` in `server/.env` and edit the following:
```dosini
CLOUDFLARE_API_TOKEN=<Cloudflare API Token>
CLOUDFLARE_ZONE=<Cloudflare Zone ID>
HASSCLOUD_BASEDOMAIN=<basedomain for remote control>
SNITUN_SERVER=<IP of SniTun Server>
APP_CLIENT_ID=<Cognito App Client ID without genereate secret key>
```

Example:
```dosini
CLOUDFLARE_API_TOKEN=NcXLmj33c2ZkvYdEtDCVdpSAcyXk28VUg5J42Fx2
CLOUDFLARE_ZONE=b91ff82ce2153ce27a91d976463ec83d
HASSCLOUD_BASEDOMAIN=ui.191lab.tech
SNITUN_SERVER=139.180.138.21
APP_CLIENT_ID=4k8pghmtvgo209ioc3d431f97s
```

Downnload and replace `jwks.json` file in `server/jwks.json` from url https://cognito-idp.us-east-1.amazonaws.com/pool_id/.well-known/jwks.json with pool_id parameter is your AWS Cognito Pool ID, ex: https://cognito-idp.us-east-1.amazonaws.com/us-east-1_n26MnE2AK/.well-known/jwks.json 

**3. Deploy:**

***3.1. Server deploy***

Clone this repo to your VPS and edit some variables to the instructions above. Your VPS must installed Python3 and allow port 80,443 and 8085. You can change to another ports.

```bash
cd <your-repo-directory>
pip3 install -r requirements.txt
```

```bash
cd snitun
python3 server.py
```

Open another terminal
```bash
cd server
python3 server.py
```

You should make this execute like service. You can refer this tutorial: https://tecadmin.net/setup-autorun-python-script-using-systemd/


***3.2. Docker deploy***

After researching the hass-nabucasa source code from repo https://github.com/NabuCasa/hass-nabucasa. We only edit some variables (cognito_client_id, user_pool_id, region, subscription_info_url, remote_api_url) in the `hass-nabucasa/hass_nabucasa/const.py` to point some service to your server.

Example:

```python3
SERVERS = {
    "production": {
        "cognito_client_id": "4k8pghmtvgo209ioc3d431f97s",
        "user_pool_id": "us-east-1_1SJ5opVZa",
        "region": "us-east-1",
        "relayer": "wss://cloud.nabucasa.com/websocket",
        "google_actions_report_state_url": "https://remotestate.nabucasa.com",
        "subscription_info_url": (
            "http://139.180.138.21:8085/payments/" "subscription_info"
        ),
        "cloudhook_create_url": "https://webhooks-api.nabucasa.com/generate",
        "remote_api_url": "http://139.180.138.21:8085",
        ...
    }
}

```

Because I'm using Docker to deploy Hass on my device, I will using mount function of Docker to replace original directory of `hass-nabucasa` package with your custom package. You can refer in `custom_hass` directory in my repo. 

## **Refer**:
[1] https://www.nabucasa.com/config/remote/

[2] https://github.com/NabuCasa/snitun

[3] https://github.com/NabuCasa/hass-nabucasa

## Thanks and I hope you only use this code to D.I.Y or research purpose.