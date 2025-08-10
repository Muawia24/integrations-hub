import os
import json
import base64
import secrets
import urllib.parse
from typing import List

from fastapi import Request, HTTPException
from fastapi.responses import HTMLResponse
import httpx
import asyncio

from integrations.integration_item import IntegrationItem
from redis_client import add_key_value_redis, get_value_redis, delete_key_redis

CLIENT_ID = os.getenv("HUBSPOT_CLIENTID")
SECRET_ID = os.getenv("HUBSPOT_SECRETID")
REDIRECT_URI = 'http://localhost:8000/integrations/hubspot/oauth2callback'

SCOPES = "oauth crm.objects.contacts.read"
ENCODED_SCOPES = urllib.parse.quote(SCOPES)
ENCODED_REDIRECT_URI = urllib.parse.quote(REDIRECT_URI)

AUTHORIZATION_URL = (
    f"https://app.hubspot.com/oauth/authorize"
    f"?client_id={CLIENT_ID}&response_type=code&owner=user"
    f"&redirect_uri={ENCODED_REDIRECT_URI}&scope={ENCODED_SCOPES}"
)

TOKEN_URL = "https://api.hubapi.com/oauth/v1/token"
CONTACTS_URL = "https://api.hubapi.com/crm/v3/objects/contacts"

encoded_client_id_secret = base64.b64encode(f'{CLIENT_ID}:{SECRET_ID}'.encode()).decode()


async def authorize_hubspot(user_id: str, org_id: str) -> str:
    """Generates the HubSpot OAuth2 authorization URL with a signed state."""
    state_data = {
        'state': secrets.token_urlsafe(32),
        'user_id': user_id,
        'org_id': org_id
    }

    state_json = json.dumps(state_data)
    encoded_state = urllib.parse.quote(state_json)

    redis_key = f'hubspot_state:{org_id}:{user_id}'
    await add_key_value_redis(redis_key, state_json, expire=600)

    return f'{AUTHORIZATION_URL}&state={encoded_state}'


async def oauth2callback_hubspot(request: Request) -> HTMLResponse:
    """Handles the OAuth2 callback and exchanges the code for tokens."""
    if request.query_params.get('error'):
        raise HTTPException(status_code=400, detail=request.path_params.get("error"))
    
    code = request.query_params.get('code')
    encoded_state = request.query_params.get('state')
    
    try:
        state_data = json.loads(encoded_state)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid state format.")

    original_state = state_data.get('state')
    user_id = state_data.get('user_id')
    org_id = state_data.get('org_id')

    redis_key = f'hubspot_state:{org_id}:{user_id}'
    saved_state = await get_value_redis(redis_key)

    if not saved_state or original_state != json.loads(saved_state).get('state'):
        raise HTTPException(status_code=400, detail='State does not match.')
    
    async with httpx.AsyncClient() as client:
        response, _ = await asyncio.gather(
            client.post(
                TOKEN_URL,
                data={
                    'grant_type': 'authorization_code',
                    'client_id': CLIENT_ID,
                    'client_secret': SECRET_ID,
                    'code': code,
                    'redirect_uri': REDIRECT_URI
                },
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            ),
            delete_key_redis(redis_key),
        )

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="Token exchange failed.")
    await add_key_value_redis(
        f'hubspot_credentials:{org_id}:{user_id}',
        json.dumps(response.json()),
        expire=600
    )

    close_window_script = """
    <html>
        <script>
            window.close();
        </script>
    </html>
    """
    return HTMLResponse(content=close_window_script)


async def get_hubspot_credentials(user_id: str, org_id: str) -> dict:
    """Retrieves and returns HubSpot credentials from Redis."""
    redis_key = f'hubspot_credentials:{org_id}:{user_id}'
    credentials = await get_value_redis(redis_key)

    if not credentials:
        raise HTTPException(status_code=400, detail='No credentials found.')
    
    try:
        credentials = json.loads(credentials)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail='Failed to decode stored credentials.')
    
    await delete_key_redis(redis_key)

    return credentials


def create_integration_item_metadata_object(response_json: str) -> IntegrationItem:
    """
    Converts a HubSpot contact JSON into an IntegrationItem.
    Matches fields seen in the UI: Name, Email, Job Title, Created, Modified.
    """
    properties = response_json.get("properties", {})
    contact_id = response_json.get("id")

    first_name = properties.get("firstname", "")
    last_name = properties.get("lastname", "")
    email = properties.get("email", "")

    full_name = f"{first_name} {last_name}".strip()
    
    created_at = response_json.get("createdAt")
    updated_at = response_json.get("updatedAt")
     
    integration_item_metadata = IntegrationItem(
        id=contact_id,
        type="hubspot_contact",
        name=full_name,
        email=email,
        creation_time=created_at,
        last_modified_time=updated_at,
        parent_id=None,
    )

    return integration_item_metadata


async def get_items_hubspot(credentials: dict) -> List[IntegrationItem] :
    """Fetches HubSpot contacts and converts them to IntegrationItems."""
    credentials = json.loads(credentials)
    access_token = credentials.get('access_token')
    if not access_token:
        raise HTTPException(status_code=401, detail="Missing access token")
    headers = {
        'Authorization': f"Bearer {access_token}",
        'Content-Type': 'application/json'
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(CONTACTS_URL, headers=headers)

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="Filed to fetch data")
    
    response_data = response.json()
    items = response_data.get('results', [])
    metadata_objects = []

    for item in items:
        metadata_obj = create_integration_item_metadata_object(item)
        metadata_objects.append(metadata_obj)

    return metadata_objects