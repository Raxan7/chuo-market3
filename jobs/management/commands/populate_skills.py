from django.core.management.base import BaseCommand
from jobs.models import Skill

class Command(BaseCommand):
    help = 'Populate the database with common skills'

    def handle(self, *args, **options):
        skills = [
            # Programming Languages
            'Python', 'JavaScript', 'Java', 'C++', 'C#', 'PHP', 'Ruby', 'Go', 'Rust', 'Swift',
            'Kotlin', 'TypeScript', 'R', 'MATLAB', 'Scala', 'Perl', 'Shell Scripting',

            # Web Technologies
            'HTML', 'CSS', 'React', 'Angular', 'Vue.js', 'Node.js', 'Express.js', 'Django',
            'Flask', 'Spring Boot', 'ASP.NET', 'Laravel', 'Ruby on Rails', 'Next.js', 'Nuxt.js',

            # Databases
            'MySQL', 'PostgreSQL', 'MongoDB', 'Redis', 'SQLite', 'Oracle', 'SQL Server',
            'Cassandra', 'Elasticsearch', 'Firebase', 'DynamoDB',

            # Cloud & DevOps
            'AWS', 'Azure', 'Google Cloud', 'Docker', 'Kubernetes', 'Jenkins', 'GitLab CI',
            'GitHub Actions', 'Terraform', 'Ansible', 'Linux', 'Ubuntu', 'CentOS', 'Nginx', 'Apache',

            # Data Science & AI
            'Machine Learning', 'Deep Learning', 'TensorFlow', 'PyTorch', 'Scikit-learn',
            'Pandas', 'NumPy', 'Jupyter', 'Tableau', 'Power BI', 'Apache Spark', 'Hadoop',
            'Natural Language Processing', 'Computer Vision',

            # Mobile Development
            'React Native', 'Flutter', 'iOS Development', 'Android Development', 'Xamarin',

            # Design & UX
            'Figma', 'Adobe XD', 'Sketch', 'Photoshop', 'Illustrator', 'InVision', 'Zeplin',
            'User Research', 'Wireframing', 'Prototyping', 'UI Design', 'UX Design',

            # Project Management
            'Agile', 'Scrum', 'Kanban', 'JIRA', 'Trello', 'Asana', 'Microsoft Project',
            'Risk Management', 'Stakeholder Management',

            # Business & Soft Skills
            'Project Management', 'Team Leadership', 'Communication', 'Problem Solving',
            'Critical Thinking', 'Time Management', 'Customer Service', 'Sales',

            # Marketing & Digital
            'Google Analytics', 'SEO', 'SEM', 'Social Media Marketing', 'Content Marketing',
            'Email Marketing', 'Marketing Automation', 'CRM', 'HubSpot', 'Salesforce',

            # Finance & Accounting
            'Financial Analysis', 'Budgeting', 'Forecasting', 'Excel', 'QuickBooks', 'SAP',
            'Financial Modeling', 'Risk Assessment',

            # Engineering
            'CAD', 'SolidWorks', 'AutoCAD', 'MATLAB', 'Simulink', 'PLC Programming',
            'Electrical Engineering', 'Mechanical Engineering', 'Civil Engineering',

            # Healthcare
            'Medical Coding', 'Patient Care', 'EMR Systems', 'HIPAA Compliance', 'Clinical Research',

            # Education
            'Curriculum Development', 'E-Learning', 'Educational Technology', 'Teaching',
            'Instructional Design', 'Classroom Management',

            # Other Technical Skills
            'API Development', 'REST APIs', 'GraphQL', 'Microservices', 'Git', 'Version Control',
            'Unit Testing', 'Integration Testing', 'Quality Assurance', 'Security Auditing',
            'Network Administration', 'System Administration', 'Cybersecurity', 'Blockchain',
            'IoT', 'Embedded Systems',

            # Languages
            'English', 'Swahili', 'French', 'Arabic', 'Spanish', 'German', 'Chinese', 'Hindi',
        ]

        created_count = 0
        for skill_name in skills:
            skill, created = Skill.objects.get_or_create(
                name=skill_name,
                defaults={'name': skill_name}
            )
            if created:
                created_count += 1
                self.stdout.write(f'Created skill: {skill_name}')

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {created_count} skills. '
                f'Total skills in database: {Skill.objects.count()}'
            )
        )