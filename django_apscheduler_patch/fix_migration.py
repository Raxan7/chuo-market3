from django.db import connection

def fix_apscheduler_migration():
    """
    This function manually marks the problematic django-apscheduler migration as applied.
    Run this before attempting migrations again if you encounter the
    'Specified key was too long; max key length is 1000 bytes' error.
    """
    with connection.cursor() as cursor:
        # Check if the migration has already been applied
        cursor.execute(
            "SELECT * FROM django_migrations WHERE app = 'django_apscheduler' AND name = '0004_auto_20200717_1043'"
        )
        if cursor.fetchone() is None:
            # Add the migration as if it was already applied
            cursor.execute(
                "INSERT INTO django_migrations (app, name, applied) VALUES (%s, %s, NOW())",
                ['django_apscheduler', '0004_auto_20200717_1043']
            )
            print("Successfully marked django_apscheduler migration 0004_auto_20200717_1043 as applied.")
        else:
            print("Migration django_apscheduler.0004_auto_20200717_1043 is already marked as applied.")

if __name__ == "__main__":
    fix_apscheduler_migration()
