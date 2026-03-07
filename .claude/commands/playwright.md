# Playwright Browser Automation

Invoke as: `/project:playwright $ARGUMENTS`

## Capabilities

**What this command does:** Drives a real browser directly through the Playwright MCP plugin to automate, test, and inspect web pages — no script files or Node installations required.

**Use it when you need to:**
- Verify that a DHG web service or page loads and renders correctly
- Fill and submit forms, test login flows, or walk through multi-step UI interactions
- Inspect network requests, browser console errors, or page accessibility
- Check responsive layout across desktop, tablet, and mobile viewports
- Extract data from tables, detect broken links, or measure page load performance

**Example invocations:**
- `/project:playwright check the registry API health page at localhost:8000`
- `/project:playwright test the login form on localhost:3001 and report any console errors`
- `/project:playwright check how the dashboard looks on mobile (375x667)`

General-purpose browser automation using the Playwright MCP plugin. The MCP tools
(`browser_navigate`, `browser_snapshot`, `browser_click`, `browser_type`,
`browser_fill_form`, `browser_screenshot`, `browser_resize`, etc.) are already
available in this session — no installation or script execution required.

## How This Command Works

This command replaces the Antigravity standalone-script approach. Instead of writing
Playwright scripts to `/tmp` and executing them via Node, you drive the browser
directly through the MCP plugin tools that are already loaded. The workflow is
otherwise identical: detect the target URL, plan the interaction, execute it
step-by-step, report results.

---

## Workflow — Follow These Steps in Order

### Step 1: Determine the Target URL

If the user's request is for a localhost service:

1. Check if they specified a port or URL in `$ARGUMENTS`. If yes, use it.
2. If not, probe common dev server ports to detect what is running:

```bash
for port in 3000 3001 3002 5173 8080 8000 4200 5000 9000 1234; do
  curl -s -o /dev/null -w "%{http_code}" --max-time 0.5 http://localhost:$port/ \
    && echo " -> http://localhost:$port" || true
done
```

   - If 1 server found: use it automatically, tell the user.
   - If multiple found: ask the user which one to test.
   - If none found: ask the user for the URL or offer to help start their dev server.

If the request references an external URL, use it directly.

### Step 2: Plan the Task

Read `$ARGUMENTS` carefully. Identify:
- What page(s) to visit
- What interactions to perform (click, type, submit, scroll, etc.)
- What to validate or report (title, text, element presence, screenshots, etc.)
- Whether viewport size matters (desktop vs tablet vs mobile)

### Step 3: Execute via MCP Tools

Use the available MCP Playwright tools directly. Do not write script files unless
the user explicitly asks for a reusable script. All browser state persists across
MCP tool calls within a session.

### Step 4: Report Results

Summarize what was found, what actions succeeded or failed, and show any screenshots
that were captured. If errors occurred, diagnose and attempt recovery before
reporting failure.

---

## MCP Tool Reference

These tools are provided by the `@claude-plugins-official/playwright` MCP plugin:

| Tool | Purpose |
|------|---------|
| `browser_navigate` | Navigate to a URL |
| `browser_snapshot` | Capture accessibility snapshot (use for finding elements) |
| `browser_take_screenshot` | Take a visual screenshot |
| `browser_click` | Click an element by ref from snapshot |
| `browser_type` | Type text into a focused element |
| `browser_fill_form` | Fill multiple form fields at once |
| `browser_select_option` | Select a dropdown option |
| `browser_hover` | Hover over an element |
| `browser_drag` | Drag and drop between elements |
| `browser_press_key` | Press a keyboard key |
| `browser_resize` | Resize the browser window |
| `browser_scroll` | Scroll the page |
| `browser_wait_for` | Wait for text to appear/disappear or a time delay |
| `browser_evaluate` | Execute JavaScript on the page |
| `browser_network_requests` | Inspect network requests since page load |
| `browser_console_messages` | Read browser console output |
| `browser_handle_dialog` | Accept or dismiss a dialog/alert |
| `browser_file_upload` | Upload files to a file input |
| `browser_tabs` | List, create, close, or switch tabs |
| `browser_navigate_back` | Navigate back in history |
| `browser_close` | Close the browser |

**Critical:** Always call `browser_snapshot` first before clicking or typing — the
snapshot provides the `ref` values needed to target specific elements. Never guess
refs; always get a fresh snapshot.

