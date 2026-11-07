"""Channel default locale overrides the stored language (ADR 0008, Phase 2)."""

import graphene

from ...account.models import User
from ...checkout.complete_checkout import create_order_from_checkout
from ...checkout.fetch import fetch_checkout_info, fetch_checkout_lines
from ...checkout.models import Checkout
from ...graphql.core.utils import to_global_id_or_none
from ...graphql.tests.utils import get_graphql_content
from ...order.models import Order
from ...plugins.manager import get_plugins_manager
from ..storefront import channel_document_language


def _set_default_locale(channel, locale="fr"):
    channel.storefront_locales = [locale, "en"]
    channel.default_locale = locale
    channel.save(update_fields=["storefront_locales", "default_locale"])


def test_channel_document_language_rule(channel_USD):
    assert channel_document_language(channel_USD, "en") == "en"
    assert channel_document_language(None, "en") == "en"
    _set_default_locale(channel_USD, "fr-ca")
    assert channel_document_language(channel_USD, "en") == "fr-ca"
    assert channel_document_language(channel_USD, None) == "fr-ca"


CHECKOUT_CREATE = """
mutation($channel: String!, $languageCode: LanguageCodeEnum!) {
  checkoutCreate(input: {channel: $channel, lines: [], languageCode: $languageCode}) {
    checkout { id languageCode }
    errors { field code message }
  }
}
"""


def test_checkout_create_uses_channel_default_locale(api_client, channel_USD):
    _set_default_locale(channel_USD)
    response = api_client.post_graphql(
        CHECKOUT_CREATE, {"channel": channel_USD.slug, "languageCode": "EN"}
    )
    data = get_graphql_content(response)["data"]["checkoutCreate"]
    assert not data["errors"]
    assert Checkout.objects.get().language_code == "fr"


def test_checkout_create_keeps_requested_language_without_default(
    api_client, channel_USD
):
    response = api_client.post_graphql(
        CHECKOUT_CREATE, {"channel": channel_USD.slug, "languageCode": "PL"}
    )
    assert not get_graphql_content(response)["data"]["checkoutCreate"]["errors"]
    assert Checkout.objects.get().language_code == "pl"


CHECKOUT_LANGUAGE_UPDATE = """
mutation($id: ID, $languageCode: LanguageCodeEnum!) {
  checkoutLanguageCodeUpdate(id: $id, languageCode: $languageCode) {
    checkout { languageCode }
    errors { field code }
  }
}
"""


def test_checkout_language_update_is_overridden(user_api_client, checkout_with_item):
    _set_default_locale(checkout_with_item.channel)
    variables = {"id": to_global_id_or_none(checkout_with_item), "languageCode": "PL"}
    response = user_api_client.post_graphql(CHECKOUT_LANGUAGE_UPDATE, variables)
    assert not get_graphql_content(response)["data"]["checkoutLanguageCodeUpdate"][
        "errors"
    ]
    checkout_with_item.refresh_from_db()
    assert checkout_with_item.language_code == "fr"


def test_order_from_checkout_uses_channel_default_locale(
    checkout_with_item, address, app
):
    checkout_with_item.shipping_address = address
    checkout_with_item.billing_address = address
    checkout_with_item.language_code = "pl"  # e.g. created before the default was set
    checkout_with_item.save()
    _set_default_locale(checkout_with_item.channel)
    manager = get_plugins_manager(allow_replica=False)
    lines, _ = fetch_checkout_lines(checkout_with_item)
    checkout_info = fetch_checkout_info(checkout_with_item, lines, manager)

    order = create_order_from_checkout(
        checkout_info=checkout_info, manager=manager, user=None, app=app
    )

    assert order.language_code == "fr"


DRAFT_ORDER_CREATE = """
mutation($input: DraftOrderCreateInput!) {
  draftOrderCreate(input: $input) {
    order { id languageCode }
    errors { field code message }
  }
}
"""


def test_draft_order_create_uses_channel_default_locale(
    staff_api_client, permission_group_manage_orders, channel_USD
):
    permission_group_manage_orders.user_set.add(staff_api_client.user)
    _set_default_locale(channel_USD)
    channel_id = graphene.Node.to_global_id("Channel", channel_USD.id)
    response = staff_api_client.post_graphql(
        DRAFT_ORDER_CREATE, {"input": {"channelId": channel_id, "languageCode": "EN"}}
    )
    data = get_graphql_content(response)["data"]["draftOrderCreate"]
    assert not data["errors"]
    assert Order.objects.get().language_code == "fr"


ORDER_UPDATE = """
mutation($id: ID!, $input: OrderUpdateInput!) {
  orderUpdate(id: $id, input: $input) {
    order { languageCode }
    errors { field code message }
  }
}
"""


def test_order_update_language_is_overridden(
    staff_api_client, permission_group_manage_orders, order_with_lines
):
    permission_group_manage_orders.user_set.add(staff_api_client.user)
    _set_default_locale(order_with_lines.channel)
    order_id = graphene.Node.to_global_id("Order", order_with_lines.id)
    response = staff_api_client.post_graphql(
        ORDER_UPDATE, {"id": order_id, "input": {"languageCode": "PL"}}
    )
    data = get_graphql_content(response)["data"]["orderUpdate"]
    assert not data["errors"]
    order_with_lines.refresh_from_db()
    assert order_with_lines.language_code == "fr"


ACCOUNT_REGISTER = """
mutation($input: AccountRegisterInput!) {
  accountRegister(input: $input) { errors { field code message } }
}
"""


def test_account_register_uses_channel_default_locale(
    api_client, channel_USD, site_settings
):
    site_settings.enable_account_confirmation_by_email = False
    site_settings.save(update_fields=["enable_account_confirmation_by_email"])
    _set_default_locale(channel_USD)
    variables = {
        "input": {
            "email": "adr8-register@example.com",
            "password": "Pa55w.rd-Strong",
            "channel": channel_USD.slug,
            "languageCode": "EN",
        }
    }
    response = api_client.post_graphql(ACCOUNT_REGISTER, variables)
    assert not get_graphql_content(response)["data"]["accountRegister"]["errors"]
    assert User.objects.get(email="adr8-register@example.com").language_code == "fr"
