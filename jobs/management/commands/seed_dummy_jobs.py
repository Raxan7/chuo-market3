from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from jobs.models import Job, Company, Industry, UserJobApproval
import random
from datetime import timedelta

JOB_TITLES = [
    "Software Engineer", "Data Analyst", "Graphic Designer", "Accountant",
    "Marketing Manager", "Sales Representative", "Customer Support Specialist",
    "Human Resources Officer", "Project Manager", "Business Analyst",
    "Web Developer", "Content Writer", "Social Media Manager", "Office Administrator",
    "Financial Analyst", "Operations Manager", "IT Support Technician",
    "Public Relations Officer", "Supply Chain Manager", "Quality Assurance Analyst",
    "Mobile App Developer", "DevOps Engineer", "UI/UX Designer", "Database Administrator",
    "Network Engineer", "Security Analyst", "Product Manager", "Scrum Master",
    "Technical Writer", "Digital Marketing Specialist", "Brand Manager",
    "Internal Auditor", "Tax Accountant", "Payroll Specialist", "Recruitment Officer",
    "Training Coordinator", "Legal Advisor", "Compliance Officer", "Risk Analyst",
    "Investment Analyst", "Procurement Officer", "Logistics Coordinator",
    "Warehouse Manager", "Export Manager", "Import Specialist", "Farm Manager",
    "Agronomist", "Environmental Officer", "Civil Engineer", "Electrical Engineer",
    "Mechanical Engineer", "Architect", "Quantity Surveyor", "Site Supervisor",
    "Health Safety Officer", "Medical Officer", "Nurse", "Pharmacist",
    "Laboratory Technician", "Radiographer", "Physiotherapist", "Dentist",
    "Veterinary Officer", "Research Scientist", "Laboratory Manager",
    "University Lecturer", "Secondary Teacher", "Primary Teacher", "Kindergarten Teacher",
    "School Principal", "Education Officer", "Curriculum Developer", "Librarian",
    "Journalist", "Editor", "News Anchor", "Radio Presenter", "Video Editor",
    "Photographer", "Film Director", "Animator", "Game Developer",
    "Chef", "Restaurant Manager", "Hotel Manager", "Tour Guide",
    "Travel Agent", "Event Coordinator", "Catering Manager", "Housekeeping Supervisor",
    "Fitness Instructor", "Sports Coach", "Athletic Trainer", "Yoga Instructor",
    "Social Worker", "Counselor", "Psychologist", "Community Development Officer",
    "NGO Program Manager", "Grant Writer", "Monitoring Evaluation Officer"
]

LOCATIONS = [
    "Dar es Salaam", "Arusha", "Mwanza", "Dodoma", "Mbeya",
    "Zanzibar", "Tanga", "Morogoro", "Kilimanjaro", "Iringa",
    "Tabora", "Kigoma", "Mtwara", "Lindi", "Singida",
    "Rukwa", "Ruvuma", "Shinyanga", "Manyara", "Pwani",
    "Dar es Salaam", "Dar es Salaam", "Arusha", "Mwanza", "Mbeya"
]

COMPANIES = [
    "Tech Tanzania Ltd", "AfriTech Solutions", "Dar Es Salaam Digital",
    "Serengeti Innovations", "Kilimanjaro Tech Hub", "Zanzibar Software House",
    "Tanzania Data Systems", "East African Cloud Services", "Crypto Africa Ltd",
    "Smart Tanzania", "Digital Dar Solutions", "Arusha Tech Park",
    "Mwanza Digital Services", "Tanga IT Solutions", "Morogoro Tech Labs",
    "Blue Ocean Financial Services", "Tanzania Investment Bank",
    "Dar Es Salaam Stock Exchange", "Microfinance Tanzania Ltd",
    "Equity Bank Tanzania", "CRDB Bank", "NMB Bank Plc",
    "National Microfinance Bank", "Tanzania Postal Bank", "Azania Bank",
    "Mount Meru Hospital", "Kilimanjaro Medical Centre", "Dar Es Salaam Health Services",
    "Aga Khan Hospital", "Muhimbili Medical Centre", "Tanzania Health Partners",
    "Green Agri Tanzania", "Kilimo Bora Ltd", "Tanzania Farming Corp",
    "Serengeti Agric Solutions", "Harvest Tanzania Ltd", "Organic Farms Ltd",
    "East African Construction", "Tanzania Builders Ltd", "Dar Construction Co",
    "Serengeti Infrastructure", "Kilimanjaro Construction", "Tanzania Road Works",
    "Safari Hotels Tanzania", "Serengeti Lodge", "Zanzibar Beach Resort",
    "Kilimanjaro Mountain Hotel", "Dar Es Salaam Serena", "Tanzania Tourism Board",
    "Global Education Tanzania", "Dar Es Salaam International School",
    "Tanzania Education Trust", "Mount Meru Academy", "Arusha Learning Centre"
]

