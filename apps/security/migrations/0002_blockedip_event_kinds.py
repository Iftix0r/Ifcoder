from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("security", "0001_initial")]

    operations = [
        migrations.AlterField(
            model_name="event",
            name="kind",
            field=models.CharField(
                choices=[
                    ("login_ok", "Kirish"),
                    ("login_fail", "Xato parol"),
                    ("new_ip", "Sessiya yangi IP'dan"),
                    ("trap", "Skaner"),
                    ("leak", "Maxfiy fayl yuklandi"),
                    ("killed", "Sessiya yopildi"),
                    ("blocked", "IP bloklandi"),
                    ("rate_limit", "So'rov limiti"),
                ],
                db_index=True,
                max_length=10,
            ),
        ),
        migrations.CreateModel(
            name="BlockedIP",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("ip", models.CharField(db_index=True, max_length=45, unique=True)),
                ("reason", models.CharField(max_length=200)),
                ("hits", models.PositiveIntegerField(default=1)),
                ("expires_at", models.DateTimeField(db_index=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