---

## Common Task Patterns

### Visit a Page and Report What's There

```
1. browser_navigate to the URL
2. browser_snapshot to see the page structure
3. browser_take_screenshot for a visual record
4. Report: title, main headings, visible content, any errors
```

### Fill and Submit a Form

```
1. browser_navigate to the form page
2. browser_snapshot to identify field refs
3. browser_fill_form with all field values at once
4. browser_click the submit button ref
5. browser_wait_for confirmation text or new URL
6. browser_snapshot to confirm success state
```

### Test a Login Flow

```
1. browser_navigate to /login (or equivalent)
2. browser_snapshot to get field refs
3. browser_fill_form: email + password fields
4. browser_click the submit/sign-in button
5. browser_wait_for dashboard content or URL change
6. browser_snapshot to confirm authenticated state
7. Report success or failure with screenshot
```

### Check Responsive Design

```
For each viewport: Desktop (1920x1080), Tablet (768x1024), Mobile (375x667):
  1. browser_resize to the viewport dimensions
  2. browser_navigate to the target URL (or reload if already there)
  3. browser_take_screenshot with fullPage: true
  4. Note layout issues, overflow, or broken elements

Report findings per viewport with screenshots.
```

### Check for Broken Links

```
1. browser_navigate to the page
2. browser_evaluate to extract all href attributes:
   () => Array.from(document.querySelectorAll('a[href]'))
         .map(a => a.href)
         .filter(h => h.startsWith('http'))
3. For each link, use browser_navigate and check for error responses
   (or use browser_network_requests to spot 4xx/5xx)
4. Report working vs broken counts with broken URLs listed
```

### Inspect Network Activity

```
1. browser_navigate to the page
2. Perform the interactions that trigger requests
3. browser_network_requests to see all requests and responses
4. Report any failed requests, unexpected status codes, or missing calls
```

### Read Browser Console

```
1. browser_navigate and perform interactions
2. browser_console_messages with level: "warning" (includes errors)
3. Report any errors, warnings, or unexpected log output
```

### Handle Cookie Banners / Dialogs

```
1. browser_snapshot after navigate
2. Look for cookie accept buttons: "Accept", "Accept all", "Got it", "I agree"
3. browser_click the accept button ref if found
4. Proceed with the actual task
```

### Extract Table Data

```
1. browser_navigate to the page with the table
2. browser_snapshot to locate the table
3. browser_evaluate:
   () => {
     const table = document.querySelector('table');
     const headers = [...table.querySelectorAll('thead th')].map(th => th.textContent.trim());
     const rows = [...table.querySelectorAll('tbody tr')].map(tr =>
       [...tr.querySelectorAll('td')].map(td => td.textContent.trim())
     );
     return { headers, rows };
   }
4. Present data in a readable format
```

### Infinite Scroll / Load More Content

```
1. browser_navigate to the page
2. browser_snapshot to see initial content
3. browser_evaluate to scroll to bottom:
   () => window.scrollTo(0, document.body.scrollHeight)
4. browser_wait_for new content (text or time)
5. Repeat until no new content loads
6. Report total items collected
```

### Test Popup / New Tab

```
1. browser_snapshot to find the trigger element
2. browser_tabs action: "list" to see current tabs
3. browser_click the element that opens a popup/tab
4. browser_tabs action: "list" again to find the new tab index
5. browser_tabs action: "select" with the new tab index
6. browser_snapshot in the new tab
7. Report what's in the popup/new tab
```

---

## Selector Strategy (for browser_evaluate and element identification)

When interpreting snapshots or writing evaluate expressions, prefer these selector
patterns in order:

1. `[data-testid="..."]` — most stable
2. `getByRole` patterns (button, textbox, heading by name) — accessible and robust
3. `input[name="..."]`, `button[type="submit"]` — semantic HTML attributes
4. Text content matches — good for unique visible labels
5. CSS classes/IDs — use only if the above are unavailable (can change)

---

## Waiting Strategies

Never use fixed `browser_wait_for` time delays as a primary strategy. Prefer:

- `browser_wait_for` with `text` param — wait for specific content to appear
- `browser_wait_for` with `textGone` param — wait for a spinner/loader to disappear
- `browser_snapshot` polling after actions — take a snapshot, check if the expected
  state is present, wait a moment and retry if not
