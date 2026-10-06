# Cloudflare Tunnel Setup Guide

This guide walks through setting up a Cloudflare Tunnel to expose local services on a private server to the internet via public hostnames, with SSL termination and Google OAuth authentication via Cloudflare Access.

**What this achieves:** Public URLs like `app.yoursite.com` securely route through Cloudflare to `localhost:3000` on your server, with no open inbound ports, free SSL, and Google login required.

---

## Prerequisites

- A domain managed by Cloudflare DNS (e.g., `digitalharmonyai.com`)
- A Cloudflare account with the domain added
- A Linux server (Ubuntu 22.04+ or similar) with services running on localhost
- `sudo` access on the server
- A Google Cloud project for OAuth (for the authentication step)

---

## Part 1: Install cloudflared

`cloudflared` is Cloudflare's tunnel client. It creates an outbound-only connection from your server to Cloudflare's edge network — no inbound firewall rules needed.

```bash
# Download and install the latest cloudflared .deb package
curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared.deb
rm cloudflared.deb

# Verify installation
cloudflared --version
```

You should see output like: `cloudflared version 2025.11.1 (built ...)`

---

## Part 2: Authenticate cloudflared

This links your server to your Cloudflare account.

```bash
cloudflared tunnel login
```

This opens a browser URL (or prints one you can paste into a browser). Log in to your Cloudflare account and select the domain you want to use (e.g., `digitalharmonyai.com`).

After authorization, a certificate is saved to:
```
~/.cloudflared/cert.pem
```

> **AI assistants:** If no browser is available, the command prints a URL. Provide this URL to the user and ask them to complete the authorization in their browser. The cert.pem file will appear automatically once they authorize.

---

## Part 3: Create a Tunnel

A tunnel is a named, persistent connection between your server and Cloudflare.

```bash
cloudflared tunnel create <TUNNEL_NAME>
```

For example:
```bash
cloudflared tunnel create dhg-tunnel
```

This outputs:
- A **Tunnel ID** (UUID like `30437aa6-d3f8-4c52-85cc-be0a0bfe8478`)
- A **credentials file** at `~/.cloudflared/<TUNNEL_ID>.json`

**Save the Tunnel ID** — you need it for the config file.

To verify:
```bash
cloudflared tunnel list
```

---

## Part 4: Create DNS Routes

Each hostname that should route through the tunnel needs a CNAME record in Cloudflare DNS. The `cloudflared` CLI creates these automatically:

```bash
cloudflared tunnel route dns <TUNNEL_NAME> <HOSTNAME>
```

For example:
```bash
cloudflared tunnel route dns dhg-tunnel app.digitalharmonyai.com
cloudflared tunnel route dns dhg-tunnel secrets.digitalharmonyai.com
```

This creates CNAME records pointing each hostname to `<TUNNEL_ID>.cfargotunnel.com`.

> **Verify in Cloudflare Dashboard:** Go to your domain > DNS > Records. You should see CNAME records for each hostname pointing to `<TUNNEL_ID>.cfargotunnel.com` with the orange Cloudflare proxy icon enabled.

---

## Part 5: Configure the Tunnel

Create the config file that tells cloudflared which hostnames map to which local services.

```bash
nano ~/.cloudflared/config.yml
```

Write the following (substitute your values):

```yaml
tunnel: <TUNNEL_ID>
credentials-file: /home/<YOUR_USER>/.cloudflared/<TUNNEL_ID>.json

ingress:
  - hostname: app.yoursite.com
    service: http://localhost:3000
  - hostname: secrets.yoursite.com
    service: http://localhost:8089
  - service: http_status:404
```

### Ingress Rules Explained

- Rules are evaluated **top to bottom**
- Each rule maps a public `hostname` to a local `service`
- The **last rule must be a catch-all** with no hostname — this handles unmatched requests
- `http_status:404` returns a 404 for any unmatched hostname (recommended)
- Services are typically `http://localhost:<PORT>` for local web apps

### Common Service Formats

| Format | Use Case |
|--------|----------|
| `http://localhost:3000` | Standard web app |
| `https://localhost:8443` | App with its own SSL (rare) |
| `tcp://localhost:22` | SSH access (requires Cloudflare WARP on client) |
| `http_status:404` | Catch-all fallback |

### Validate the Config

```bash
cloudflared tunnel ingress validate
```

This checks your config for syntax errors. Fix any issues before proceeding.

### Test Before Installing

```bash
cloudflared tunnel run
```

This runs the tunnel in the foreground. Open your hostname in a browser to verify it works. Press `Ctrl+C` to stop when satisfied.

---

## Part 6: Install as a System Service

Running cloudflared as a systemd service ensures it starts automatically on boot and restarts on failure.

### Step 1: Copy Config to System Location

