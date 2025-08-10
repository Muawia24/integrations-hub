import json
import pytest
from unittest.mock import AsyncMock, Mock, patch
from integrations.hubspot import get_items_hubspot, create_integration_item_metadata_object
from integrations.integration_item import IntegrationItem


@pytest.mark.asyncio
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

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_data

    async_mock_get = AsyncMock(return_value=mock_response)
    with patch("httpx.AsyncClient.get", async_mock_get):
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