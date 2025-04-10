# Generated by Django 4.1.9 on 2023-06-23 16:30

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Resume",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("path", models.TextField(max_length=100)),
                ("name", models.TextField(max_length=255)),
                ("phone", models.TextField(max_length=20)),
                ("email", models.TextField()),
                ("skills", django.contrib.postgres.fields.ArrayField(base_field=models.TextField(), size=None)),
                ("educations", django.contrib.postgres.fields.ArrayField(base_field=models.TextField(), size=None)),
            ],
        ),
    ]
