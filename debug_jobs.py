import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Commerce.settings')
django.setup()

from django.contrib.auth.models import User
from jobs.models import Job, UserJobApproval

print("=" * 50)
print("USER APPROVAL STATUS")
print("=" * 50)
users = User.objects.all()
for user in users:
    try:
        approval = user.job_approval
        print(f"✓ {user.username}: is_approved={approval.is_approved}")
    except UserJobApproval.DoesNotExist:
        print(f"✗ {user.username}: No UserJobApproval record")

print("\n" + "=" * 50)
print("JOBS VISIBILITY")
print("=" * 50)
jobs = Job.objects.all()
for job in jobs:
    print(f"Job: {job.title}")
    print(f"  - Created by: {job.created_by.username}")
    print(f"  - is_active: {job.is_active}")
    print(f"  - is_public: {job.is_public}")
    print(f"  - visibility_label: {job.visibility_label}")
    print()

print("=" * 50)
print("PUBLIC QUERYSET")
print("=" * 50)
public_jobs = Job.public_queryset()
print(f"Total public jobs: {public_jobs.count()}")
for job in public_jobs:
    print(f"  - {job.title}")
