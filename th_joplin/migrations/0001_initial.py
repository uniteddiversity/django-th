# Generated by Django 2.1.5 on 2019-02-05 09:27

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('django_th', '0013_auto_20171127_2122'),
    ]

    operations = [
        migrations.CreateModel(
            name='Joplin',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('status', models.BooleanField(default=False)),
                ('description', models.CharField(max_length=255)),
                ('folder', models.TextField()),
                ('trigger', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='django_th.TriggerService')),
            ],
            options={
                'db_table': 'django_th_joplin',
            },
        ),
    ]
