#!/bin/bash

# This script creates the django_apscheduler tables directly in MySQL,
# bypassing Django's migration system completely. This should be
# used as a last resort when migrations cannot be fixed.

# Activate the virtual environment
source /home/chuowlwe/virtualenv/repositories/chuo-market3/3.9/bin/activate

# Go to the project directory
cd /home/chuowlwe/repositories/chuo-market3

# Extract database credentials from environment
DB_NAME=$(python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('DB_NAME'))")
DB_USER=$(python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('DB_USER'))")
DB_PASSWORD=$(python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('DB_PASSWORD'))")
DB_HOST=$(python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('DB_HOST', 'localhost'))")

echo "Creating direct SQL schema for django_apscheduler..."

cat > create_apscheduler_schema.sql << EOF
-- Drop existing tables if they exist
DROP TABLE IF EXISTS django_apscheduler_djangojobexecution;
DROP TABLE IF EXISTS django_apscheduler_djangojob;

-- Create django_apscheduler_djangojob table
CREATE TABLE django_apscheduler_djangojob (
    id varchar(255) NOT NULL PRIMARY KEY,
    next_run_time datetime(6) NULL,
    job_state longblob NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- Create index on next_run_time
CREATE INDEX django_apscheduler_djangojob_next_run_time_idx ON django_apscheduler_djangojob(next_run_time);

-- Create django_apscheduler_djangojobexecution table
CREATE TABLE django_apscheduler_djangojobexecution (
    id bigint(20) NOT NULL AUTO_INCREMENT PRIMARY KEY,
    status varchar(50) NOT NULL,
    run_time datetime(6) NOT NULL,
    duration decimal(15, 2) NULL,
    finished decimal(15, 2) NULL,
    exception varchar(1000) NULL,
    traceback longtext NULL,
    job_id varchar(255) NOT NULL,
    CONSTRAINT unique_job_execution UNIQUE (job_id, run_time),
    CONSTRAINT fk_djangojobexecution_job_id FOREIGN KEY (job_id) REFERENCES django_apscheduler_djangojob(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- Create index on run_time
CREATE INDEX django_apscheduler_djangojobexecution_run_time_idx ON django_apscheduler_djangojobexecution(run_time);

-- Mark all django_apscheduler migrations as applied in django_migrations
DELETE FROM django_migrations WHERE app = 'django_apscheduler';

INSERT INTO django_migrations (app, name, applied) VALUES 
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
mysql -u$DB_USER -p$DB_PASSWORD -h$DB_HOST $DB_NAME < create_apscheduler_schema.sql

# Remove SQL file for security
rm create_apscheduler_schema.sql

echo "Done creating django_apscheduler schema."
echo "You can now enable django_apscheduler in settings.py and run your application."
