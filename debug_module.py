import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Commerce.settings')
django.setup()

from lms.models import CourseModule
from lms.ai_assessments import collect_module_learning_context

m = CourseModule.objects.get(id=47)
print(f"Module: {m.title}")
print(f"Course: {m.course.title}")
print(f"Skip assessment: {m.skip_assessment}")
print(f"Description: {m.description}")
print(f"Contents count: {m.contents.count()}")
for c in m.contents.all():
    print(f"  Content: {c.title} type={c.content_type}")
ctx = collect_module_learning_context(m)
print(f"\nContext ({len(ctx)} chars):")
print(ctx[:2000])
