from datetime import datetime, timedelta
import pytest
import freezegun

from config import Config


@pytest.fixture(scope='function')
def test_client_unauthenticated(flask_app):
    # Create a test client using the Flask application configured for testing
    with flask_app.test_client() as testing_client:
        yield testing_client


@pytest.fixture(scope='function')
def test_client_logged(flask_app, init_database):
    # Create a test client using the Flask application configured for testing
    with flask_app.test_client() as testing_client:
        r = testing_client.post('/login', json={'phone_number': '+19870000001', 'password': 'qwerty'})
        assert r.status_code == 200
        yield testing_client


def test_register(test_client, init_database):
    response = test_client.post('/register', json={
        'phone_number': '+19870000003',
        'password': 'qwerty',
        'first_name': 'John',
        'last_name': 'Doe'
    })
    assert response.status_code == 200


def test_login(test_client, init_database):
    response = test_client.post('/login', json={'phone_number': '+19870000001', 'password': 'qwerty'})
    assert response.status_code == 200


def test_logout(test_client_logged, init_database):
    response = test_client_logged.post('/logout')
    assert response.status_code == 200


def test_change_password(test_client, init_database):
    # request a password change
    # NOTE: doing this to keep tests super simple (don't test like this in a real project!)
    response = test_client.post('/change_password', json={'old_password': 'qwerty', 'new_password': 'qwerty'})
    assert response.status_code == 200


def test_jwt_expiration(init_database, test_client_logged):
    """Test login authenticated endpoints are blocked when JWT expires"""
    now = datetime.utcnow()
    expiration = Config.JWT_ACCESS_TOKEN_EXPIRES + timedelta(seconds=1)
    # jumping ahead in time after JWT expiration
    with freezegun.freeze_time(now + expiration):
        r = test_client_logged.get('/user')
        assert r.status_code == 401
        assert r.json['msg'] == 'Token has expired'


def test_jwt_missing(init_database, test_client_unauthenticated):
    """Test no JWT cookie is present"""
    assert not test_client_unauthenticated.get_cookie('access_token_cookie')
    r = test_client_unauthenticated.get('/user')
    assert r.status_code == 401
    assert r.json['msg'] == 'Missing cookie "access_token_cookie"'
