from django.core.management.base import BaseCommand
from jobs.models import Industry

class Command(BaseCommand):
    help = 'Populate the database with common industry categories'

    def handle(self, *args, **options):
        industries = [
            # Technology & IT
            'Information Technology',
            'Software Development',
            'Web Development',
            'Mobile App Development',
            'Data Science & Analytics',
            'Cybersecurity',
            'Cloud Computing',
            'Artificial Intelligence',
            'Machine Learning',
            'Blockchain',
            'Internet of Things (IoT)',

            # Business & Finance
            'Finance',
            'Banking',
            'Investment',
            'Accounting',
            'Financial Services',
            'Insurance',
            'Consulting',
            'Business Development',
            'Management Consulting',
            'Strategy',
            'Operations',

            # Marketing & Sales
            'Marketing',
            'Digital Marketing',
            'Content Marketing',
            'Social Media Marketing',
            'SEO/SEM',
            'Advertising',
            'Public Relations',
            'Sales',
            'Business Development',
            'Customer Success',

            # Healthcare & Medical
            'Healthcare',
            'Medical',
            'Pharmaceutical',
            'Biotechnology',
            'Nursing',
            'Medical Research',
            'Healthcare Administration',
            'Mental Health',
            'Dental',
            'Veterinary',

            # Education & Training
            'Education',
            'Higher Education',
            'K-12 Education',
            'E-Learning',
            'Training & Development',
            'Teaching',
            'Educational Technology',
            'Academic Research',

            # Engineering & Manufacturing
            'Engineering',
            'Mechanical Engineering',
            'Electrical Engineering',
            'Civil Engineering',
            'Chemical Engineering',
            'Manufacturing',
            'Automotive',
            'Aerospace',
            'Construction',
            'Architecture',

            # Creative & Design
            'Design',
            'Graphic Design',
            'UX/UI Design',
            'Product Design',
            'Fashion Design',
            'Interior Design',
            'Photography',
            'Video Production',
            'Creative Services',

            # Legal & Government
            'Legal',
            'Law',
            'Government',
            'Public Administration',
            'Non-Profit',
            'International Relations',
            'Policy',

            # Hospitality & Tourism
            'Hospitality',
            'Tourism',
            'Hotel Management',
            'Restaurant',
            'Travel',
            'Event Planning',
            'Entertainment',

            # Retail & Consumer Goods
            'Retail',
            'E-commerce',
            'Consumer Goods',
            'Fashion',
            'Food & Beverage',
            'Luxury Goods',
            'Wholesale',

            # Energy & Utilities
            'Energy',
            'Oil & Gas',
            'Renewable Energy',
            'Utilities',
            'Environmental',
            'Sustainability',

            # Transportation & Logistics
            'Transportation',
            'Logistics',
            'Supply Chain',
            'Shipping',
            'Aviation',
            'Railway',
            'Automotive',

            # Real Estate
            'Real Estate',
            'Property Management',
            'Construction',
            'Architecture',
            'Urban Planning',

            # Media & Communications
            'Media',
            'Journalism',
            'Publishing',
            'Broadcasting',
            'Communications',
            'Public Relations',
            'Advertising',

            # Agriculture & Food
            'Agriculture',
            'Farming',
            'Food Production',
            'Agribusiness',
            'Fisheries',
            'Forestry',

            # Other Industries
            'Telecommunications',
            'Mining',
            'Chemicals',
            'Pharmaceuticals',
            'Textiles',
            'Sports & Recreation',
            'Security',
            'Human Resources',
            'Quality Assurance',
            'Research & Development',
        ]

        created_count = 0
        for industry_name in industries:
            industry, created = Industry.objects.get_or_create(
                name=industry_name,
                defaults={'name': industry_name}
            )
            if created:
                created_count += 1
                self.stdout.write(f'Created industry: {industry_name}')

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {created_count} industries. '
                f'Total industries in database: {Industry.objects.count()}'
            )
        )