from app import USERS_COLL
from config import Config


def test_admin_user_forbidden(init_database, test_client):
    response = test_client.post('/login', json={'phone_number': '+19870000002', 'password': 'qwerty'})
    assert response.status_code == 200

    response = test_client.get('admin/users')
    assert response.status_code == 401


def test_admin_users_get(init_database, test_client):
    response = test_client.post('/login', json={'phone_number': '+19870000001', 'password': 'qwerty'})
    assert response.status_code == 200

    enabled_users_count = USERS_COLL.count_documents({'status': 'active'})
    expected_page_count = (enabled_users_count - 1) // Config.USERS_PAGE_SIZE + 1
    
    response = test_client.get('admin/users')
    assert response.status_code == 200
    assert 'page_count' in response.json
    assert response.json['page_count'] == expected_page_count
    assert 'total_active_users' in response.json
    assert response.json['total_active_users'] == enabled_users_count
    assert 'users' in response.json
    assert len(response.json['users']) == min(Config.USERS_PAGE_SIZE, enabled_users_count)
