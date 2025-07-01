# Learning Management System (LMS) App for Chuo Market

This Django app provides a complete Learning Management System (LMS) functionality integrated with Chuo Market. It is based on the features of SkyLearn LMS but adapted to work seamlessly with the Chuo Market platform.

## Features

- **Course Management**: Create, update, and manage courses, modules, and content
- **User Roles**: Student, Instructor, and Admin roles with appropriate permissions
- **Rich Content Types**: Support for documents, videos, external links, and text content
- **Assessment System**: Quizzes with multiple choice, true/false, and essay questions
- **Grading System**: Comprehensive grading with attendance, assignments, mid-exam, and final exam components
- **Student Dashboards**: Personalized dashboards for students to track their progress
- **Instructor Tools**: Course management, content creation, quiz authoring, and student grading

## Installation

1. Install the required packages:
   ```bash
   pip install -r lms-requirements.txt
   ```

2. Run migrations to create the database tables:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

3. Create a superuser to access the admin interface:
   ```bash
   python manage.py createsuperuser
   ```

4. Start the development server:
   ```bash
   python manage.py runserver
   ```

5. Access the LMS at: http://localhost:8000/lms/

## Usage

1. **Create Programs**: Use the admin interface to create educational programs
2. **Create Courses**: Create courses within programs 
3. **Add Course Content**: Add modules and various content types to courses
4. **Create Assessments**: Add quizzes and other assessments
5. **Enroll Students**: Students can self-enroll or be enrolled by administrators
6. **Grade Students**: Instructors can grade students based on various components

## Integration with Chuo Market

The LMS app is fully integrated with Chuo Market and uses the same user authentication system. It extends the core User model with LMS-specific profiles, allowing existing users to seamlessly access LMS functionality.

## Credits

This LMS app is inspired by SkyLearn, an open-source learning management system. It has been adapted and customized to work within the Chuo Market ecosystem.
