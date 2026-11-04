from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("userbot", "0002_images")]

    operations = [
        migrations.RenameField("message", "has_photo", "media_pending"),
        migrations.RenameField("message", "image", "media"),
    ]
