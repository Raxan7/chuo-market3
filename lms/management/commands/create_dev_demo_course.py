"""
Management command to create 10 development demo courses for testing
module access behaviors (free skip_assessment, paid modules, sequential gating).

Usage:
    python manage.py create_dev_demo_course
"""

from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from lms.models import Course, CourseContent, CourseModule, LMSProfile


def _get_or_create_instructor():
    user, _ = User.objects.get_or_create(
        username='dev_instructor',
        defaults={'email': 'instructor@dev.local', 'first_name': 'Dev', 'last_name': 'Instructor'},
    )
    user.set_password('instructor123')
    user.save()
    profile, _ = LMSProfile.objects.get_or_create(user=user, defaults={'role': 'instructor'})
    if profile.role != 'instructor':
        profile.role = 'instructor'
        profile.save(update_fields=['role'])
    return profile


COURSES = [
    {
        "title": "Dev 1: Free Overview + Paid Modules",
        "summary": "Classic layout: one free overview, then paid modules.",
        "price": 50000,
        "modules": [
            ("Introduction to Course", 0, None, True),
            ("Fundamentals", 1, 20000, False),
            ("Intermediate Topics", 2, 15000, False),
            ("Advanced Topics", 3, 15000, False),
        ],
    },
    {
        "title": "Dev 2: All Paid — No Free Module",
        "summary": "All modules have a price, no skip_assessment.",
        "price": 60000,
        "modules": [
            ("Getting Started", 0, 10000, False),
            ("Core Concepts", 1, 20000, False),
            ("Practical Projects", 2, 20000, False),
        ],
    },
    {
        "title": "Dev 3: Free Overview at the Middle",
        "summary": "A skip_assessment module appears in the middle of paid modules.",
        "price": 45000,
        "modules": [
            ("Part 1: Basics", 0, 15000, False),
            ("Part 2: Intermediate", 1, 15000, False),
            ("Bonus: Quick Recap (skip assessment)", 2, None, True),
            ("Part 3: Advanced", 3, 20000, False),
        ],
    },
    {
        "title": "Dev 4: Single Free Module Only",
        "summary": "One free skip_assessment module, no paid modules.",
        "price": 0,
        "modules": [
            ("Introduction (skip assessment)", 0, None, True),
        ],
    },
    {
        "title": "Dev 5: Multiple Free Modules",
        "summary": "Two free overview modules followed by paid ones.",
        "price": 40000,
        "modules": [
            ("Welcome (skip assessment)", 0, None, True),
            ("Course Roadmap (skip assessment)", 1, None, True),
            ("Module 1: First Paid Lesson", 2, 15000, False),
            ("Module 2: Second Paid Lesson", 3, 15000, False),
        ],
    },
    {
        "title": "Dev 6: Free Overview + Chain of Paid",
        "summary": "One free overview, then a long chain of paid modules.",
        "price": 80000,
        "modules": [
            ("Course Overview (skip assessment)", 0, None, True),
            ("Week 1", 1, 10000, False),
            ("Week 2", 2, 10000, False),
            ("Week 3", 3, 10000, False),
            ("Week 4", 4, 10000, False),
            ("Week 5", 5, 10000, False),
        ],
    },
    {
        "title": "Dev 7: Expensive Course",
        "summary": "Higher priced modules for premium feel.",
        "price": 200000,
        "modules": [
            ("Introduction (skip assessment)", 0, None, True),
            ("Foundation Module", 1, 80000, False),
            ("Expert Module", 2, 100000, False),
        ],
    },
    {
        "title": "Dev 8: Cheap Course",
        "summary": "Low-cost modules for budget testing.",
        "price": 15000,
        "modules": [
            ("What You Will Learn (skip assessment)", 0, None, True),
            ("Lesson 1", 1, 5000, False),
            ("Lesson 2", 2, 5000, False),
            ("Lesson 3", 3, 5000, False),
        ],
    },
    {
        "title": "Dev 9: Free Module Last",
        "summary": "Skip_assessment module placed at the end.",
        "price": 50000,
        "modules": [
            ("Part 1: Fundamentals", 0, 20000, False),
            ("Part 2: Practice", 1, 20000, False),
            ("Part 3: Summary & Review (skip assessment)", 2, None, True),
        ],
    },
    {
        "title": "Dev 10: Free + Paid Alternating",
        "summary": "Alternating free and paid modules.",
        "price": 60000,
        "modules": [
            ("Overview (skip assessment)", 0, None, True),
            ("Deep Dive 1", 1, 15000, False),
            ("Bonus Recap (skip assessment)", 2, None, True),
            ("Deep Dive 2", 3, 15000, False),
            ("Bonus Recap 2 (skip assessment)", 4, None, True),
            ("Final Project", 5, 20000, False),
        ],
    },
]


class Command(BaseCommand):
    help = 'Creates 10 development demo courses to test module access behaviors'

    def handle(self, *args, **kwargs):
        instructor = _get_or_create_instructor()
        self.stdout.write(f"Instructor: {instructor.user.username} (id={instructor.id})")

        created = 0
        skipped = 0

        for i, spec in enumerate(COURSES, 1):
            title = spec["title"]
            if Course.objects.filter(title=title).exists():
                skipped += 1
                continue

            course = Course.objects.create(
                title=title,
                slug=slugify(title) + "-dev",
                course_type="general",
                is_free=spec["price"] == 0,
                price=Decimal(str(spec["price"])),
                summary=spec["summary"],
                content="<p>Development demo course for testing module access.</p>",
            )
            course.instructors.add(instructor)

            for mod_title, order, price, skip in spec["modules"]:
                mod = CourseModule.objects.create(
                    course=course,
                    title=mod_title,
                    description=f"<p>Module content for {mod_title}.</p>",
                    order=order,
                    price=Decimal(str(price)) if price else None,
                    skip_assessment=skip,
                )
                CourseContent.objects.create(
                    title=f"{mod_title} — Lesson 1",
                    module=mod,
                    content_type="text",
                    text_content=f"Content for {mod_title}.",
                    order=0,
                )
                if not skip:
                    CourseContent.objects.create(
                        title=f"{mod_title} — Lesson 2",
                        module=mod,
                        content_type="text",
                        text_content=f"Additional content for {mod_title}.",
                        order=1,
                    )

            created += 1
            modules = CourseModule.objects.filter(course=course).count()
            self.stdout.write(f"  {i}/10  {title}  ({modules} modules)")

        self.stdout.write(self.style.SUCCESS(
            f"\nDone: {created} course(s) created, {skipped} already existed."
        ))
