#!/usr/bin/env bash
# Inode-preserving docs build.
#
# `docusaurus build` rm-rf's build/ and recreates it with a NEW inode. The
# dhg-docs container bind-mounts docs-site/build -> /usr/share/nginx/html and
# resolves that host inode at container start; after the rm-rf the kernel keeps
# serving the orphaned old inode, so fresh docs never appear until the container
# is restarted.
#
# Fix: never delete build/. Build into a temp dir, then rsync its CONTENTS into
# the existing build/. build/'s inode stays stable, the mount never orphans, and
# nginx serves fresh files live with no restart.
set -euo pipefail
cd "$(dirname "$0")"

TMP="build.tmp"
rm -rf "$TMP"
npx docusaurus build --out-dir "$TMP"

mkdir -p build
rsync -a --delete "$TMP"/ build/   # swap contents; build/ itself is never removed
rm -rf "$TMP"

echo "Docs built into existing build/ (inode preserved) — no container restart needed."
