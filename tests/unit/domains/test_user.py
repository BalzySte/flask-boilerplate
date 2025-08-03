from datetime import datetime
import pytest

from app import USERS_COLL


@pytest.fixture(scope='function')
def logged_test_user(init_database, test_client):
    response = test_client.post('/login', json={'phone_number': '+19870000002', 'password': 'qwerty'})
    assert response.status_code == 200
    return response.json['_id']


@pytest.fixture(scope='function')
def reset_user_contacts(init_database, logged_test_user):
    empty_contacts = {'email': None, 'telegram': None}
    USERS_COLL.update_one(
        {'_id': logged_test_user},
        {'$set': {'contacts': empty_contacts}}
    )


def test_user_get(init_database, test_client):
    response = test_client.post('/login', json={'phone_number': '+19870000002', 'password': 'qwerty'})
    assert response.status_code == 200

    response = test_client.get('/user')
    response_keys = response.json.keys()
    assert response.status_code == 200
    assert 'password' not in response_keys


def test_user_put(init_database, test_client):
    response = test_client.post('/login', json={'phone_number': '+19870000002', 'password': 'qwerty'})
    assert response.status_code == 200
    response = test_client.put('/user', json={
        'first_name': 'New First', 
        'last_name': 'New Last',
        'date_of_birth': '1990-01-15'
    })
    assert response.status_code == 200
    user = USERS_COLL.find_one(response.json['_id'])
    assert user['details']['first_name'] == 'New First'
    assert user['details']['last_name'] == 'New Last'
    # Check that date_of_birth was updated (compare as date strings)
    expected_date = datetime(1990, 1, 15)
    actual_date = user['details']['date_of_birth']
    assert actual_date.date() == expected_date.date()


def test_user_put_missing_fields(init_database, test_client):
    response = test_client.post('/login', json={'phone_number': '+19870000002', 'password': 'qwerty'})
    assert response.status_code == 200
    
    # Test missing first_name
    response = test_client.put('/user', json={
        'last_name': 'New Last',
        'date_of_birth': '1990-01-15'
    })
    assert response.status_code == 400
    
    # Test missing last_name
    response = test_client.put('/user', json={
        'first_name': 'New First',
        'date_of_birth': '1990-01-15'
    })
    assert response.status_code == 400
    
    # Test missing date_of_birth
    response = test_client.put('/user', json={
        'first_name': 'New First',
        'last_name': 'New Last'
    })
    assert response.status_code == 400


def test_user_put_invalid_date(init_database, test_client):
    response = test_client.post('/login', json={'phone_number': '+19870000002', 'password': 'qwerty'})
    assert response.status_code == 200
    
    # Test invalid date format
    response = test_client.put('/user', json={
        'first_name': 'New First',
        'last_name': 'New Last',
        'date_of_birth': 'invalid-date'
    })
    assert response.status_code == 400
    assert 'invalid date format' in response.json['msg']


def test_user_put_security(init_database, test_client):
    # testing endpoint against possible attacks
    response = test_client.post('/login', json={'phone_number': '+19870000002', 'password': 'qwerty'})
    assert response.status_code == 200
    
    # trying to inject malicious fields
    response = test_client.put('/user', json={
        'first_name': 'New First', 
        'last_name': 'New Last',
        'date_of_birth': '1990-01-15',
        'role': 'admin',  # This should be ignored due to additionalProperties: false
        'balance': 999999  # This should be ignored due to additionalProperties: false
    })
    assert response.status_code == 400  # Should fail due to additionalProperties: false


def test_user_contacts_post(init_database, test_client, logged_test_user, reset_user_contacts):
    # set multiple contact fields - email and Telegram ID
    r = test_client.post('/user/contacts', json={
        'email': 'another@example.com',
        'telegram': 'telegram_user'
    })
    assert r.status_code == 200
    contacts = USERS_COLL.find_one({'_id': logged_test_user}, {'contacts': True})['contacts']
    assert contacts['email']['contact'] == 'another@example.com'
    assert contacts['telegram']['contact'] == 'telegram_user'
    assert contacts['telegram']['chat_id'] is None

    # set one single contact (telegram) - assert other contacts are kept
    r = test_client.post('/user/contacts', json={
        'telegram': 'diff_telegram_user'
    })
    assert r.status_code == 200
    contacts = USERS_COLL.find_one({'_id': logged_test_user}, {'contacts': True})['contacts']
    assert contacts['email']['contact'] == 'another@example.com'
    assert contacts['telegram']['contact'] == 'diff_telegram_user'
    assert contacts['telegram']['chat_id'] is None

    # test invalid email and invalid
    r = test_client.post('/user/contacts', json={
        'email': '$!!invalid-email'
    })
    assert r.status_code == 400

    r = test_client.post('/user/contacts', json={
        'telegram': '@telegram_user'  # starts with @ - not allowed
    })
    assert r.status_code == 400


def test_user_contacts_get(init_database, test_client, logged_test_user, reset_user_contacts):
    # set multiple contact fields - update email and set Telegram ID
    r = test_client.post('/user/contacts', json={
        'email': 'user@example.com',
    })
    assert r.status_code == 200

    r = test_client.get('/user')
    assert r.status_code == 200
    r_contacts = r.json['contacts']
    assert r_contacts['email'] == {'contact': 'user@example.com'}
    assert r_contacts['telegram'] is None

    r = test_client.get('/user')
    assert r.status_code == 200
    r_contacts = r.json['contacts']
    assert r_contacts['email'] == {'contact': 'user@example.com'}
    assert r_contacts['telegram'] is None
