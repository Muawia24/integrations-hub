import json
import pytest
import respx
from httpx import Response
from integrations.hubspot import get_items_hubspot, create_integration_item_metadata_object
from integrations.integration_item import IntegrationItem


@pytest.mark.asyncio
@respx.mock
async def test_get_items_hubspot_success():
    # Mock credentials
    credentials = json.dumps({"access_token": "fake_token"})

    # Mock HubSpot API response
    mock_data = {
        "results": [
            {
                "id": "123",
                "properties": {
                    "firstname": "Ahmed",
                    "lastname": "Muawia",
                    "email": "ahmed@example.com"
                },
                "createdAt": "2025-08-07T17:35:28.768Z",
                "updatedAt": "2025-08-07T17:35:43.234Z"
            }
        ]
    }

    respx.get("https://api.hubapi.com/crm/v3/objects/contacts").mock(
        return_value=Response(200, json=mock_data)
    )

    items = await get_items_hubspot(credentials)
    assert len(items) == 1
    assert isinstance(items[0], IntegrationItem)
    assert items[0].name == "Ahmed Muawia"
    assert items[0].id == "123"
    assert items[0].type == "hubspot_contact"


def test_create_integration_item_metadata_object():
    # Sample HubSpot contact
    response_json = {
        "id": "123",
        "properties": {
            "firstname": "Ahmed",
            "lastname": "Muawia",
            "email": "ahmed@muawia.com"
        },
        "createdAt": "2025-08-07T17:35:28.768Z",
        "updatedAt": "2025-08-07T17:35:43.234Z"
    }

    item = create_integration_item_metadata_object(response_json)
    assert item.id == "123"
    assert item.name == "Ahmed Muawia"
    assert item.type == "hubspot_contact"