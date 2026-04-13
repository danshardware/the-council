#!env bash
# Simple backup script to copy the current state of the project to a file (tar.bz or stdout).
# Usage: ./backup.sh [file_to_backup_to]

set -e

if [ "$1" ]; then
    BACKUP_FILE="$1"
else
    BACKUP_FILE="-"
fi

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

tar -cjf "$BACKUP_FILE" -C "$DIR" ./logs ./memory_db ./messages ./shared_knowledge ./workspace || { echo "Backup failed"; exit 1; }