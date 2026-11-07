"""Copy Phase 1 storefront metadata into the Phase 2 channel fields (ADR 0008, M1).

Phase 1 kept the storefront market config in channel public metadata
(`storefront.locales`, `storefront.defaultLocale`). This one-off command copies it into
`storefront_locales`, `default_locale` and `is_storefront_visible`. The metadata is left in
place (storefronts fall back to it for one release). Channels whose fields are already set
are skipped unless `--force`.
"""

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand

from ...models import Channel
from ...storefront import SUPPORTED_LOCALES, clean_storefront_locales, normalize_locale

LOCALES_KEY = "storefront.locales"
DEFAULT_KEY = "storefront.defaultLocale"


def _read(metadata: dict, key: str) -> str | None:
    # Keys were typed by hand in the Dashboard — tolerate stray spaces.
    for raw_key, value in (metadata or {}).items():
        if raw_key.strip() == key:
            return str(value).strip()
    return None


def _fields_set(channel: Channel) -> bool:
    return bool(
        channel.storefront_locales
        or channel.default_locale
        or channel.is_storefront_visible
    )


class Command(BaseCommand):
    help = "Copy storefront.* channel metadata into the storefront channel fields."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Report only.")
        parser.add_argument(
            "--force",
            action="store_true",
            help="Overwrite channels whose fields are set.",
        )

    def handle(self, *args, **options):
        for channel in Channel.objects.order_by("slug"):
            raw_locales = _read(channel.metadata, LOCALES_KEY)
            if raw_locales is None:
                self.stdout.write(f"{channel.slug}: no {LOCALES_KEY} metadata, skipped")
                continue
            if _fields_set(channel) and not options["force"]:
                self.stdout.write(f"{channel.slug}: fields already set, skipped")
                continue

            requested = [normalize_locale(code) for code in raw_locales.split(",")]
            known = [code for code in requested if code in SUPPORTED_LOCALES]
            dropped = sorted({code for code in requested if code and code not in known})
            default = _read(channel.metadata, DEFAULT_KEY)
            try:
                locales, default = clean_storefront_locales(known, default)
            except ValidationError:
                # Default not in the list: keep the locales, drop the default.
                locales, default = clean_storefront_locales(known, None)
                self.stdout.write(
                    f"{channel.slug}: default locale not in list, cleared"
                )

            before = (
                channel.storefront_locales,
                channel.default_locale,
                channel.is_storefront_visible,
            )
            after = (locales, default, bool(locales))
            note = f" (dropped unknown: {', '.join(dropped)})" if dropped else ""
            self.stdout.write(f"{channel.slug}: {before} -> {after}{note}")
            if options["dry_run"]:
                continue
            (
                channel.storefront_locales,
                channel.default_locale,
                channel.is_storefront_visible,
            ) = after
            channel.save(
                update_fields=[
                    "storefront_locales",
                    "default_locale",
                    "is_storefront_visible",
                ]
            )