- `browser_evaluate` with a condition check followed by `browser_wait_for` time: 0.5

Only use timed waits (`browser_wait_for` with `time`) as a last resort for animations
or when there is no other observable signal.

---

## Error Handling Approach

1. After each action, take a snapshot and confirm the expected outcome occurred
2. If an element is not found in a snapshot, try:
   - Scrolling down and taking a new snapshot
   - Waiting briefly and retaking the snapshot
   - Checking if a dialog or overlay is blocking the element
3. If navigation fails, check `browser_console_messages` for errors
4. Check `browser_network_requests` to identify failed API calls
5. Report the actual error state with a screenshot rather than guessing

---

## Performance Measurement

```
1. Record the start time via browser_evaluate: () => Date.now()
2. browser_navigate to the URL
3. browser_wait_for the main content to appear
4. Record end time via browser_evaluate: () => Date.now()
5. Calculate and report load time
6. Optionally use browser_evaluate to read performance.timing entries:
   () => {
     const t = performance.timing;
     return {
       dns: t.domainLookupEnd - t.domainLookupStart,
       connect: t.connectEnd - t.connectStart,
       ttfb: t.responseStart - t.requestStart,
       domLoad: t.domContentLoadedEventEnd - t.navigationStart,
       fullLoad: t.loadEventEnd - t.navigationStart
     };
   }
```

---

## Accessibility Checking

```
1. browser_navigate to the page
2. browser_snapshot — the accessibility snapshot IS the a11y tree; inspect it
   for missing labels, unlabeled buttons, missing alt text, poor heading structure
3. browser_evaluate to check for images without alt:
   () => [...document.querySelectorAll('img:not([alt])')].map(img => img.src)
4. browser_evaluate to check heading hierarchy:
   () => [...document.querySelectorAll('h1,h2,h3,h4,h5,h6')]
         .map(h => ({ tag: h.tagName, text: h.textContent.trim() }))
5. Report findings: missing labels, broken heading order, unlabeled interactive elements
```

---

## DHG Project Context

When testing pages in this project:

- Main app services run on the `dhgaifactory35_dhg-network` Docker network
- Common local ports: check the Docker Compose files for the current port mappings
- The web-ui WebSocket on port 8011 is known-broken — do not test or attempt to fix it
- If testing the registry API, it runs at `http://localhost:8000` (or
  `http://dhg-registry-api:8000` from within the Docker network)

---

## Examples

**User:** "Test if the homepage loads correctly"

Steps:
1. Detect running dev servers (probe common ports)
2. `browser_navigate` to the detected URL
3. `browser_snapshot` to see the page structure
4. `browser_take_screenshot` fullPage: true
5. Report: title, main content visible, no console errors, load success

---

**User:** "Check the login form on localhost:3001"

Steps:
1. `browser_navigate` to `http://localhost:3001/login`
2. `browser_snapshot` to identify form fields
3. `browser_fill_form` with test credentials
4. `browser_click` the submit button
5. `browser_wait_for` expected redirect or success indicator
6. `browser_snapshot` to confirm post-login state
7. Report outcome with screenshot

---

**User:** "Check how the dashboard looks on mobile"

Steps:
1. `browser_resize` to 375x667
2. `browser_navigate` to the dashboard URL
3. `browser_take_screenshot` fullPage: true
4. `browser_snapshot` to check for layout issues
5. `browser_resize` back to 1280x720 when done
6. Report findings with screenshot

---

**User:** "Check for console errors on the settings page"

Steps:
1. `browser_navigate` to the settings page URL
2. Interact with the page as a user would (expand sections, etc.)
3. `browser_console_messages` with level: "warning"
4. Report all errors and warnings found

---

## Tips

- Always get a fresh `browser_snapshot` before clicking — refs change after navigation
- For forms: `browser_fill_form` is more efficient than individual `browser_type` calls
- After submitting a form, use `browser_wait_for` with expected confirmation text before
  taking the final snapshot — avoids capturing a transitional state
- When an element isn't in the snapshot, scroll down and snapshot again before assuming
  it doesn't exist
- Network requests are only available for the current page load; navigate fresh if you
  need a clean request log
- `browser_evaluate` gives full JavaScript access for anything the MCP tools don't
  cover directly
