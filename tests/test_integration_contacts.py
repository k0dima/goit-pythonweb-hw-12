import pytest
from datetime import date, timedelta


@pytest.fixture
def created_contacts(client, get_token):
    headers = {"Authorization": f"Bearer {get_token}"}
    created = []

    try:
        for offset in (0, 3, 8):
            birthday = date.today() + timedelta(days=offset)
            contact = {
                "first_name": f"Contact{offset}",
                "last_name": "Test",
                "email": f"fixture{offset}@example.com",
                "phone": "123456789",
                "birthday": birthday.isoformat(),
            }

            response = client.post(
                "/api/contacts/",
                json=contact,
                headers=headers,
            )
            assert response.status_code == 201, response.text
            created.append(response.json())

        yield created

    finally:
        for contact in created:
            response = client.delete(
                f"/api/contacts/{contact['id']}",
                headers=headers,
            )
            assert response.status_code in (200, 404), response.text


def test_read_contacts(client, get_token, created_contacts):
    response = client.get(
        "/api/contacts",
        headers={"Authorization": f"Bearer {get_token}"}
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert isinstance(data, list)

    assert len(data) == len(created_contacts)

    actual = sorted(data, key=lambda contact: contact["id"])
    expected = sorted(created_contacts, key=lambda contact: contact["id"])

    assert actual == expected


def test_read_upcoming_birthdays(client, get_token, created_contacts):
    today = date.today()
    next_birthday_range = today + timedelta(days=7)

    upcoming = list(filter(
        lambda contact: (
                today
                <= date.fromisoformat(contact["birthday"])
                <= next_birthday_range
        ),
        created_contacts,
    ))

    response = client.get(
        "/api/contacts/upcoming-birthdays",
        headers={"Authorization": f"Bearer {get_token}"}
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert isinstance(data, list)

    assert len(data) == len(upcoming)

    actual = sorted(data, key=lambda contact: contact["id"])
    expected = sorted(upcoming, key=lambda contact: contact["id"])

    assert actual == expected


def test_create_contact(client, get_token):
    contact = {
        "first_name": "first_name",
        "last_name": "last_name",
        "email": "email",
        "phone": "123456789",
        "birthday": "1990-05-07",
        "additional_data": "additional_data"
    }
    response = client.post(
        "/api/contacts",
        json=contact,
        headers={"Authorization": f"Bearer {get_token}"},
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["first_name"] == contact["first_name"]
    assert data["last_name"] == contact["last_name"]
    assert data["email"] == contact["email"]
    assert data["phone"] == contact["phone"]
    assert data["birthday"] == contact["birthday"]
    assert data["additional_data"] == contact["additional_data"]
    assert "id" in data


def test_read_contact(client, get_token, created_contacts):
    contact = created_contacts[0]

    response = client.get(
        f"/api/contacts/{contact["id"]}",
        headers={"Authorization": f"Bearer {get_token}"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["first_name"] == contact["first_name"]
    assert data["last_name"] == contact["last_name"]
    assert data["email"] == contact["email"]
    assert data["phone"] == contact["phone"]
    assert data["birthday"] == contact["birthday"]
    assert data["additional_data"] == contact["additional_data"]
    assert data["id"] == contact["id"]

def test_read_not_found_contact(client, get_token, created_contacts):
    not_existing_contact = 9999
    response = client.get(
        f"/api/contacts/{not_existing_contact}",
        headers={"Authorization": f"Bearer {get_token}"},
    )
    assert response.status_code == 404, response.text
    assert response.json()["detail"] == (
        f"Contact with ID {not_existing_contact} not found"
    )


def test_read_not_access_contact(client, get_token, created_contacts):
    contact = created_contacts[0]

    response = client.get(
        f"/api/contacts/{contact["id"]}",
        headers={"Authorization": "Bearer"},
    )
    assert response.status_code == 401, response.text
    assert response.json()["detail"] == "Could not validate credentials"
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_update_contact(client, get_token, created_contacts):
    contact = created_contacts[0]
    updated_contact_fields = {
        "first_name": "updated_first_name",
        "additional_data": "updated_additional_data",
        "phone": "097999999"
    }
    response = client.put(
        f"/api/contacts/{contact["id"]}",
        json=updated_contact_fields,
        headers={"Authorization": f"Bearer {get_token}"},
    )

    assert response.status_code == 200, response.text
    data = response.json()

    assert data["first_name"] == updated_contact_fields["first_name"]
    assert data["phone"] == updated_contact_fields["phone"]
    assert data["additional_data"] == updated_contact_fields["additional_data"]

    assert data["last_name"] == contact["last_name"]
    assert data["email"] == contact["email"]
    assert data["birthday"] == contact["birthday"]
    assert data["id"] == contact["id"]

def test_update_not_found_contact(client, get_token, created_contacts):
    not_existing_contact = 9999
    updated_contact_fields = {
        "first_name": "updated_first_name",
    }
    response = client.put(
        f"/api/contacts/{not_existing_contact}",
        json=updated_contact_fields,
        headers={"Authorization": f"Bearer {get_token}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == f"Contact with ID {not_existing_contact} not found"

def test_update_already_exist_contact(client, get_token, created_contacts):
    contact = created_contacts[0]
    another_contact = created_contacts[1]
    updated_contact_fields = {
        "email": another_contact["email"],
    }

    response = client.put(
        f"/api/contacts/{contact["id"]}",
        json=updated_contact_fields,
        headers={"Authorization": f"Bearer {get_token}"},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Contact with this email already exists"


def test_delete_contact(client, get_token, created_contacts):
    contact = created_contacts[0]

    response = client.delete(
        f"/api/contacts/{contact["id"]}",
        headers={"Authorization": f"Bearer {get_token}"},
    )
    assert response.status_code == 200
    assert response.json()["id"] == contact["id"]

def test_delete_not_found_ontact(client, get_token):
    not_exist_contact_id = 9999

    response = client.delete(
        f"/api/contacts/{not_exist_contact_id}",
        headers={"Authorization": f"Bearer {get_token}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == f"Contact with ID {not_exist_contact_id} not found"

def test_delete_not_access_contact(client, get_token, created_contacts):
    contact = created_contacts[0]

    response = client.get(
        f"/api/contacts/{contact["id"]}",
        headers={"Authorization": "Bearer"},
    )
    assert response.status_code == 401, response.text
    assert response.json()["detail"] == "Could not validate credentials"
    assert response.headers["WWW-Authenticate"] == "Bearer"

