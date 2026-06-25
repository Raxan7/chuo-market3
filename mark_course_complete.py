import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Commerce.settings')
sys.path.insert(0, os.path.dirname(__file__))
django.setup()

from django.contrib.auth import get_user_model
from lms.models import ModuleProgress, StudentCertificate, CertificateTemplate
from lms.utils import issue_certificate_if_eligible

User = get_user_model()

# Configuration — change these as needed
USERNAME = 'saidi'
COURSE_SLUG = 'kozi-ya-usafirishaji-wa-bidhaa-kwa-njia-za-ardhi-a'

try:
    user = User.objects.get(username=USERNAME)
except User.DoesNotExist:
    print(f'Error: User "{USERNAME}" not found')
    sys.exit(1)

profile = getattr(user, 'lms_profile', None)
if not profile:
    print(f'Error: User "{USERNAME}" has no LMS profile')
    sys.exit(1)

from lms.models import Course
try:
    course = Course.objects.get(slug=COURSE_SLUG)
except Course.DoesNotExist:
    courses = Course.objects.filter(slug__startswith='kozi')[:10]
    print(f'Error: Course with slug "{COURSE_SLUG}" not found')
    print('Available courses:')
    for c in courses:
        print(f'  {c.id}: {c.slug} — {c.title}')
    sys.exit(1)

# Ensure legal name is set
if not profile.has_legal_name:
    profile.legal_name = user.get_full_name() or user.username
    profile.save()
    print(f'Set legal name to: "{profile.legal_name}"')

modules = list(course.modules.order_by('order', 'id'))
if not modules:
    print(f'Error: Course "{course.title}" has no modules')
    sys.exit(1)

print(f'User: {user.username} (ID: {user.id})')
print(f'Course: {course.title} (slug: {course.slug})')
print(f'Modules: {len(modules)}')

# Mark all modules complete
for mod in modules:
    mp, created = ModuleProgress.objects.get_or_create(
        student=profile,
        module=mod,
        defaults={
            'content_completed': True,
            'assessment_passed': True,
            'best_score': 100,
        }
    )
    if not created:
        mp.content_completed = True
        mp.assessment_passed = True
        mp.best_score = 100
    mp.refresh_completion(save=True)
    print(f'  Module "{mod.title}" -> completed')

# Set a default template if none exists
template = CertificateTemplate.objects.filter(course=course).first()
if not template:
    instructor = course.instructors.first()
    instructor_name = 'Course Instructor'
    if instructor:
        instructor_name = (
            instructor.display_legal_name
            or instructor.user.get_full_name()
            or instructor.user.username
        )
    template = CertificateTemplate.objects.create(
        course=course,
        title='Certificate of Completion',
        organization_name='ChuoSmart Academy',
        primary_color='#0d6efd',
        secondary_color='#111827',
        accent_color='#1FAA59',
        instructor_name=instructor_name,
        status='active',
    )
    print(f'Created certificate template: "{template.title}"')

# Issue certificate
cert = issue_certificate_if_eligible(course, profile)
if cert:
    print(f'Certificate issued: {cert.certificate_id}')
    print(f'View at: /lms/certificates/{cert.certificate_id}/')
else:
    print('Certificate could not be issued (check student legal name & instructor names)')
