from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lms', '0021_quiz_generated_for_quiz_generation_completed_at_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='quiz',
            name='slug',
            field=models.SlugField(blank=True, max_length=150, unique=True),
        ),
    ]