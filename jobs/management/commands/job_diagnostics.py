from django.core.management.base import BaseCommand
from django.db import connection

from jobs.forms import JobForm
from jobs.models import Company, Job, UserJobApproval


class Command(BaseCommand):
    help = 'Read-only production diagnostics for the ChuoSmart job-posting subsystem.'

    def add_arguments(self, parser):
        parser.add_argument('--recent', type=int, default=10)
        parser.add_argument('--user-id', type=int, default=None)

    def handle(self, *args, **options):
        tables = set(connection.introspection.table_names())
        required_tables = {
            Job._meta.db_table,
            Company._meta.db_table,
            UserJobApproval._meta.db_table,
            'core_newsletterjob',
        }
        missing = sorted(required_tables - tables)
        self.stdout.write(f'DATABASE={connection.vendor}')
        self.stdout.write(f'MISSING_REQUIRED_TABLES={missing}')
        self.stdout.write(f'JOB_COUNT={Job.objects.count()}')
        self.stdout.write(f'ACTIVE_JOB_COUNT={Job.objects.filter(is_active=True).count()}')
        self.stdout.write(f'PUBLIC_JOB_COUNT={Job.public_queryset().count()}')
        self.stdout.write(f'VERIFIED_COMPANIES={Company.objects.filter(is_verified=True).count()}')
        self.stdout.write(f'APPROVED_JOB_POSTERS={UserJobApproval.objects.filter(is_approved=True).count()}')

        form = JobForm()
        required_fields = sorted(name for name, field in form.fields.items() if field.required)
        self.stdout.write(f'JOB_FORM_REQUIRED_FIELDS={required_fields}')
        self.stdout.write('JOB_FORM_DEFAULT_CURRENCY=TZS')
        self.stdout.write('JOB_FORM_DEFAULT_POSTING_TYPE=internal')

        user_id = options.get('user_id')
        if user_id:
            approval = UserJobApproval.objects.filter(user_id=user_id).first()
            companies = Company.objects.filter(created_by_id=user_id)
            self.stdout.write(f'USER_ID={user_id}')
            self.stdout.write(f'USER_APPROVED={bool(approval and approval.is_approved)}')
            self.stdout.write(f'USER_COMPANIES={companies.count()}')
            self.stdout.write(f'USER_VERIFIED_COMPANIES={companies.filter(is_verified=True).count()}')
            self.stdout.write(f'USER_JOBS={Job.objects.filter(created_by_id=user_id).count()}')

        recent = max(0, min(options['recent'], 50))
        self.stdout.write('RECENT_JOBS:')
        for job in Job.objects.select_related('company', 'created_by').order_by('-posted_date')[:recent]:
            self.stdout.write(
                '  id={id} user={user} company={company} active={active} public={public} title={title}'.format(
                    id=job.pk,
                    user=job.created_by_id,
                    company=job.company_id or '-',
                    active=job.is_active,
                    public=job.is_public,
                    title=(job.title or '')[:80],
                )
            )

        if missing:
            self.stderr.write(self.style.ERROR('Job diagnostics found missing database tables.'))
            return
        self.stdout.write(self.style.SUCCESS('Job diagnostics completed without structural errors.'))
