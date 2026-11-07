import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("channel", "0027_channel_allow_legacy_gift_card_use"),
    ]

    operations = [
        migrations.AddField(
            model_name="channel",
            name="storefront_locales",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.CharField(max_length=35),
                blank=True,
                db_default=[],
                default=list,
                size=None,
            ),
        ),
        migrations.AddField(
            model_name="channel",
            name="default_locale",
            field=models.CharField(blank=True, max_length=35, null=True),
        ),
        migrations.AddField(
            model_name="channel",
            name="is_storefront_visible",
            field=models.BooleanField(db_default=False, default=False),
        ),
    ]
