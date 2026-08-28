import pytest

from src.i18n import t


def test_t_returns_spanish_by_default():
    assert t("ui.client_label") == "Cliente"


def test_t_returns_requested_language():
    assert t("ui.client_label", "en") == "Client"


def test_t_formats_kwargs():
    assert t("ui.client_added", "es", id="abc-123") == "Cliente añadido: abc-123"
    assert t("ui.client_added", "en", id="abc-123") == "Client added: abc-123"


def test_t_raises_on_unknown_key():
    with pytest.raises(KeyError):
        t("nonexistent.key")


def test_t_raises_on_unknown_language():
    with pytest.raises(KeyError):
        t("ui.client_label", "fr")
