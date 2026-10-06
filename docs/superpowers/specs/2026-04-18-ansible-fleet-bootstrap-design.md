# Ansible Fleet Bootstrap Design

**Date:** 2026-04-18
**Status:** Design
**Scope:** SSH key bootstrap and mesh distribution across 4-machine DHG fleet

## Context

DHG operates a 4-machine fleet on a local 10.0.0.0/24 network. The fleet has heterogeneous operating systems (Ubuntu, Windows x2, macOS) and is managed from g700data1 as the Ansible control node. Ansible 2.16.3 is installed with all required collections (ansible.posix, ansible.windows, community.windows).

Playbooks already exist in `ansible/` (untracked) to bootstrap SSH key-based auth and distribute keys in a mesh topology. The goal is to run these playbooks to bring the fleet online with passwordless SSH between all machines.

**Current SSH connectivity from g700data1:**

| Host | IP | OS | Key SSH | Status |
|------|----|----|---------|--------|
| g700data1 | 10.0.0.251 | Ubuntu 24.04 | self | control node |
| jason | 10.0.0.80 | Windows | works | ready |
| macbook | 10.0.0.235 | macOS M3 | works | ready |
| dhg5090 | 10.0.0.54 | Windows | denied | needs bootstrap |

## Bug Fix

**File:** `ansible/playbooks/bootstrap-windows.yml`, line 52

The `ssh-keygen` command passes `'""'` as the passphrase, which sends literal `""` instead of an empty string. Fix: change `-N '""'` to `-N '""'` -> `-N ''` (empty string in PowerShell).

## Execution Plan

### Step 0: Fix the quoting bug
Edit `ansible/playbooks/bootstrap-windows.yml` line 52.

### Step 1: Bootstrap dhg5090
```bash
cd ansible
ansible-playbook playbooks/bootstrap-windows.yml --limit=dhg5090 --ask-pass
```
Requires entering the swebber64 password once. The playbook:
1. Detects admin group membership (determines authorized_keys path)
2. Creates `C:\Users\swebber64\.ssh\`
3. Generates per-host Ed25519 keypair
4. Installs `dhg_fleet.pub` in the correct authorized_keys file
5. Fixes ACL on `administrators_authorized_keys` if admin
6. Reports the host's public key

### Step 2: Verify control-node connectivity to all 4
```bash
ansible all -m ping
```
Expected: all 4 hosts return `pong`. If dhg5090 fails, troubleshoot before proceeding.

### Step 3: Distribute mesh keys (POSIX)
```bash
ansible-playbook playbooks/distribute-ssh-keys.yml
```
Gathers pubkeys from all hosts, installs on g700data1 and macbook.

### Step 4: Distribute mesh keys (Windows)
```bash
ansible-playbook playbooks/distribute-ssh-keys-windows.yml
```
Same gather, installs on dhg5090 and jason with admin-path detection.

### Step 5: Verify full mesh
```bash
ansible all -m ping
```

## Verification

After all steps complete, the fleet should have:
- g700data1 can SSH to all 3 peers without password
- All peers can SSH to each other without password
- `ansible all -m ping` returns SUCCESS for all 4 hosts

## Out of Scope

- Ansible Vault / secrets management
- Ansible roles for Docker, GPU, or service deployment
- CI/CD integration
- Committing `ansible/` to git (separate decision)
