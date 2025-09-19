import pytest
from django.test import Client
from django.urls import reverse


@pytest.mark.django_db
def test_healthcheck_ok(client: Client) -> None:
    """
    Basic health check endpoint should return HTTP 200 and
    contain status + database info in JSON payload.
    """
    url = reverse("healthcheck")
    response = client.get(url)

    assert response.status_code == 200
    data = response.json()

    assert "status" in data
    assert "database" in data
    assert "redis" in data

    assert data["status"] in ("ok", "error")
    assert isinstance(data["database"], bool)
    assert data["redis"] in (True, False, None)
