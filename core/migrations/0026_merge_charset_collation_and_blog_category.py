from django.db import migrations


class Migration(migrations.Migration):
    """
    This migration is a manual merge to resolve the conflicting migration paths.
    It connects the simplified migrations with the main migration path.
    APScheduler has been removed from the project.
    """

    dependencies = [
        ('core', '0004_update_charset_collation'),
        ('core', '0025_blog_category_alter_blog_is_markdown'),
    ]

    operations = [
        # No operations needed, this migration just connects the two branches
    ]
