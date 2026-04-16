#!/bin/bash

# Log rotation and cleanup script for 3D Kenji
# Rotates logs and removes old backups

set -e

LOG_DIR="${LOG_DIR:=/workspace/data/logs}"
MAX_AGE_DAYS="${MAX_AGE_DAYS:=30}"  # Keep logs for 30 days
BACKUP_FILES="${BACKUP_FILES:=5}"   # Keep 5 backup files

echo "Starting log rotation for $LOG_DIR"

# Check if log directory exists
if [ ! -d "$LOG_DIR" ]; then
    echo "Log directory $LOG_DIR does not exist. Skipping rotation."
    exit 0
fi

# Find and remove old log files (older than MAX_AGE_DAYS)
echo "Removing log files older than $MAX_AGE_DAYS days..."
find "$LOG_DIR" -name "*.log*" -type f -mtime +$MAX_AGE_DAYS -delete
echo "Done."

# Cleanup old backup files (keep only BACKUP_FILES count)
echo "Cleaning up old backup files (keeping $BACKUP_FILES backups)..."
for log_file in "$LOG_DIR"/*.log; do
    if [ -f "$log_file" ]; then
        # Count backup files for this log
        backup_count=$(find "$LOG_DIR" -name "${log_file}.*" -type f | wc -l)
        
        if [ $backup_count -gt $BACKUP_FILES ]; then
            # Delete oldest backups
            find "$LOG_DIR" -name "${log_file}.*" -type f -printf '%T+ %p\n' | \
                sort | head -n $((backup_count - BACKUP_FILES)) | \
                cut -d' ' -f2- | xargs rm -f
            echo "Cleaned up $(($backup_count - BACKUP_FILES)) old backups for $log_file"
        fi
    fi
done

echo "Log rotation complete."
