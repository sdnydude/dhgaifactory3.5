#!/usr/bin/env bash
# install-hosts.sh — idempotently install DHG host entries into /etc/hosts
#
# Usage:
#   sudo bash install-hosts.sh              # install
#   sudo bash install-hosts.sh --dry-run    # preview changes
#   sudo bash install-hosts.sh --remove     # remove DHG block

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOSTS_FILE="${SCRIPT_DIR}/dhg-hosts"
TARGET="/etc/hosts"
MARKER_BEGIN="# >>> DHG LAN HOSTS >>>"
MARKER_END="# <<< DHG LAN HOSTS <<<"

DRY_RUN=false
REMOVE=false
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=true ;;
    --remove)  REMOVE=true ;;
  esac
done

if [ "$REMOVE" = "true" ]; then
  if grep -q "$MARKER_BEGIN" "$TARGET"; then
    if [ "$DRY_RUN" = "true" ]; then
      echo "DRY RUN: would remove DHG block from $TARGET"
    else
      sed -i "/$MARKER_BEGIN/,/$MARKER_END/d" "$TARGET"
      echo "Removed DHG hosts block from $TARGET"
    fi
  else
    echo "No DHG block found in $TARGET"
  fi
  exit 0
fi

if [ ! -f "$HOSTS_FILE" ]; then
  echo "ERROR: $HOSTS_FILE not found" >&2
  exit 1
fi

if grep -q "$MARKER_BEGIN" "$TARGET"; then
  if [ "$DRY_RUN" = "true" ]; then
    echo "DRY RUN: would replace existing DHG block in $TARGET"
    diff <(sed -n "/$MARKER_BEGIN/,/$MARKER_END/p" "$TARGET") <(echo "$MARKER_BEGIN"; cat "$HOSTS_FILE"; echo "$MARKER_END") || true
  else
    sed -i "/$MARKER_BEGIN/,/$MARKER_END/d" "$TARGET"
    printf '\n%s\n' "$MARKER_BEGIN" >> "$TARGET"
    cat "$HOSTS_FILE" >> "$TARGET"
    printf '%s\n' "$MARKER_END" >> "$TARGET"
    echo "Updated DHG hosts block in $TARGET"
  fi
else
  if [ "$DRY_RUN" = "true" ]; then
    echo "DRY RUN: would append DHG block to $TARGET"
    echo "--- entries ---"
    cat "$HOSTS_FILE"
  else
    printf '\n%s\n' "$MARKER_BEGIN" >> "$TARGET"
    cat "$HOSTS_FILE" >> "$TARGET"
    printf '%s\n' "$MARKER_END" >> "$TARGET"
    echo "Installed DHG hosts block in $TARGET"
  fi
fi
