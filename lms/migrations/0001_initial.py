# Generated by Django 4.2.20 on 2025-06-25 07:00

from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ActivityLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('message', models.TextField()),
            ],
            options={
                'ordering': ['-timestamp'],
            },
        ),
        migrations.CreateModel(
            name='Choice',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content', models.TextField(help_text='Enter the choice text that you want displayed')),
                ('correct', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='Course',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('slug', models.SlugField(blank=True, unique=True)),
                ('code', models.CharField(max_length=20, unique=True)),
                ('credit', models.IntegerField(default=3)),
                ('summary', models.TextField(blank=True)),
                ('level', models.CharField(choices=[('1', 'Level 1'), ('2', 'Level 2'), ('3', 'Level 3'), ('4', 'Level 4'), ('5', 'Level 5'), ('6', 'Level 6')], max_length=2)),
                ('year', models.IntegerField(choices=[(1, 'First'), (2, 'Second'), (3, 'Third'), (4, 'Fourth'), (5, 'Fifth'), (6, 'Sixth')], default=1)),
                ('semester', models.CharField(choices=[('First', 'First'), ('Second', 'Second')], max_length=10)),
                ('is_elective', models.BooleanField(default=False)),
                ('image', models.ImageField(blank=True, null=True, upload_to='lms/course_images/')),
            ],
        ),
        migrations.CreateModel(
            name='CourseModule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('description', models.TextField(blank=True)),
                ('order', models.PositiveIntegerField(default=0)),
                ('course', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='modules', to='lms.course')),
            ],
            options={
                'ordering': ['order'],
            },
        ),
        migrations.CreateModel(
            name='LMSProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(choices=[('student', 'Student'), ('instructor', 'Instructor'), ('admin', 'Administrator')], default='student', max_length=10)),
                ('bio', models.TextField(blank=True, null=True)),
                ('profile_picture', models.ImageField(blank=True, null=True, upload_to='lms/profile_pictures/')),
                ('phone_number', models.CharField(blank=True, max_length=15, null=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='lms_profile', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Program',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=150, unique=True)),
                ('summary', models.TextField(blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='Question',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('figure', models.ImageField(blank=True, null=True, upload_to='lms/quiz_figures')),
                ('content', models.TextField(help_text='Enter the question text')),
                ('explanation', models.TextField(blank=True, help_text='Explanation to be shown after the question has been answered.')),
                ('order', models.IntegerField(default=0)),
            ],
            options={
                'ordering': ['order'],
            },
        ),
        migrations.CreateModel(
            name='Quiz',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=60, verbose_name='Title')),
                ('slug', models.SlugField(blank=True, unique=True)),
                ('description', models.TextField(blank=True, help_text='A detailed description of the quiz', verbose_name='Description')),
                ('category', models.CharField(blank=True, choices=[('assignment', 'Assignment'), ('exam', 'Exam'), ('practice', 'Practice Quiz')], max_length=20)),
                ('random_order', models.BooleanField(default=False, help_text='Display the questions in a random order or as they are set?', verbose_name='Random Order')),
                ('answers_at_end', models.BooleanField(default=False, help_text='Correct answer is NOT shown after question. Answers displayed at the end.', verbose_name='Answers at end')),
                ('exam_paper', models.BooleanField(default=False, help_text='If yes, the result of each attempt by a user will be stored. Necessary for marking.', verbose_name='Exam Paper')),
                ('single_attempt', models.BooleanField(default=False, help_text='If yes, only one attempt by a user will be permitted.', verbose_name='Single Attempt')),
                ('pass_mark', models.SmallIntegerField(default=50, help_text='Percentage required to pass exam.', validators=[django.core.validators.MaxValueValidator(100)], verbose_name='Pass Mark')),
                ('draft', models.BooleanField(default=False, help_text='If yes, the quiz is not displayed in the quiz list and can only be taken by users who can edit quizzes.', verbose_name='Draft')),
                ('due_date', models.DateTimeField(blank=True, null=True)),
                ('timestamp', models.DateTimeField(auto_now=True)),
                ('course', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='lms.course')),
                ('module', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='quizzes', to='lms.coursemodule')),
            ],
            options={
                'verbose_name': 'Quiz',
                'verbose_name_plural': 'Quizzes',
                'ordering': ['course', 'title'],
            },
        ),
        migrations.CreateModel(
            name='QuizTaker',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('score', models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ('completed', models.BooleanField(default=False)),
                ('date_started', models.DateTimeField(auto_now_add=True)),
                ('date_completed', models.DateTimeField(blank=True, null=True)),
                ('quiz', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='lms.quiz')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='lms.lmsprofile')),
            ],
            options={
                'unique_together': {('user', 'quiz')},
            },
        ),
        migrations.CreateModel(
            name='Essay_Question',
            fields=[
                ('question_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='lms.question')),
                ('answer_type', models.CharField(choices=[('text', 'Text'), ('file_upload', 'File Upload'), ('both', 'Both')], default='text', max_length=20)),
            ],
            bases=('lms.question',),
        ),
        migrations.CreateModel(
            name='MCQuestion',
            fields=[
                ('question_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='lms.question')),
                ('choice_order', models.CharField(blank=True, choices=[('content', 'Content'), ('random', 'Random'), ('none', 'None')], help_text='The order in which multichoice choice options are displayed', max_length=30, null=True)),
            ],
            bases=('lms.question',),
        ),
        migrations.CreateModel(
            name='TF_Question',
            fields=[
                ('question_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='lms.question')),
                ('correct', models.BooleanField(default=False)),
            ],
            bases=('lms.question',),
        ),
        migrations.CreateModel(
            name='Semester',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('year', models.IntegerField(choices=[(1, 'First'), (2, 'Second'), (3, 'Third'), (4, 'Fourth'), (5, 'Fifth'), (6, 'Sixth')], default=1)),
                ('semester', models.CharField(choices=[('First', 'First'), ('Second', 'Second')], default='First', max_length=10)),
                ('is_current_semester', models.BooleanField(default=False)),
            ],
            options={
                'unique_together': {('semester', 'year')},
            },
        ),
        migrations.AddField(
            model_name='question',
            name='quiz',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='questions', to='lms.quiz'),
        ),
        migrations.CreateModel(
            name='CourseEnrollment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_enrolled', models.DateTimeField(auto_now_add=True)),
                ('course', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='lms.course')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='lms.lmsprofile')),
            ],
            options={
                'unique_together': {('student', 'course')},
            },
        ),
        migrations.CreateModel(
            name='CourseContent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('content_type', models.CharField(choices=[('document', 'Document'), ('video', 'Video'), ('link', 'External Link'), ('text', 'Text Content')], max_length=10)),
                ('document', models.FileField(blank=True, null=True, upload_to='lms/course_documents/', validators=[django.core.validators.FileExtensionValidator(allowed_extensions=['pdf', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx', 'txt'])])),
                ('video_url', models.URLField(blank=True, null=True)),
                ('external_link', models.URLField(blank=True, null=True)),
                ('text_content', models.TextField(blank=True, null=True)),
                ('order', models.PositiveIntegerField(default=0)),
                ('date_added', models.DateTimeField(auto_now_add=True)),
                ('module', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='contents', to='lms.coursemodule')),
            ],
            options={
                'ordering': ['order'],
            },
        ),
        migrations.AddField(
            model_name='course',
            name='instructors',
            field=models.ManyToManyField(limit_choices_to={'role': 'instructor'}, related_name='courses_teaching', to='lms.lmsprofile'),
        ),
        migrations.AddField(
            model_name='course',
            name='program',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='lms.program'),
        ),
        migrations.AddField(
            model_name='course',
            name='students',
            field=models.ManyToManyField(related_name='courses_enrolled', through='lms.CourseEnrollment', to='lms.lmsprofile'),
        ),
        migrations.CreateModel(
            name='StudentAnswer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tf_answer', models.BooleanField(blank=True, null=True)),
                ('essay_text_answer', models.TextField(blank=True, null=True)),
                ('essay_file_answer', models.FileField(blank=True, null=True, upload_to='lms/essay_answers/')),
                ('is_correct', models.BooleanField(default=False)),
                ('mc_answer', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='lms.choice')),
                ('question', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='lms.question')),
                ('quiz_taker', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='answers', to='lms.quiztaker')),
            ],
            options={
                'unique_together': {('quiz_taker', 'question')},
            },
        ),
        migrations.CreateModel(
            name='Grade',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('attendance', models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ('assignment', models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ('mid_exam', models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ('final_exam', models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ('total', models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ('grade', models.CharField(blank=True, max_length=5, null=True)),
                ('comment', models.TextField(blank=True, null=True)),
                ('course', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='lms.course')),
                ('semester', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='lms.semester')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='lms.lmsprofile')),
            ],
            options={
                'unique_together': {('student', 'course', 'semester')},
            },
        ),
        migrations.AddField(
            model_name='choice',
            name='question',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='choices', to='lms.mcquestion'),
        ),
    ]
