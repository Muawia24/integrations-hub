# hubspot.py

from fastapi import Request
import secrets
import os
import base64
import urllib
import json
from redis_client import add_key_value_redis

CLIENT_ID = os.getenv("HUBSPOT_CLIENTID")
SECRET_ID = os.getenv("HUBSPOT_SECRETID")

encoded_client_secret_id = base64.b64decode(f'{CLIENT_ID}:{SECRET_ID}'.encode()).decode()
REDIRECT_URI = 'http://localhost:8000/integrations/hubspot/oauth2callback'
encoded_redirect_uri = urllib.parse.quote(REDIRECT_URI)
authorization_url = f'https://app.hubspot.com/oauth/authorize?client_id={CLIENT_ID}&response_type=code&owner=user&redirect_uri={encoded_redirect_uri}'
scopes = urllib.parse.quote("oauth crm.objects.contacts.read")


async def authorize_hubspot(user_id, org_id):
    state_data = {
        'state': None,
        'user_id': user_id,
        'org_id': org_id
    }

    encoded_state = json.dumps(state_data)
    await add_key_value_redis(f'hubspot_state:{user_id}:{org_id}', encoded_state, expire=600)

    return f'{authorization_url}&scope={scopes}&state={encoded_state}'

async def oauth2callback_hubspot(request: Request):
    # TODO
    pass

async def get_hubspot_credentials(user_id, org_id):
    # TODO
    pass

async def create_integration_item_metadata_object(response_json):
    # TODO
    pass

async def get_items_hubspot(credentials):
    # TODO
    pass