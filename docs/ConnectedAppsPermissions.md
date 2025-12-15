# Connected Apps Permissions Guide

## Overview

This guide explains how to adjust permissions for connected apps (like Replit, GitHub Codespaces, etc.) to enable read/write access to your repositories, both public and private.

## Table of Contents

1. [Understanding Connected Apps](#understanding-connected-apps)
2. [Granting Replit Write Access](#granting-replit-write-access)
3. [Managing GitHub App Permissions](#managing-github-app-permissions)
4. [OAuth App Permissions](#oauth-app-permissions)
5. [Personal Access Tokens](#personal-access-tokens)
6. [Troubleshooting](#troubleshooting)

---

## Understanding Connected Apps

GitHub connected apps fall into three main categories:

1. **GitHub Apps** - Newer, more granular permission model
2. **OAuth Apps** - Older model, user-level permissions
3. **Personal Access Tokens (PATs)** - Manual token-based access

For apps like **Replit** that need to push code to your repositories, they typically use either GitHub Apps or OAuth Apps.

---

## Granting Replit Write Access

### Method 1: Via GitHub App Installation (Recommended)

If Replit uses a GitHub App integration:

1. **Navigate to GitHub Settings**
   - Go to [https://github.com/settings/installations](https://github.com/settings/installations)
   - Or: Click your profile → Settings → Applications → Installed GitHub Apps

2. **Find Replit App**
   - Look for "Replit" or "Replit GitHub App" in the list
   - If not installed, you'll need to install it first from [Replit's GitHub integration page](https://replit.com)

3. **Configure Repository Access**
   - Click **Configure** next to the Replit app
   - Under "Repository access", choose one of:
     - **All repositories** - Grants access to all current and future repos
     - **Only select repositories** - Choose specific repos (recommended)
   
4. **Set Repository Permissions**
   - Scroll down to "Repository permissions"
   - Find **"Contents"** permission
   - Set to **"Read and write"** (this allows push access)
   - Find **"Metadata"** permission (usually required)
   - Set to **"Read-only"** (minimum required)

5. **Optional: Additional Permissions**
   - **Pull requests**: Read and write (if Replit creates PRs)
   - **Workflows**: Read and write (if you want to modify GitHub Actions)
   - **Issues**: Read and write (if needed)

6. **Save Changes**
   - Click **Save** at the bottom of the page
   - Replit now has write access to your repositories

### Method 2: Via OAuth App Authorization

If Replit uses OAuth:

1. **Navigate to Authorized OAuth Apps**
   - Go to [https://github.com/settings/applications](https://github.com/settings/applications)
   - Or: Profile → Settings → Applications → Authorized OAuth Apps

2. **Find and Click Replit**
   - Click on "Replit" in the list

3. **Check Granted Permissions**
   - Review the current permissions
   - OAuth apps request specific scopes during authorization

4. **Modify Access (if needed)**
   - Click **"Revoke"** to remove current access
   - Re-authorize Replit and grant the following scopes:
     - `repo` - Full control of private repositories (includes push)
     - `public_repo` - Access to public repositories only (if you don't need private)
     - `workflow` - Update GitHub Action workflows (optional)

5. **Reconnect in Replit**
   - After revocation, go back to Replit
   - Reconnect your GitHub account
   - Accept the new permission requests

---

## Managing GitHub App Permissions

### For Organization Repositories

If the repository belongs to an organization:

1. **Organization Settings**
   - Navigate to your organization page
   - Click **Settings** → **GitHub Apps** or **Installed GitHub Apps**

2. **Configure App Access**
   - Find the app (e.g., Replit)
   - Click **Configure**
   - Adjust permissions as described above

3. **Organization Approval**
   - Some organizations require admin approval for app installations
   - Contact your organization admin if you don't have permission

### Required Permissions for Push Access

For any app to push code to your repositories, ensure these minimum permissions:

| Permission | Access Level | Purpose |
|------------|-------------|---------|
| **Contents** | Read and write | Clone, pull, and **push** code |
| **Metadata** | Read-only | Access basic repository info |
| **Commit statuses** | Read-only (optional) | View CI/CD status |

### Additional Permissions for Full Development Workflow

| Permission | Access Level | Purpose |
|------------|-------------|---------|
| **Pull requests** | Read and write | Create and update PRs |
| **Issues** | Read and write | Create and manage issues |
| **Workflows** | Read and write | Modify GitHub Actions |
| **Deployments** | Read and write | Manage deployments |
| **Environments** | Read and write | Access deployment environments |

---

## OAuth App Permissions

### Understanding OAuth Scopes

OAuth apps use scopes to define permissions. Key scopes for repository access:

- **`repo`** - Full control of private repositories
  - Includes: `repo:status`, `repo_deployment`, `public_repo`, `repo:invite`, `security_events`
  - **This scope is required for push access to private repositories**

- **`public_repo`** - Access to public repositories only
  - Use this if you only work with public repos
  - More limited, better for security

- **`workflow`** - Update GitHub Action workflow files
  - Required if you want to modify `.github/workflows/` files

### Checking Current OAuth Permissions

1. Visit [https://github.com/settings/applications](https://github.com/settings/applications)
2. Click on the app name
3. Review "This application will be able to:" section
4. Verify it includes repository write access

---

## Personal Access Tokens

### Creating a PAT for Replit (Alternative Method)

If Replit supports PAT authentication:

1. **Generate Token**
   - Go to [https://github.com/settings/tokens](https://github.com/settings/tokens)
   - Click **Generate new token** → **Generate new token (classic)**
   - Or use **Fine-grained tokens** for better security

2. **Configure Token (Classic)**
   - Name: `Replit Access Token`
   - Expiration: Choose your preference (recommend 90 days or less)
   - Select scopes:
     - ✅ `repo` (Full control of private repositories)
     - ✅ `workflow` (Update GitHub Action workflows) - optional
     - ✅ `write:packages` (if using GitHub Packages) - optional

3. **Configure Fine-Grained Token (Recommended)**
   - Resource owner: Select your account or organization
   - Repository access: 
     - "All repositories" or "Only select repositories"
   - Permissions:
     - **Repository permissions:**
       - Contents: **Read and write**
       - Metadata: **Read-only** (automatically included)
       - Pull requests: **Read and write** (optional)
       - Workflows: **Read and write** (optional)

4. **Copy and Save Token**
   - Click **Generate token**
   - **IMPORTANT**: Copy the token immediately (you won't see it again)
   - Store securely (password manager recommended)

5. **Use Token in Replit**
   - In Replit, go to project settings or secrets
   - Add the token as `GITHUB_TOKEN` or as instructed by Replit
   - Use it for git operations:
     ```bash
     git remote set-url origin https://YOUR_TOKEN@github.com/username/repo.git
     ```

---

## Specific Instructions for Replit

### Method A: Using Replit's GitHub Integration

1. **In Replit**
   - Open your Repl
   - Click on **Version Control** (Git icon) in the sidebar
   - Click **Connect to GitHub**

2. **Authorize Replit**
   - You'll be redirected to GitHub
   - Review the permissions Replit is requesting
   - Ensure it includes repository write access
   - Click **Authorize Replit**

3. **Select Repository**
   - Choose existing repository or create new
   - For existing repos, ensure you have write access

4. **Push Code**
   - Make changes in Replit
   - Use the Version Control panel to commit and push
   - Or use git commands in the shell:
     ```bash
     git add .
     git commit -m "Your commit message"
     git push origin main
     ```

### Method B: Manual Git Configuration in Replit

If you need more control:

1. **Create a Personal Access Token** (see above section)

2. **In Replit Shell**, configure git:
   ```bash
   # Configure git user
   git config --global user.name "Your Name"
   git config --global user.email "your.email@example.com"
   
   # Clone your repository with token
   git clone https://YOUR_TOKEN@github.com/username/repository.git
   
   # Or update existing remote
   cd your-repository
   git remote set-url origin https://YOUR_TOKEN@github.com/username/repository.git
   ```

3. **Push Changes**
   ```bash
   git add .
   git commit -m "Changes from Replit"
   git push origin main
   ```

4. **Security Note**: 
   - Store the token in Replit Secrets instead of hardcoding:
     - Add a secret named `GITHUB_TOKEN`
     - Access it in shell: `$GITHUB_TOKEN`
     - Use: `git remote set-url origin https://$GITHUB_TOKEN@github.com/username/repo.git`

---

## Verification

### Test Write Access

After configuring permissions, verify push access works:

```bash
# Create a test file
echo "# Test from Replit" > TEST.md

# Add, commit, and push
git add TEST.md
git commit -m "Test push access from Replit"
git push origin main

# If successful, you should see:
# "Writing objects: 100% ... done"
```

### Check GitHub

1. Go to your repository on GitHub
2. Verify the test commit appears
3. Check that the author is correctly attributed

---

## Troubleshooting

### "Permission denied" or "403 Forbidden"

**Cause**: Insufficient permissions

**Solutions**:
1. Verify the app has "Contents: Read and write" permission
2. For OAuth apps, ensure the `repo` scope is granted
3. Check if repository requires 2FA (enable it in your account)
4. For organization repos, check org-level restrictions

### "Remote repository not found"

**Cause**: App doesn't have access to the repository

**Solutions**:
1. In GitHub App settings, add the specific repository
2. Check repository visibility (private repos need explicit access)
3. Verify you're using the correct repository URL

### "Updates were rejected because the remote contains work"

**Cause**: Local branch is behind remote

**Solutions**:
```bash
# Pull latest changes first
git pull origin main

# Or pull with rebase
git pull --rebase origin main

# Then push
git push origin main
```

### Token Authentication Failed

**Cause**: Expired or invalid token

**Solutions**:
1. Generate a new Personal Access Token
2. Update the remote URL with the new token
3. Check token hasn't expired (Settings → Developer settings → Tokens)

### Two-Factor Authentication Issues

**Cause**: 2FA requires special handling

**Solutions**:
1. Use a Personal Access Token instead of password
2. Use SSH keys (configure in GitHub settings)
3. Enable 2FA in the connecting app if supported

### Organization Access Restrictions

**Cause**: Organization blocks third-party app access

**Solutions**:
1. Contact your organization admin
2. Request approval for the specific app
3. Organization settings → Third-party access → Review and approve

---

## Security Best Practices

### 1. Principle of Least Privilege
- Only grant necessary permissions
- Use "Only select repositories" instead of "All repositories"
- Prefer fine-grained tokens over classic tokens

### 2. Regular Audits
- Review connected apps monthly: [https://github.com/settings/applications](https://github.com/settings/applications)
- Revoke unused app access
- Check repository access logs

### 3. Token Management
- Set expiration dates on tokens (max 90 days recommended)
- Rotate tokens regularly
- Store tokens in secure secrets managers (not in code)
- Revoke tokens immediately if compromised

### 4. Monitor Activity
- Enable security alerts for your repositories
- Review commit history for unexpected changes
- Use branch protection rules for important branches

### 5. Use SSH Keys (Alternative to Tokens)
```bash
# Generate SSH key
ssh-keygen -t ed25519 -C "your.email@example.com"

# Add to GitHub (Settings → SSH and GPG keys)
# Then use SSH URLs
git remote set-url origin git@github.com:username/repository.git
```

---

## Quick Reference Commands

### Check Current Remote
```bash
git remote -v
```

### Update Remote URL with Token
```bash
git remote set-url origin https://TOKEN@github.com/USER/REPO.git
```

### Update Remote URL with SSH
```bash
git remote set-url origin git@github.com:USER/REPO.git
```

### Test Push Access
```bash
git push --dry-run origin main
```

### View Git Configuration
```bash
git config --list
```

---

## Additional Resources

- **GitHub Apps Documentation**: https://docs.github.com/en/apps
- **OAuth Scopes**: https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/scopes-for-oauth-apps
- **Personal Access Tokens**: https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token
- **Replit GitHub Integration**: https://docs.replit.com/programming-ide/using-git-on-replit
- **Managing Deploy Keys**: https://docs.github.com/en/developers/overview/managing-deploy-keys

---

## Summary Checklist

For granting Replit (or any connected app) write access to repositories:

- [ ] Identify if the app uses GitHub App or OAuth
- [ ] Navigate to GitHub Settings → Applications
- [ ] Find the app (Replit) in Installed GitHub Apps or Authorized OAuth Apps
- [ ] Click Configure (GitHub App) or the app name (OAuth)
- [ ] Set repository access to include your target repositories
- [ ] For GitHub Apps: Set "Contents" permission to "Read and write"
- [ ] For OAuth Apps: Ensure "repo" scope is granted
- [ ] Save changes
- [ ] Test push access from the app
- [ ] Verify commits appear on GitHub
- [ ] Document the token/configuration in a secure location

---

**Last Updated**: December 2025  
**Maintained By**: DHG AI Factory Team

For questions or issues with this guide, please open an issue in the repository.
