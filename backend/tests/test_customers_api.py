from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_get_customers():
    response = client.get('/customers', params={'limit': 5, 'offset': 0})
    assert response.status_code == 200
    payload = response.json()
    assert 'items' in payload
    assert 'total' in payload
    assert payload['limit'] == 5
    assert payload['offset'] == 0
    assert len(payload['items']) <= 5
    assert payload['items'][0]['customer_number']


def test_get_customer_by_id():
    response = client.get('/customers/1')
    assert response.status_code == 200
    payload = response.json()
    assert payload['id'] == 1
    assert payload['customer_number'] == 'CUST001'
    assert payload['full_name'] == 'Aarav Mehta'


def test_get_customer_context():
    response = client.get('/customers/1/context')
    assert response.status_code == 200
    payload = response.json()
    assert payload['customer']['id'] == 1
    assert isinstance(payload['loans'], list)
    assert isinstance(payload['payments'], list)
    assert isinstance(payload['previous_calls'], list)


def test_get_nonexistent_customer_404():
    response = client.get('/customers/999999')
    assert response.status_code == 404
    assert response.json()['detail'] == 'Customer not found'
