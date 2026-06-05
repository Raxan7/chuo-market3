from django.db import migrations, models
from django.db.models import Case, Count, IntegerField, Q, When


def archive_duplicate_module_quizzes(apps, schema_editor):
    Quiz = apps.get_model('lms', 'Quiz')

    duplicate_groups = (
        Quiz.objects
        .filter(module__isnull=False, draft=False)
        .values('module_id', 'generated_for_id')
        .annotate(total=Count('id'))
        .filter(total__gt=1)
    )

    for group in duplicate_groups:
        quizzes = (
            Quiz.objects
            .filter(
                module_id=group['module_id'],
                generated_for_id=group['generated_for_id'],
                draft=False,
            )
            .annotate(
                question_count=Count('questions'),
                ready_rank=Case(
                    When(generation_status='ready', then=1),
                    default=0,
                    output_field=IntegerField(),
                ),
            )
            .order_by('-ready_rank', '-question_count', 'id')
        )
        keep = quizzes.first()
        if keep:
            quizzes.exclude(pk=keep.pk).update(
                draft=True,
                generation_message='Archived duplicate AI module quiz during LMS cleanup.',
            )


class Migration(migrations.Migration):

    dependencies = [
        ('lms', '0022_alter_quiz_slug_length'),
    ]

    operations = [
        migrations.RunPython(archive_duplicate_module_quizzes, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name='quiz',
            constraint=models.UniqueConstraint(
                fields=('module', 'generated_for'),
                condition=Q(draft=False, generated_for__isnull=False, module__isnull=False),
                name='unique_personal_ai_quiz_per_module_student',
            ),
        ),
        migrations.AddConstraint(
            model_name='quiz',
            constraint=models.UniqueConstraint(
                fields=('module',),
                condition=Q(draft=False, generated_for__isnull=True, module__isnull=False),
                name='unique_shared_ai_quiz_per_module',
            ),
        ),
    ]
