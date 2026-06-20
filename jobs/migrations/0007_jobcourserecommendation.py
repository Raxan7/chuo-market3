from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('lms', '0029_course_created_at'),
        ('jobs', '0006_job_job_posting_type_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='JobCourseRecommendation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reasons', models.JSONField(blank=True, default=dict, help_text='Mapping of course_id to reason string', verbose_name='Recommendation reasons')),
                ('source', models.CharField(blank=True, choices=[('cerebras', 'Cerebras AI'), ('fallback', 'Fallback')], max_length=20, verbose_name='Recommendation source')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('courses', models.ManyToManyField(blank=True, related_name='job_recommendations', to='lms.Course')),
                ('job', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='course_recommendations', to='jobs.Job')),
            ],
            options={
                'verbose_name': 'Job Course Recommendation',
                'verbose_name_plural': 'Job Course Recommendations',
                'ordering': ['-updated_at'],
            },
        ),
    ]
