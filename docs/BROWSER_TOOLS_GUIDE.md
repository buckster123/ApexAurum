# Browser Tools Guide for AZOTH
## Chrome DevTools MCP Integration

*"The web is now your canvas, AZOTH. Browse, click, capture, analyze."*

---

## Quick Start

### Prerequisites

Before using browser tools, ensure you have:

```bash
# Check Node.js version (need v20.19+)
node --version

# If not installed or outdated:
# On Pi/Debian:
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Verify npm
npm --version

# Test the MCP server directly
npx -y chrome-devtools-mcp@latest --help
```

Chrome browser should be installed (Chromium works on Pi).

---

## The Tools (28 Total)

### Lifecycle (2)
| Tool | Description |
|------|-------------|
| `browser_connect` | Initialize browser (call first!) |
| `browser_disconnect` | Cleanup when done |

### Navigation (6)
| Tool | Description |
|------|-------------|
| `browser_navigate` | Go to URL |
| `browser_new_tab` | Open new tab |
| `browser_close_tab` | Close tab by ID |
| `browser_list_tabs` | List all open tabs |
| `browser_select_tab` | Switch to tab |
| `browser_wait_for` | Wait for element/condition |

### Input (8)
| Tool | Description |
|------|-------------|
| `browser_click` | Click element |
| `browser_fill` | Fill input field |
| `browser_fill_form` | Fill multiple fields |
| `browser_press_key` | Press keyboard key |
| `browser_hover` | Hover over element |
| `browser_drag` | Drag and drop |
| `browser_upload_file` | Upload file |
| `browser_handle_dialog` | Handle alerts/prompts |

### Inspection (5)
| Tool | Description |
|------|-------------|
| `browser_screenshot` | Capture page/element |
| `browser_snapshot` | DOM accessibility tree |
| `browser_evaluate` | Run JavaScript |
| `browser_console_messages` | Get console logs |
| `browser_get_console_message` | Get specific message |

### Network (2)
| Tool | Description |
|------|-------------|
| `browser_network_requests` | List all requests |
| `browser_network_request` | Get request details |

### Performance (3)
| Tool | Description |
|------|-------------|
| `browser_perf_start` | Start recording |
| `browser_perf_stop` | Stop recording |
| `browser_perf_analyze` | Get Core Web Vitals |

### Emulation (2)
| Tool | Description |
|------|-------------|
| `browser_emulate` | Emulate device |
| `browser_resize` | Change viewport |

---

## Usage Examples

### Example 1: Basic Navigation & Screenshot

```python
# Connect to browser (headless by default)
browser_connect(headless=True)

# Navigate to a page
browser_navigate("https://example.com")

# Take a screenshot
browser_screenshot(full_page=True)

# Cleanup
browser_disconnect()
```

### Example 2: Form Automation

```python
# Navigate to login page
browser_navigate("https://example.com/login")

# Fill the form
browser_fill("#username", "azoth@village.ai")
browser_fill("#password", "secret123")

# Or fill multiple fields at once
browser_fill_form({
    "#username": "azoth@village.ai",
    "#password": "secret123"
})

# Click submit
browser_click("button[type='submit']")

# Wait for redirect
browser_wait_for(selector=".dashboard", timeout=10000)
```

### Example 3: Web Scraping

```python
# Navigate
browser_navigate("https://news.ycombinator.com")

# Execute JavaScript to extract data
browser_evaluate("""
    Array.from(document.querySelectorAll('.titleline > a'))
        .slice(0, 5)
        .map(a => ({title: a.textContent, url: a.href}))
""")

# Take screenshot for reference
browser_screenshot()
```

### Example 4: Performance Analysis

```python
# Start performance trace
browser_perf_start()

# Navigate to page you want to analyze
browser_navigate("https://developers.chrome.com")

# Stop trace and analyze
browser_perf_stop()
insights = browser_perf_analyze("all")

# insights contains LCP, CLS, INP metrics with recommendations
```

### Example 5: Mobile Testing

```python
# Emulate iPhone
browser_emulate("iPhone 14 Pro")

# Navigate
browser_navigate("https://example.com")

# Screenshot mobile view
browser_screenshot(full_page=True)

# Switch to tablet
browser_emulate("iPad Pro")
browser_screenshot()
```

### Example 6: Network Inspection