DESCRIPTION_TEMPLATES = [
    "<p>We are looking for a talented {title} to join our team in {location}.</p>"
    "<p>This is an exciting opportunity to work with a dynamic organization that values innovation and growth.</p>"
    "<h4>Key Responsibilities:</h4>"
    "<ul><li>Plan and execute daily tasks according to company guidelines</li>"
    "<li>Collaborate with cross-functional teams to achieve organizational goals</li>"
    "<li>Prepare reports and maintain documentation</li>"
    "<li>Ensure compliance with company policies and procedures</li>"
    "<li>Contribute to team meetings and planning sessions</li></ul>"
    "<h4>Qualifications:</h4>"
    "<ul><li>Bachelor's degree in relevant field</li>"
    "<li>Minimum 2 years of relevant experience</li>"
    "<li>Strong communication and interpersonal skills</li>"
    "<li>Ability to work both independently and as part of a team</li>"
    "<li>Proficiency in Microsoft Office Suite</li></ul>",

    "<p>{title} position available at our {location} office.</p>"
    "<p>We are seeking a motivated professional ready to make an impact.</p>"
    "<h4>What You'll Do:</h4>"
    "<ul><li>Manage day-to-day operations in your area of expertise</li>"
    "<li>Develop strategies to improve efficiency and productivity</li>"
    "<li>Train and mentor junior team members</li>"
    "<li>Monitor project timelines and deliverables</li></ul>"
    "<h4>What We're Looking For:</h4>"
    "<ul><li>Relevant degree or equivalent experience</li>"
    "<li>Strong problem-solving abilities</li>"
    "<li>Excellent organizational skills</li>"
    "<li>Fluency in English and Swahili</li></ul>",

    "<p>Join our growing team as a {title} based in {location}.</p>"
    "<p>This role offers great potential for career growth and professional development.</p>"
    "<h4>Role Description:</h4>"
    "<ul><li>Execute assigned tasks efficiently and accurately</li>"
    "<li>Support senior team members in project delivery</li>"
    "<li>Maintain accurate records and documentation</li>"
    "<li>Participate in continuous improvement initiatives</li></ul>"
    "<h4>Requirements:</h4>"
    "<ul><li>Diploma or degree in relevant field</li>"
    "<li>1-3 years of working experience</li>"
    "<li>Good communication skills</li>"
    "<li>Computer literacy</li></ul>",

    "<p>Excellent career opportunity for a {title} in {location}.</p>"
    "<p>Our company is expanding and we need talented individuals to grow with us.</p>"
    "<h4>Main Duties:</h4>"
    "<ul><li>Handle daily operational responsibilities</li>"
    "<li>Work closely with department heads</li>"
    "<li>Implement best practices and standard operating procedures</li>"
    "<li>Assist in budgeting and resource planning</li></ul>"
    "<h4>Required Skills:</h4>"
    "<ul><li>Relevant academic background</li>"
    "<li>Strong analytical skills</li>"
    "<li>Team player with positive attitude</li>"
    "<li>Attention to detail</li></ul>"
]


