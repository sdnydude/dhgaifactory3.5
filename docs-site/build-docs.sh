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
# No persistent webpack cache: a stale entry in node_modules/.cache/webpack
# compiled service-inventory.md without its metadata export and failed the
# portage Deploy Docs build on 2026-10-04 and 2026-10-06 ("reading 'id'" in
# DocItem); a cache-disabled build of the same tree passed. A cold build
# costs ~10s more; package.json "build" (the CI path) sets the same flag.
DOCUSAURUS_NO_PERSISTENT_CACHE=1 npx docusaurus build --out-dir "$TMP"

mkdir -p build
rsync -a --delete "$TMP"/ build/   # swap contents; build/ itself is never removed
rm -rf "$TMP"

echo "Docs built into existing build/ (inode preserved) — no container restart needed."
