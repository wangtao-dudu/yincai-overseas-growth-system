#!/bin/sh
set -eu

PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
BACKUP_DIR="$PROJECT_DIR/backups"
STAMP=$(date +%Y%m%d-%H%M%S)

mkdir -p "$BACKUP_DIR"
tar -czf "$BACKUP_DIR/yincai-$STAMP.tar.gz" -C "$PROJECT_DIR" data uploads
find "$BACKUP_DIR" -type f -name 'yincai-*.tar.gz' -mtime +30 -delete
printf '备份完成：%s\n' "$BACKUP_DIR/yincai-$STAMP.tar.gz"