class Command(BaseCommand):
    help = "Seed 1000+ dummy jobs for testing the job listing page"

    def add_arguments(self, parser):
        parser.add_argument('--count', type=int, default=1200,
                            help='Number of dummy jobs to create (default: 1200)')

    def handle(self, *args, **options):
        count = options['count']

        # Ensure a superuser exists to own the jobs
        admin, created = User.objects.get_or_create(
            username='jobseeder',
            defaults={
                'email': 'seeder@chuosmart.co.tz',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        if created:
            admin.set_password('seeder123')
            admin.save()
            self.stdout.write(self.style.SUCCESS(f'Created admin user: {admin.username}'))

        # Ensure job approval for the admin
        approval, created = UserJobApproval.objects.get_or_create(
            user=admin,
            defaults={
                'is_approved': True,
                'approved_by': admin,
                'approved_date': timezone.now(),
                'reason': 'Auto-approved for seeding',
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created job approval for {admin.username}'))
        elif not approval.is_approved:
            approval.is_approved = True
            approval.save()
            self.stdout.write(self.style.SUCCESS(f'Approved {admin.username} for job posting'))

        # Create industries if none exist
        industry_names = [
            "Technology", "Finance & Banking", "Healthcare", "Agriculture",
            "Construction", "Education", "Hospitality & Tourism", "Manufacturing",
            "Transport & Logistics", "Retail", "Energy", "Telecommunications",
            "Media & Communications", "Real Estate", "Mining", "Government",
            "Non-Profit", "Legal", "Consulting", "Entertainment"
        ]
        industries = {}
        for name in industry_names:
            ind, created = Industry.objects.get_or_create(name=name)
            industries[name] = ind
        self.stdout.write(self.style.SUCCESS(f'{len(industries)} industries ready'))

        # Create companies
        company_objects = []
        for name in COMPANIES:
            co, created = Company.objects.get_or_create(
                name=name,
                defaults={
                    'description': f'<p>{name} is a leading organization based in Tanzania.</p>',
                    'city': random.choice(LOCATIONS),
                    'country': 'Tanzania',
                    'created_by': admin,
                    'is_verified': True,
                }
            )
            company_objects.append(co)
        self.stdout.write(self.style.SUCCESS(f'{len(company_objects)} companies ready'))

        # Generate jobs
        job_types = ['full_time', 'part_time', 'contract', 'freelance', 'internship', 'volunteer']
        exp_levels = ['entry', 'mid', 'senior', 'executive']
        existing_count = Job.objects.filter(created_by=admin).count()
        needed = max(0, count - existing_count)

        if needed == 0:
            self.stdout.write(self.style.WARNING(
                f'Already have {existing_count} jobs from this seeder. '
                f'Use --count {existing_count + needed + 1} to add more.'
            ))
            return

        batch = []
        created_count = 0
        now = timezone.now()

        for i in range(needed):
            title = random.choice(JOB_TITLES)
            location = random.choice(LOCATIONS)
            company = random.choice(company_objects)
            industry = random.choice(list(industries.values()))
            job_type = random.choice(job_types)
            exp_level = random.choice(exp_levels)
            description = random.choice(DESCRIPTION_TEMPLATES).format(title=title, location=location)

            salary_min = random.choice([300000, 500000, 700000, 1000000, 1500000, 2000000, 0])
            salary_max = salary_min + random.choice([200000, 300000, 500000, 1000000]) if salary_min > 0 else None

            days_ago = random.randint(0, 60)
            posted = now - timedelta(days=days_ago)
            deadline = posted + timedelta(days=random.randint(14, 60))

            job = Job(
                title=title,
                description=description,
                company=company if random.random() > 0.3 else None,
                industry=industry,
                location=location,
                is_remote=random.random() < 0.25,
                salary_min=salary_min if salary_min > 0 else None,
                salary_max=salary_max,
                salary_currency='TZS',
                job_type=job_type,
                experience_level=exp_level,
                requirements='<p>See description above.</p>',
                responsibilities='<p>See description above.</p>',
                benefits='<p>Competitive salary and benefits package.</p>',
                application_deadline=deadline,
                posted_date=posted,
                is_active=True,
                is_featured=random.random() < 0.1,
                created_by=admin,
            )
            batch.append(job)
            created_count += 1

            if len(batch) >= 200:
                Job.objects.bulk_create(batch)
                self.stdout.write(self.style.SUCCESS(f'  Created {created_count} jobs so far...'))
                batch = []

        if batch:
            Job.objects.bulk_create(batch)
            self.stdout.write(self.style.SUCCESS(f'  Created {created_count} jobs so far...'))

        total = Job.objects.count()
        self.stdout.write(self.style.SUCCESS(
            f'\nDone! Created {created_count} new jobs. Total jobs in database: {total}'
        ))
        self.stdout.write(self.style.SUCCESS(
            f'Public queryset count: {Job.public_queryset().count()}'
        ))
