# hubspot.py

from fastapi import Request, HTTPException
from fastapi.responses import HTMLResponse
import secrets
import os
import base64
import urllib
import json
import httpx
import asyncio
from redis_client import add_key_value_redis, get_value_redis, delete_key_redis

CLIENT_ID = os.getenv("HUBSPOT_CLIENTID")
SECRET_ID = os.getenv("HUBSPOT_SECRETID")

encoded_client_id_secret = base64.b64encode(f'{CLIENT_ID}:{SECRET_ID}'.encode()).decode()
REDIRECT_URI = 'http://localhost:8000/integrations/hubspot/oauth2callback'
encoded_redirect_uri = urllib.parse.quote(REDIRECT_URI)
authorization_url = f'https://app.hubspot.com/oauth/authorize?client_id={CLIENT_ID}&response_type=code&owner=user&redirect_uri={encoded_redirect_uri}'
scopes = urllib.parse.quote("oauth crm.objects.contacts.read")


async def authorize_hubspot(user_id, org_id):
    state_data = {
        'state': secrets.urlsafe(32),
        'user_id': user_id,
        'org_id': org_id
    }

    encoded_state = json.dumps(state_data)
    await add_key_value_redis(f'hubspot_state:{org_id}:{user_id}', encoded_state, expire=600)

    return f'{authorization_url}&scope={scopes}&state={encoded_state}'

async def oauth2callback_hubspot(request: Request):
    if request.query_params.get('error'):
        raise HTTPException(status_code=400, detail=request.path_params.get("error"))
    code = request.query_params.get('code')
    encoded_state = request.query_params.get('state')
    state_data = json.loads(encoded_state)

    original_state = state_data.get('state')
    user_id = state_data.get('user_id')
    org_id = state_data.get('org_id')

    saved_state = await get_value_redis(f'hubspot_state:{org_id}:{user_id}')

    if not saved_state or original_state != json.loads(saved_state).get('state'):
        raise HTTPException(status_code=400, detail='State does not match.')
    
    async with httpx.AsyncClient() as client:
        response, _ = await asyncio.gather(
            client.post(
                'https://api.hubapi.com/oauth/v1/token',
                data={
                    'grant_type': 'authorization_code',
                    'code': code,
                    'redirecr_uri': REDIRECT_URI
                },
                headers={
                    'Authorization': f'Basic {encoded_client_id_secret}',
                    'Content-Type': 'application/json',
                },
            ),
            delete_key_redis(f'hubspot_state:{org_id}:{user_id}'),
        )

    await add_key_value_redis(f'hubspot_credentials:{org_id}:{user_id}', json.dumps(response.json()), expire=600)

    close_window_script = """
    <html>
        <script>
            window.close();
        </script>
    </html>
    """
    return HTMLResponse(content=close_window_script)

async def get_hubspot_credentials(user_id, org_id):
    credentials = await get_value_redis(f'hubspot_credentials:{org_id}:{user_id}')
    if not credentials:
        raise HTTPException(status_code=400, detail='No credentials found.')
    credentials = json.loads(credentials)
    if not credentials:
        raise HTTPException(status_code=400, detail='No credentials found.')
    await delete_key_redis(f'hubspot_credentials:{org_id}:{user_id}')

    return credentials

async def create_integration_item_metadata_object(response_json):
    # TODO
    pass

async def get_items_hubspot(credentials):
    # TODO
    pass