from io import StringIO

from django.core.management import call_command


def _run(*args):
    out = StringIO()
    call_command("copy_storefront_channel_metadata", *args, stdout=out)
    return out.getvalue()


def test_copies_metadata_into_fields(channel_USD):
    channel_USD.metadata = {
        "storefront.locales": "en, FR-ca,xx",
        "storefront.defaultLocale ": "fr-ca",
    }
    channel_USD.save(update_fields=["metadata"])

    output = _run()

    channel_USD.refresh_from_db()
    assert channel_USD.storefront_locales == ["en", "fr-ca"]
    assert channel_USD.default_locale == "fr-ca"
    assert channel_USD.is_storefront_visible is True
    assert "dropped unknown: xx" in output
    # Metadata stays as the storefront fallback.
    assert "storefront.locales" in channel_USD.metadata


def test_dry_run_and_skip_rules(channel_USD, channel_PLN):
    channel_USD.metadata = {"storefront.locales": "en"}
    channel_USD.save(update_fields=["metadata"])
    _run("--dry-run")
    channel_USD.refresh_from_db()
    assert channel_USD.storefront_locales == []

    channel_USD.storefront_locales = ["ja"]
    channel_USD.is_storefront_visible = True
    channel_USD.save(update_fields=["storefront_locales", "is_storefront_visible"])
    output = _run()
    channel_USD.refresh_from_db()
    assert channel_USD.storefront_locales == ["ja"]
    assert "fields already set" in output
    assert f"{channel_PLN.slug}: no storefront.locales metadata" in output


def test_default_not_in_list_is_cleared(channel_USD):
    channel_USD.metadata = {
        "storefront.locales": "en",
        "storefront.defaultLocale": "fr",
    }
    channel_USD.save(update_fields=["metadata"])
    _run()
    channel_USD.refresh_from_db()
    assert channel_USD.storefront_locales == ["en"]
    assert channel_USD.default_locale is None
