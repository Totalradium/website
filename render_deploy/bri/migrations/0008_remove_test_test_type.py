# Generated migration to remove test_type field

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bri', '0007_testsession_session_type'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='test',
            name='test_type',
        ),
    ]