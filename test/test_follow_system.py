import pytest
import utils.data_manager as dm
   # adapte si ton fichier s’appelle différemment


# -------------------------------------------------------------
# Fake DB en mémoire pour remplacer les fichiers JSON réels
# -------------------------------------------------------------
@pytest.fixture
def fake_users():
    """
    Base d'utilisateurs simulée (comme users.json).
    """
    return [
        {"id": 1, "username": "alice", "followers": [], "following": []},
        {"id": 2, "username": "bob", "followers": [], "following": []},
        {"id": 3, "username": "charlie", "followers": [], "following": []},
    ]


@pytest.fixture
def mock_read_write(monkeypatch, fake_users):
    """
    Remplace read_users() et write_users() par notre base en mémoire.
    """

    # read_users → renvoie la fake DB
    monkeypatch.setattr(dm, "read_users", lambda: fake_users)

    # write_users → met à jour la fake DB directement
    monkeypatch.setattr(dm, "write_users", lambda users: None)

    return fake_users


# -------------------------------------------------------------
# Tests
# -------------------------------------------------------------

def test_follow_user(mock_read_write):
    users = mock_read_write

    # Alice suit Bob
    ok = dm.follow_user(1, 2)
    assert ok is True

    # Vérification interne
    alice = next(u for u in users if u["id"] == 1)
    bob = next(u for u in users if u["id"] == 2)

    assert 2 in alice["following"]
    assert 1 in bob["followers"]


def test_unfollow_user(mock_read_write):
    users = mock_read_write

    # Préparation : Alice suit Bob
    dm.follow_user(1, 2)

    # Action : désabonnement
    ok = dm.unfollow_user(1, 2)
    assert ok is True

    alice = next(u for u in users if u["id"] == 1)
    bob = next(u for u in users if u["id"] == 2)

    assert 2 not in alice["following"]
    assert 1 not in bob["followers"]


def test_ensure_follow_fields(monkeypatch):
    # Fake DB sans les champs
    users = [
        {"id": 1, "username": "alice"},
        {"id": 2, "username": "bob"},
    ]

    # Mock
    monkeypatch.setattr(dm, "read_users", lambda: users)
    monkeypatch.setattr(dm, "write_users", lambda u: None)

    dm.ensure_follow_fields()

    for u in users:
        assert "followers" in u
        assert "following" in u
        assert isinstance(u["followers"], list)
        assert isinstance(u["following"], list)
