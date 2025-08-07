from fastapi import Request, HTTPException
from fastapi.responses import HTMLResponse
import secrets
import os
import base64
import urllib
import json
import httpx
import asyncio
from typing import List
from integrations.integration_item import IntegrationItem
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
        'state': secrets.token_urlsafe(32),
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
                    'client_id': CLIENT_ID,
                    'client_secret': SECRET_ID,
                    'code': code,
                    'redirect_uri': REDIRECT_URI
                },
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
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
    try:
        credentials = json.loads(credentials)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail='Failed to decode stored credentials.')
    
    await delete_key_redis(f'hubspot_credentials:{org_id}:{user_id}')

    return credentials

async def create_integration_item_metadata_object(response_json: str) -> IntegrationItem:
    """
    Converts a HubSpot contact JSON into an IntegrationItem.
    Matches fields seen in the UI: Name, Email, Job Title, Created, Modified.
    """
    properties = response_json.get("properties", {})
    contact_id = response_json.get("id")

    first_name = properties.get("firstname", "")
    last_name = properties.get("lastname", "")

    full_name = f"{first_name} {last_name}".strip()
    created_at = response_json.get("createdAt")
    updated_at = response_json.get("updatedAt")
     
    integration_item_metadata = IntegrationItem(
        id=contact_id,
        type="hubspot_contact",
        name=full_name,
        creation_time=created_at,
        last_modified_time=updated_at,
        parent_id=None,
    )

    return integration_item_metadata

async def get_items_hubspot(credentials) -> List[IntegrationItem] :
    credentials = json.loads(credentials)
    access_token = credentials.get('access_token')
    if not access_token:
        raise HTTPException(status_code=401, detail="Missing access token")
    headers = {
        'Authorization': f"Bearer {access_token}",
        'Content-Type': 'application/json'
    }
    url = "https://api.hubapi.com/crm/v3/objects/contacts"

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="Filed to fetch data")
    response_data = response.json()
    items = response_data.get('results', [])
    metadata_objects = []
    for item in items:
        metadata_obj = await create_integration_item_metadata_object(item)
        metadata_objects.append(metadata_obj)

    return metadata_objects