from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_list_customer_accounts_mock():
    response = client.get("/accounts/customer/cust_1")
    assert response.status_code == 200
    accounts = response.json()
    assert len(accounts) == 2
    assert accounts[0]["type"] == "Checking"


def test_list_transactions_mock():
    response = client.get("/accounts/acc_1/transactions")
    assert response.status_code == 200
    transactions = response.json()
    assert len(transactions) == 14


def test_simulate_purchase_appends_transaction():
    before = client.get("/accounts/acc_1/transactions").json()
    response = client.post(
        "/accounts/acc_1/transactions/simulate",
        json={"merchant_id": "merchant_test", "amount": 42.5, "description": "Test"},
    )
    assert response.status_code == 200
    after = client.get("/accounts/acc_1/transactions").json()
    assert len(after) == len(before) + 1
    assert after[0]["amount"] == 42.5