```bash
sudo mkdir -p /etc/cloudflared
sudo cp ~/.cloudflared/config.yml /etc/cloudflared/config.yml
sudo cp ~/.cloudflared/<TUNNEL_ID>.json /etc/cloudflared/<TUNNEL_ID>.json
```

> **Important:** The credentials file path in `config.yml` must match where you copy it. Either update the `credentials-file` path in `/etc/cloudflared/config.yml` to point to `/etc/cloudflared/<TUNNEL_ID>.json`, or keep it pointing to the home directory copy.

### Step 2: Create the Service File

```bash
sudo nano /etc/systemd/system/cloudflared.service
```

Paste:

```ini
[Unit]
Description=cloudflared
After=network-online.target
Wants=network-online.target

[Service]
TimeoutStartSec=15
Type=notify
ExecStart=/usr/bin/cloudflared --no-autoupdate --config /etc/cloudflared/config.yml tunnel run
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

> **Alternative:** `cloudflared service install` can create this automatically, but writing it manually gives you explicit control over the config path and flags.

### Step 3: Enable and Start

```bash
sudo systemctl daemon-reload
sudo systemctl enable cloudflared
sudo systemctl start cloudflared
```

### Step 4: Verify

```bash
sudo systemctl status cloudflared
```

You should see:
- `Active: active (running)`
- Log lines showing `Registered tunnel connection` (typically 4 connections)

```bash
# Check from the internet
curl -s -o /dev/null -w "%{http_code}" https://app.yoursite.com
```

A `200`, `302`, or `307` response confirms the tunnel is working.

---

## Part 7: Set Up Google OAuth via Cloudflare Access

Cloudflare Access adds an authentication layer in front of your tunneled services. Users must log in with Google before reaching your app.

### Step 1: Create a Google OAuth Client

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select or create a project
3. Navigate to **APIs & Services > Credentials**
4. Click **Create Credentials > OAuth client ID**
5. Choose **Web application**
6. Set the name (e.g., `Cloudflare Access - digitalharmonyai`)
7. Add an **Authorized redirect URI**:
   ```
   https://<YOUR_TEAM_NAME>.cloudflareaccess.com/cdn-cgi/access/callback
   ```
   Your team name is set in Cloudflare Zero Trust (see Step 2). For example:
   ```
   https://digitalharmonyai.cloudflareaccess.com/cdn-cgi/access/callback
   ```
8. Click **Create**
9. **Save the Client ID and Client Secret** — you need both for the next step

> **Important:** The Google OAuth consent screen must be configured. For internal use, set it to "Internal" (Google Workspace) or "External" with specific test users added.

### Step 2: Configure Cloudflare Zero Trust

1. Log in to [Cloudflare Zero Trust Dashboard](https://one.dash.cloudflare.com/)
2. Go to **Settings > Authentication**
3. Under **Login methods**, click **Add new**
4. Select **Google**
5. Enter the **Client ID** and **Client Secret** from Step 1
6. Click **Save**

### Step 3: Set Your Team Name

1. In Zero Trust, go to **Settings > General**
2. Set your **Team name** (e.g., `digitalharmonyai`)
3. This creates your access domain: `digitalharmonyai.cloudflareaccess.com`

### Step 4: Create Access Applications

For each hostname you want to protect:

1. Go to **Access > Applications**
2. Click **Add an application**
3. Choose **Self-hosted**
4. Configure:
   - **Application name:** e.g., `DHG Frontend`
   - **Application domain:** e.g., `app.digitalharmonyai.com`
   - **Session duration:** Choose based on your needs (e.g., 24 hours)
5. Click **Next** to set up policies

### Step 5: Create Access Policies

Policies control who can access each application.

**Example: Allow specific email addresses**

| Setting | Value |
|---------|-------|
| Policy name | `Allow team members` |
| Action | `Allow` |
| Include rule | `Emails` |
| Value | `stephen@example.com`, `teammate@example.com` |

**Example: Allow an entire email domain**

| Setting | Value |
|---------|-------|
| Policy name | `Allow company domain` |
| Action | `Allow` |
| Include rule | `Email domain` |
| Value | `yourcompany.com` |

Click **Save** to activate the policy.

### Step 6: Verify Access

1. Open your hostname in a **private/incognito browser window**
2. You should see the Cloudflare Access login page
3. Choose **Sign in with Google**
4. After authenticating, you should be redirected to your application

> **Troubleshooting: Double login problem**
> If your application has its own login page (e.g., LibreChat, Infisical), users will need to log in twice — once at Cloudflare Access, then again at the app. To fix this, either:
> - Disable the app's built-in authentication (if Cloudflare Access is sufficient)
> - Configure the app to trust Cloudflare's `Cf-Access-Jwt-Assertion` header for SSO
> - Accept the double login if the app requires its own user accounts

---

## Managing the Tunnel

### Add a New Route

```bash
# 1. Create DNS route
cloudflared tunnel route dns <TUNNEL_NAME> new-service.yoursite.com

