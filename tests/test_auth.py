from da.extensions import db
from da.models import User


def test_registration_allows_only_company_domain(client):
    response = client.post(
        "/auth/register",
        data={
            "email": "user@gmail.com",
            "first_name": "Test",
            "last_name": "User",
            "middle_name": "",
            "phone": "+7700000000",
            "telegram": "@user",
            "password": "Password123!",
            "password_confirm": "Password123!",
        },
        follow_redirects=True,
    )
    assert b"\xd0\xa0\xd0\xb5\xd0\xb3\xd0\xb8\xd1\x81\xd1\x82\xd1\x80\xd0\xb0\xd1\x86\xd0\xb8\xd1\x8f \xd0\xb4\xd0\xbe\xd1\x81\xd1\x82\xd1\x83\xd0\xbf\xd0\xbd\xd0\xb0 \xd1\x82\xd0\xbe\xd0\xbb\xd1\x8c\xd0\xba\xd0\xbe" in response.data


def test_registration_and_login_flow(client, app):
    # Register user
    resp = client.post(
        "/auth/register",
        data={
            "email": "lead@ittest-team.ru",
            "first_name": "Lead",
            "last_name": "User",
            "middle_name": "",
            "phone": "+77770000000",
            "telegram": "@lead",
            "password": "Password123!",
            "password_confirm": "Password123!",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200

    with app.app_context():
        user = User.query.filter_by(email="lead@ittest-team.ru").one()
        assert user.role.name == "SUPER_ADMIN"

    # Login
    login_resp = client.post(
        "/auth/login",
        data={
            "email": "lead@ittest-team.ru",
            "password": "Password123!",
        },
        follow_redirects=True,
    )
    assert b"\xd0\x92\xd1\x8b \xd1\x83\xd1\x81\xd0\xbf\xd0\xb5\xd1\x88\xd0\xbd\xd0\xbe \xd0\xb2\xd0\xbe\xd1\x88\xd0\xbb\xd0\xb8" in login_resp.data

