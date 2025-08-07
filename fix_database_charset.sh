#!/bin/bash

# Activate the virtual environment
source /home/chuowlwe/virtualenv/repositories/chuo-market3/3.9/bin/activate

# Go to the project directory
cd /home/chuowlwe/repositories/chuo-market3

# Extract database credentials from environment
DB_NAME=$(python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('DB_NAME'))")
DB_USER=$(python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('DB_USER'))")
DB_PASSWORD=$(python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('DB_PASSWORD'))")
DB_HOST=$(python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('DB_HOST', 'localhost'))")

# Create SQL file to fix character set
cat > fix_charset.sql << EOF
-- Set the database default charset
ALTER DATABASE \`$DB_NAME\` CHARACTER SET utf8 COLLATE utf8_general_ci;

-- For existing tables that might cause issues with index lengths
ALTER TABLE django_apscheduler_djangojob CONVERT TO CHARACTER SET utf8 COLLATE utf8_general_ci;
ALTER TABLE django_apscheduler_djangojoblookup CONVERT TO CHARACTER SET utf8 COLLATE utf8_general_ci;
ALTER TABLE django_apscheduler_djangojobexecution CONVERT TO CHARACTER SET utf8 COLLATE utf8_general_ci;

-- If indexes are causing problems, drop and recreate them with limited length
-- First check if the index exists before trying to drop it
SET @exist := (SELECT COUNT(1) FROM INFORMATION_SCHEMA.STATISTICS WHERE table_schema = DATABASE() AND table_name = 'django_apscheduler_djangojoblookup' AND index_name = 'django_apscheduler_djangojoblookup_job_id_535f354f');
SET @sqlstmt := IF( @exist > 0, 'DROP INDEX django_apscheduler_djangojoblookup_job_id_535f354f ON django_apscheduler_djangojoblookup', 'SELECT ''Index does not exist''');
PREPARE stmt FROM @sqlstmt;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Create indexes with limited length
CREATE INDEX django_apscheduler_djangojoblookup_job_id_535f354f ON django_apscheduler_djangojoblookup (job_id(250));
CREATE INDEX django_apscheduler_djangojoblookup_job_class_string_ea8ffeb8 ON django_apscheduler_djangojoblookup (job_class_string(250));
EOF

# Execute the SQL file
echo "Fixing database character set and indexes..."
mysql -u$DB_USER -p$DB_PASSWORD -h$DB_HOST $DB_NAME < fix_charset.sql

# Remove SQL file for security
rm fix_charset.sql

# Try running migrations again
echo "Running migrations..."
python manage.py migrate
