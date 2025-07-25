# Generated by Django 5.0.6 on 2025-06-12 10:00

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0003_systembalance"),
    ]

    operations = [
        migrations.AddField(
            model_name="systembalance",
            name="total_disbursed",
            field=models.DecimalField(
                decimal_places=2,
                default=0.0,
                help_text="Cumulative sum of all claim payouts.",
                max_digits=12,
                validators=[django.core.validators.MinValueValidator(0)],
            ),
        ),
    ]