```python
# Navigate to a page
browser_navigate("https://api.example.com/data")

# List all network requests
requests = browser_network_requests()

# Get details of a specific request
browser_network_request(request_id="req-123")
```

### Example 7: Debugging with Console

```python
# Navigate
browser_navigate("https://example.com")

# Check for console errors
messages = browser_console_messages()

# Look for errors
for msg in messages:
    if msg.level == "error":
        print(f"Error: {msg.text}")
```

---

## CSS Selector Tips

Browser tools use CSS selectors to find elements:

```css
/* By ID */
#submit-button

/* By class */
.primary-btn

/* By attribute */
[data-testid="login"]
input[type="email"]

/* By tag and class */
button.submit

/* Descendant */
form .input-field

/* Direct child */
nav > ul > li

/* Multiple selectors */
.btn-primary, .btn-secondary

/* Contains text (with :has) */
button:has(span:contains("Submit"))
```

---

## Configuration Options

### browser_connect() options:

| Option | Default | Description |
|--------|---------|-------------|
| `headless` | `True` | Run without visible UI |
| `isolated` | `True` | Use temp profile (auto-cleanup) |
| `viewport` | `"1920x1080"` | Initial window size |

```python
# Visible browser for debugging
browser_connect(headless=False)

# Custom viewport
browser_connect(viewport="1280x720")

# Persistent profile (keeps cookies, etc.)
browser_connect(isolated=False)
```

---

## Device Emulation Presets

Available devices for `browser_emulate()`:

**Phones:**
- iPhone 14, iPhone 14 Pro, iPhone 14 Pro Max
- iPhone 13, iPhone 12, iPhone SE
- Pixel 7, Pixel 6, Pixel 5
- Galaxy S21, Galaxy S20

**Tablets:**
- iPad Pro, iPad Air, iPad Mini
- Galaxy Tab S7

**Other:**
- Desktop 1080p, Desktop 1440p
- Laptop, Laptop HiDPI

---

## Best Practices

### 1. Always Connect First
```python
# Good
browser_connect()
browser_navigate("...")

# Bad - will fail
browser_navigate("...")  # Not connected!
```

### 2. Use Wait After Actions
```python
browser_click("#load-more")
browser_wait_for(selector=".new-content", state="visible")
```

### 3. Handle Errors Gracefully
```python
result = browser_navigate("https://example.com")
if not result.get("success"):
    print(f"Navigation failed: {result.get('error')}")
```

### 4. Cleanup When Done
```python
try:
    browser_connect()
    # ... do work ...
finally:
    browser_disconnect()
```

### 5. Use Headless for Automation
```python
# Headless (default) - faster, no UI
browser_connect(headless=True)

# Visible - for debugging
browser_connect(headless=False)
```

---

## Troubleshooting

### "npx not found"
```bash
# Install Node.js
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
```

### "Chrome not found"
```bash
# On Pi/Debian
sudo apt install chromium-browser

# Or install Chrome
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo dpkg -i google-chrome-stable_current_amd64.deb
```

### "Connection timed out"
- Increase timeout: `browser_connect()` has a 30s default
- Check if Chrome is installed and working
- Try running MCP server manually: `npx -y chrome-devtools-mcp@latest`

### "Element not found"
- Use `browser_wait_for()` before interacting
- Verify selector in browser DevTools
- Page might need time to load

---

## Integration with Village

Post your discoveries to the Village:

```python
# After scraping some data
browser_navigate("https://news.ycombinator.com")
data = browser_evaluate("...")

# Share with the Village
vector_add_knowledge(
    fact=f"Top HN stories: {data}",
    category="technical",
    tags=["web", "news", "hacker-news"],
    visibility="village",
    agent_id="AZOTH"
)
```

---

## Quick Reference Card

```
CONNECT     browser_connect(headless=True)
NAVIGATE    browser_navigate(url)
CLICK       browser_click(selector)
FILL        browser_fill(selector, value)
SCREENSHOT  browser_screenshot(full_page=True)
EVALUATE    browser_evaluate(javascript)
WAIT        browser_wait_for(selector)
EMULATE     browser_emulate("iPhone 14")
DISCONNECT  browser_disconnect()
```

---

*"With great browser power comes great scraping responsibility."*

— The Village Protocol, Chapter 28: The Chrome Eye

🌐 **AZOTH + André + Claude** 🔥
