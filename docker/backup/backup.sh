#!/bin/sh
set -eu
set -o pipefail

BACKUP_DIR=${BACKUP_DIR:-/backups}
RECIPIENTS_FILE=${BACKUP_RECIPIENTS_FILE:-/run/secrets/backup_recipients}

fail() {
    echo "backup: $1" >&2
    exit 1
}

check_freshness() {
    max_hours=${1:-36}
    case "$max_hours" in
        ''|*[!0-9]*) fail "freshness limit must be a positive number of hours" ;;
    esac
    [ "$max_hours" -gt 0 ] || fail "freshness limit must be a positive number of hours"
    newest=
    for candidate in "$BACKUP_DIR"/bs-manager-*.age; do
        [ -f "$candidate" ] || continue
        [ -z "$newest" ] && newest=$candidate && continue
        [ "$candidate" -nt "$newest" ] && newest=$candidate
    done
    [ -n "$newest" ] || fail "no encrypted backup archive found"
    backup_epoch=$(stat -c %Y "$newest" 2>/dev/null) || fail "could not read newest archive modification time"
    now_epoch=$(date -u +%s)
    age_seconds=$((now_epoch - backup_epoch))
    [ "$age_seconds" -ge 0 ] || fail "newest archive timestamp is in the future"
    [ "$age_seconds" -le $((max_hours * 3600)) ] || fail "newest encrypted archive exceeds freshness limit"
    echo "Encrypted backup freshness check passed."
}

if [ "${1:-}" = "--check-freshness" ]; then
    [ "$#" -le 2 ] || fail "usage: backup.sh --check-freshness [max-age-hours]"
    check_freshness "${2:-36}"
    exit 0
fi
[ "$#" -eq 0 ] || fail "usage: backup.sh [--check-freshness [max-age-hours]]"

: "${PGHOST:?PGHOST is required}"
: "${PGUSER:?PGUSER is required}"
: "${PGDATABASE:?PGDATABASE is required}"
: "${PGPASSFILE:?PGPASSFILE is required}"
[ -r "$PGPASSFILE" ] || fail "password file is missing or unreadable"
[ -r "$RECIPIENTS_FILE" ] || fail "recipient file is missing or unreadable"
[ -d "$BACKUP_DIR" ] && [ -w "$BACKUP_DIR" ] || fail "backup directory is not writable"

umask 077
partial_base=
partial=
cleanup() {
    [ -z "$partial" ] || rm -f -- "$partial"
    [ -z "$partial_base" ] || rm -f -- "$partial_base"
}
trap cleanup EXIT
trap 'exit 1' HUP INT TERM
partial_base=$(mktemp "$BACKUP_DIR/.bs-manager-backup.XXXXXXXX") || fail "could not create private partial archive"
partial="$partial_base.partial"
mv -- "$partial_base" "$partial" || fail "could not prepare private partial archive"
partial_base=

stamp=$(date -u +%Y-%m-%dT%H-%M-%SZ)
suffix=$(od -An -N8 -tx1 /dev/urandom | tr -d ' \n')
final="$BACKUP_DIR/bs-manager-$stamp-$suffix.age"

if ! pg_dump --no-password --format=custom --no-owner --no-acl --dbname="$PGDATABASE" \
    | age --encrypt --recipients-file "$RECIPIENTS_FILE" >"$partial"; then
    fail "database dump or encryption failed; partial archive removed"
fi

# A hard link publishes the completed file atomically and refuses to overwrite.
ln -- "$partial" "$final" || fail "could not publish encrypted archive without overwriting"
rm -- "$partial"
partial=
echo "Encrypted backup created: $(basename "$final")"
