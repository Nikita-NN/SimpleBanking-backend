# Generated by Django 5.0.5 on 2024-05-08 15:24

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('banking', '0003_transaction_internal'),
    ]

    operations = [
        migrations.AlterField(
            model_name='account',
            name='account_number',
            field=models.IntegerField(max_length=20, unique=True),
        ),
    ]