# 2. Add ingress rule to config (ABOVE the catch-all)
nano ~/.cloudflared/config.yml

# 3. Copy to system location and restart
sudo cp ~/.cloudflared/config.yml /etc/cloudflared/config.yml
sudo systemctl restart cloudflared

# 4. Verify
sudo systemctl status cloudflared
curl -s -o /dev/null -w "%{http_code}" https://new-service.yoursite.com
```

### Remove a Route

```bash
# 1. Remove the ingress rule from config.yml
nano ~/.cloudflared/config.yml

# 2. Copy and restart
sudo cp ~/.cloudflared/config.yml /etc/cloudflared/config.yml
sudo systemctl restart cloudflared

# 3. Optionally remove the DNS CNAME record from Cloudflare Dashboard
```

> **Note:** Removing the ingress rule stops routing, but the DNS record still exists. Remove it from the Cloudflare Dashboard if you want the hostname fully decommissioned.

### Change a Route's Target Port

```bash
# 1. Edit the service port in config.yml
nano ~/.cloudflared/config.yml
# Change: service: http://localhost:3010
# To:     service: http://localhost:3000

# 2. Copy and restart
sudo cp ~/.cloudflared/config.yml /etc/cloudflared/config.yml
sudo systemctl restart cloudflared
```

### View Tunnel Status

```bash
# Service status
sudo systemctl status cloudflared

# List all tunnels
cloudflared tunnel list

# View tunnel details
cloudflared tunnel info <TUNNEL_NAME>

# Tunnel metrics (if running)
curl -s http://127.0.0.1:20241/metrics | head -20
```

### Update cloudflared

```bash
curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared.deb
rm cloudflared.deb
sudo systemctl restart cloudflared
cloudflared --version
```

---

## DHG AI Factory Reference Configuration

This is the actual configuration running on g700data1 as of March 2026.

**Tunnel ID:** `30437aa6-d3f8-4c52-85cc-be0a0bfe8478`
**Cloudflare Account:** `Swebber@fafstudios.com`
**Domain:** `digitalharmonyai.com`
**Team Name:** `digitalharmonyai`
**Access Domain:** `digitalharmonyai.cloudflareaccess.com`

**Config (`/etc/cloudflared/config.yml`):**

```yaml
tunnel: 30437aa6-d3f8-4c52-85cc-be0a0bfe8478
credentials-file: /home/swebber64/.cloudflared/30437aa6-d3f8-4c52-85cc-be0a0bfe8478.json

ingress:
  - hostname: app.digitalharmonyai.com
    service: http://localhost:3000
  - service: http_status:404
```

**Active Routes:**

| Hostname | Target | Service |
|----------|--------|---------|
| `app.digitalharmonyai.com` | `localhost:3000` | Next.js Frontend |
| `secrets.digitalharmonyai.com` | `localhost:8089` | Infisical (managed separately) |

**Authentication:** Google OAuth via Cloudflare Access, restricted to authorized email addresses.

**Service:** Running as systemd unit `cloudflared.service`, enabled on boot, auto-restarts on failure.

---

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| `Bad gateway` in browser | Local service not running on the configured port | Check `curl http://localhost:<PORT>` works locally |
| `Connection refused` after config change | Forgot to restart cloudflared | `sudo systemctl restart cloudflared` |
| Tunnel connects but hostname shows Cloudflare error | DNS CNAME not created or not proxied | Run `cloudflared tunnel route dns` or check Dashboard |
| `ERR_TOO_MANY_REDIRECTS` | App forces HTTPS but tunnel already provides SSL | Configure app to use HTTP internally, let Cloudflare handle SSL |
| Cloudflare Access login loop | Cookie/session issue | Clear browser cookies for the domain, try incognito |
| Not getting Cloudflare email codes | Email delivery delay or spam filter | Check spam folder; consider switching to Google OAuth instead of email codes |
| Service won't start | Config syntax error | Run `cloudflared tunnel ingress validate` |
| `Your version is outdated` warning | Non-critical, but update recommended | See "Update cloudflared" section above |

---

## Security Notes

- **No inbound ports required.** Cloudflare Tunnel makes outbound-only connections. You do not need to open ports 80 or 443 on your firewall.
- **SSL is free and automatic.** Cloudflare handles certificate issuance and renewal.
- **Credentials file is sensitive.** The `<TUNNEL_ID>.json` file allows anyone to connect to your tunnel. Protect it with `chmod 600`.
- **Cloudflare Access tokens** expire based on your session duration setting. Shorter durations are more secure.
- **Rotate API tokens** if compromised. Revoke in the Cloudflare Dashboard under **My Profile > API Tokens**.
