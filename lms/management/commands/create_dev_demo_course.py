"""
Management command to create a development demo course for testing module access.

Creates a paid course with:
  - Module 1: skip_assessment=True (free, open to everyone, even without enrollment)
  - Module 2: paid module right after the free overview (requestable without enrollment)
  - Module 3+: more paid modules (sequential gating applies)

Usage:
    python manage.py create_dev_demo_course
"""

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils.text import slugify

from lms.models import Course, CourseContent, CourseModule


class Command(BaseCommand):
    help = 'Creates a development demo course to test free skip_assessment modules and module access requests'

    def handle(self, *args, **kwargs):
        title = 'Dev Demo: Free Overview + Paid Modules'
        if Course.objects.filter(title=title).exists():
            self.stdout.write(self.style.WARNING('Demo course already exists — skipping.'))
            return

        course = Course.objects.create(
            title=title,
            slug=slugify(title) + '-dev',
            course_type='general',
            is_free=False,
            price=Decimal('50000.00'),
            summary='Dev course: Module 1 is free (skip_assessment), later modules are paid.',
            content=(
                '<h3>Course Description</h3>'
                '<p>This course lets you verify that the first module is free and open to everyone, '
                'and that the following paid module shows a Request Access button.</p>'
            ),
        )

        overview = CourseModule.objects.create(
            course=course,
            title='Module 1: Free Overview (skip assessment)',
            description=(
                '<p>This module is free and open to everyone — no enrollment or payment needed.</p>'
            ),
            order=0,
            price=None,
            skip_assessment=True,
        )
        CourseContent.objects.create(
            title='Welcome to the free overview',
            module=overview,
            content_type='text',
            text_content='This free lesson is accessible without enrollment.',
            order=0,
        )
        CourseContent.objects.create(
            title='How module access works',
            module=overview,
            content_type='text',
            text_content='The next module is paid. You can request access to it individually.',
            order=1,
        )

        module2 = CourseModule.objects.create(
            course=course,
            title='Module 2: Paid Module (requestable)',
            description=(
                '<p>This module follows the free overview, so it must show a Request Access button.</p>'
            ),
            order=1,
            price=Decimal('20000.00'),
        )
        CourseContent.objects.create(
            title='Paid lesson 1',
            module=module2,
            content_type='text',
            text_content='Paid module content — locked until access is granted.',
            order=0,
        )

        for i in (3, 4):
            module = CourseModule.objects.create(
                course=course,
                title=f'Module {i}: Another Paid Module',
                description='<p>Sequential gating applies here — previous module must be completed.</p>',
                order=i,
                price=Decimal('15000.00'),
            )
            CourseContent.objects.create(
                title=f'Paid lesson {i}',
                module=module,
                content_type='text',
                text_content='Paid module content.',
                order=0,
            )

        self.stdout.write(self.style.SUCCESS(
            f'Created demo course "{course.title}" (id={course.id}, slug={course.slug}) '
            f'with {CourseModule.objects.filter(course=course).count()} modules.'
        ))
