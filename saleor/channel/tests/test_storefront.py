import pytest
from django.core.exceptions import ValidationError

from ..storefront import clean_storefront_locales


def test_clean_storefront_locales_normalizes_and_dedupes():
    locales, default = clean_storefront_locales([" FR ", "fr_CA", "fr"], "FR-ca")
    assert locales == ["fr", "fr-ca"]
    assert default == "fr-ca"


def test_clean_storefront_locales_empty():
    assert clean_storefront_locales(None, None) == ([], None)
    assert clean_storefront_locales(["", " "], "") == ([], None)


def test_clean_storefront_locales_rejects_unknown_code():
    with pytest.raises(ValidationError) as exc:
        clean_storefront_locales(["en", "xx-yy"], None)
    assert "storefront_locales" in exc.value.message_dict


def test_clean_storefront_locales_rejects_unlisted_default():
    with pytest.raises(ValidationError) as exc:
        clean_storefront_locales(["en"], "fr")
    assert "default_locale" in exc.value.message_dict


def test_channel_storefront_fields_defaults(channel_USD):
    channel_USD.refresh_from_db()
    assert channel_USD.storefront_locales == []
    assert channel_USD.default_locale is None
    assert channel_USD.is_storefront_visible is False
