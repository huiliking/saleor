"""Storefront locale fields on channels (ADR 0008, Phase 2)."""

import graphene

from .....channel.error_codes import ChannelErrorCode
from .....channel.models import Channel
from ....tests.utils import assert_no_permission, get_graphql_content

CHANNEL_CREATE = """
    mutation CreateChannel($input: ChannelCreateInput!) {
        channelCreate(input: $input) {
            channel { slug storefrontLocales defaultLocale isStorefrontVisible }
            errors { field code message }
        }
    }
"""

CHANNEL_UPDATE = """
    mutation UpdateChannel($id: ID!, $input: ChannelUpdateInput!) {
        channelUpdate(id: $id, input: $input) {
            channel { slug storefrontLocales defaultLocale isStorefrontVisible }
            errors { field code message }
        }
    }
"""

CHANNEL_QUERY = """
    query Channel($slug: String!) {
        channel(slug: $slug) { slug storefrontLocales defaultLocale isStorefrontVisible }
    }
"""


def test_channel_create_with_storefront_settings(
    staff_api_client, permission_manage_channels
):
    variables = {
        "input": {
            "name": "Canada",
            "slug": "channel-cad",
            "currencyCode": "CAD",
            "defaultCountry": "CA",
            "storefrontLocales": ["fr-CA", "en"],
            "defaultLocale": "fr-ca",
            "isStorefrontVisible": True,
        }
    }
    response = staff_api_client.post_graphql(
        CHANNEL_CREATE, variables, permissions=(permission_manage_channels,)
    )
    data = get_graphql_content(response)["data"]["channelCreate"]
    assert not data["errors"]
    assert data["channel"] == {
        "slug": "channel-cad",
        "storefrontLocales": ["fr-ca", "en"],
        "defaultLocale": "fr-ca",
        "isStorefrontVisible": True,
    }
    channel = Channel.objects.get(slug="channel-cad")
    assert channel.storefront_locales == ["fr-ca", "en"]
    assert channel.default_locale == "fr-ca"


def test_channel_update_storefront_settings(
    staff_api_client, permission_manage_channels, channel_USD
):
    channel_id = graphene.Node.to_global_id("Channel", channel_USD.id)
    variables = {
        "id": channel_id,
        "input": {"storefrontLocales": ["en", "ja"], "defaultLocale": "en"},
    }
    response = staff_api_client.post_graphql(
        CHANNEL_UPDATE, variables, permissions=(permission_manage_channels,)
    )
    data = get_graphql_content(response)["data"]["channelUpdate"]
    assert not data["errors"]
    channel_USD.refresh_from_db()
    assert channel_USD.storefront_locales == ["en", "ja"]
    assert channel_USD.default_locale == "en"


def test_channel_update_rejects_unknown_locale(
    staff_api_client, permission_manage_channels, channel_USD
):
    channel_id = graphene.Node.to_global_id("Channel", channel_USD.id)
    variables = {"id": channel_id, "input": {"storefrontLocales": ["en", "xx-yy"]}}
    response = staff_api_client.post_graphql(
        CHANNEL_UPDATE, variables, permissions=(permission_manage_channels,)
    )
    errors = get_graphql_content(response)["data"]["channelUpdate"]["errors"]
    assert errors[0]["field"] == "storefrontLocales"
    assert errors[0]["code"] == ChannelErrorCode.INVALID.name
    channel_USD.refresh_from_db()
    assert channel_USD.storefront_locales == []


def test_channel_update_rejects_default_outside_stored_locales(
    staff_api_client, permission_manage_channels, channel_USD
):
    # Partial update: only defaultLocale sent, checked against the stored list.
    channel_USD.storefront_locales = ["en"]
    channel_USD.save(update_fields=["storefront_locales"])
    channel_id = graphene.Node.to_global_id("Channel", channel_USD.id)
    variables = {"id": channel_id, "input": {"defaultLocale": "fr"}}
    response = staff_api_client.post_graphql(
        CHANNEL_UPDATE, variables, permissions=(permission_manage_channels,)
    )
    errors = get_graphql_content(response)["data"]["channelUpdate"]["errors"]
    assert errors[0]["field"] == "defaultLocale"
    assert errors[0]["code"] == ChannelErrorCode.INVALID.name


def test_channel_update_storefront_settings_requires_manage_channels(
    staff_api_client, permission_manage_orders, channel_USD
):
    channel_id = graphene.Node.to_global_id("Channel", channel_USD.id)
    variables = {"id": channel_id, "input": {"storefrontLocales": ["en"]}}
    response = staff_api_client.post_graphql(
        CHANNEL_UPDATE, variables, permissions=(permission_manage_orders,)
    )
    assert_no_permission(response)


def test_channel_storefront_fields_require_app_or_staff(
    api_client, app_api_client, channel_USD
):
    channel_USD.storefront_locales = ["en"]
    channel_USD.save(update_fields=["storefront_locales"])
    # Anonymous: not public (same rule as the channel name).
    response = api_client.post_graphql(CHANNEL_QUERY, {"slug": channel_USD.slug})
    assert_no_permission(response)
    # Any authenticated app (no specific permission) can read them.
    response = app_api_client.post_graphql(CHANNEL_QUERY, {"slug": channel_USD.slug})
    data = get_graphql_content(response)["data"]["channel"]
    assert data["storefrontLocales"] == ["en"]
    assert data["isStorefrontVisible"] is False
