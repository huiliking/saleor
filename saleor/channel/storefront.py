"""Storefront market configuration on channels (ADR 0008, Phase 2).

A channel lists the storefront (market) locales it is sold in and, optionally, a default
locale. The default locale is the channel's document language: Saleor stores it on
checkouts, orders and customer accounts created in the channel, overriding the language
sent by the caller, so order/account emails and invoices follow the market.
"""

from collections.abc import Iterable

from django.conf import settings
from django.core.exceptions import ValidationError

SUPPORTED_LOCALES = frozenset(code for code, _name in settings.LANGUAGES)


def normalize_locale(value: str) -> str:
    return value.strip().lower().replace("_", "-")


def clean_storefront_locales(
    locales: Iterable[str] | None, default_locale: str | None
) -> tuple[list[str], str | None]:
    """Normalize and validate storefront locales and the default locale.

    Returns the de-duplicated locale list (input order kept) and the normalized default.
    Raises ``ValidationError`` keyed by field name for unknown codes or a default that is
    not listed.
    """
    cleaned: list[str] = []
    unknown: list[str] = []
    for raw in locales or []:
        code = normalize_locale(raw)
        if not code:
            continue
        if code not in SUPPORTED_LOCALES:
            unknown.append(raw)
        elif code not in cleaned:
            cleaned.append(code)
    if unknown:
        raise ValidationError(
            {"storefront_locales": f"Unsupported locale codes: {', '.join(unknown)}."}
        )

    default = normalize_locale(default_locale) if default_locale else None
    if default and default not in cleaned:
        raise ValidationError(
            {"default_locale": "Default locale must be one of the storefront locales."}
        )
    return cleaned, default


def channel_document_language(channel, requested: str | None) -> str | None:
    """Language to store on a checkout, order or account created in ``channel``.

    Override rule (ADR 0008, Phase 2): when the channel has a default locale it always
    wins over the language sent by the client, so documents follow the market whatever
    the caller (storefront, Dashboard, app). Without one, the requested language is kept.
    """
    default_locale = getattr(channel, "default_locale", None) if channel else None
    return default_locale or requested
