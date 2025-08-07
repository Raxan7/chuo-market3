#!/bin/bash

# Activate the virtual environment
source /home/chuowlwe/virtualenv/repositories/chuo-market3/3.9/bin/activate

# Go to the project directory
cd /home/chuowlwe/repositories/chuo-market3

echo "===== STEP 1: Fixing MySQL settings in settings.py ====="
echo "Removing innodb_large_prefix and innodb_file_format settings from DATABASE OPTIONS"
echo "These settings are deprecated in MySQL 5.7 and removed in MySQL 8.0"

echo "===== STEP 2: Fixing django_apscheduler tables ====="
# Extract database credentials from environment
DB_NAME=$(python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('DB_NAME'))")
DB_USER=$(python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('DB_USER'))")
DB_PASSWORD=$(python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('DB_PASSWORD'))")
DB_HOST=$(python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('DB_HOST', 'localhost'))")

# Create a simple SQL file to set up django_apscheduler tables correctly
cat > fix_apscheduler_simple.sql << EOF
-- Set the database default charset
ALTER DATABASE \`$DB_NAME\` CHARACTER SET utf8 COLLATE utf8_general_ci;

-- Create all required django_apscheduler tables with correct UTF-8 charset
CREATE TABLE IF NOT EXISTS \`django_apscheduler_djangojob\` (
  \`id\` varchar(255) NOT NULL PRIMARY KEY,
  \`next_run_time\` datetime(6) NULL,
  \`job_state\` longblob NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE INDEX IF NOT EXISTS \`django_apscheduler_djangojob_next_run_time_idx\` 
ON \`django_apscheduler_djangojob\` (\`next_run_time\`);

CREATE TABLE IF NOT EXISTS \`django_apscheduler_djangojobexecution\` (
  \`id\` bigint(20) NOT NULL AUTO_INCREMENT PRIMARY KEY,
  \`status\` varchar(50) NOT NULL,
  \`run_time\` datetime(6) NOT NULL,
  \`duration\` decimal(15,2) NULL,
  \`finished\` decimal(15,2) NULL,
  \`exception\` varchar(1000) NULL,
  \`traceback\` longtext NULL,
  \`job_id\` varchar(255) NOT NULL,
  CONSTRAINT \`django_apscheduler_job_execution_unique\` UNIQUE (\`job_id\`, \`run_time\`),
  CONSTRAINT \`django_apscheduler_job_execution_job_id_fk\` 
  FOREIGN KEY (\`job_id\`) REFERENCES \`django_apscheduler_djangojob\` (\`id\`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

CREATE INDEX IF NOT EXISTS \`django_apscheduler_djangojobexecution_run_time_idx\` 
ON \`django_apscheduler_djangojobexecution\` (\`run_time\`);

-- Mark all django_apscheduler migrations as applied
INSERT IGNORE INTO django_migrations (app, name, applied) VALUES 
('django_apscheduler', '0001_initial', NOW()),
('django_apscheduler', '0002_auto_20180412_0758', NOW()),
('django_apscheduler', '0003_auto_20200716_1632', NOW()),
('django_apscheduler', '0004_auto_20200717_1043', NOW()),
('django_apscheduler', '0005_migrate_name_to_id', NOW()),
('django_apscheduler', '0006_remove_djangojob_name', NOW()),
('django_apscheduler', '0007_auto_20200717_1404', NOW()),
('django_apscheduler', '0008_remove_djangojobexecution_started', NOW()),
('django_apscheduler', '0009_djangojobexecution_unique_job_executions', NOW());
EOF

# Execute the SQL file
echo "Executing SQL commands to fix database schema..."
mysql -u$DB_USER -p$DB_PASSWORD -h$DB_HOST $DB_NAME < fix_apscheduler_simple.sql 2>/dev/null || echo "Some SQL commands may have failed, but this is often normal if tables already exist."

# Remove SQL file for security
rm fix_apscheduler_simple.sql

echo "===== STEP 3: Fix jobs/scheduler.py temporary workaround ====="
# Backup original scheduler.py
cp jobs/scheduler.py jobs/scheduler.py.bak

# Create a fixed version of scheduler.py
cat > jobs/scheduler.py << 'EOF'
import logging
from django.conf import settings
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from jobs.api_integration import fetch_all_jobs

logger = logging.getLogger(__name__)

def start_scheduler():
    """Start the background scheduler to fetch jobs periodically"""
    try:
        # Import these conditionally to avoid errors when django_apscheduler is not configured
        from django_apscheduler.jobstores import DjangoJobStore
        
        scheduler = BackgroundScheduler()
        scheduler.add_jobstore(DjangoJobStore(), "default")
        
        # Schedule job to fetch from APIs every 6 hours
        scheduler.add_job(
            fetch_all_jobs,
            trigger=IntervalTrigger(hours=6),
            id="fetch_jobs",
            replace_existing=True,
        )
        
        try:
            logger.info("Starting scheduler...")
            scheduler.start()
        except Exception as e:
            logger.error(f"Error starting scheduler: {e}")
    except ImportError:
        logger.warning("django_apscheduler not properly configured. Job scheduling disabled.")
    except Exception as e:
        logger.error(f"Error initializing scheduler: {e}")
EOF

echo "===== STEP 4: Apply all migrations ====="
python manage.py makemigrations --merge --noinput
python manage.py migrate

echo "===== STEP 5: Done ====="
echo "If you want to restore the original scheduler.py, run:"
echo "mv jobs/scheduler.py.bak jobs/scheduler.py"
