# Live Firecrawl Examples

Recorded from sessions on 2026-07-24. All examples produced real output from live Firecrawl MCP tools.

## 1. Scrape -- Markdown mode

```python
mcp_firecrawl_firecrawl_scrape(
    url="https://example.com",
    formats=["markdown"],
    onlyMainContent=True
)
# Returns: full page markdown
# Cost: 1 credit
```

## 2. Scrape -- JSON mode with schema

```python
mcp_firecrawl_firecrawl_scrape(
    url="https://example.com",
    formats=["json"],
    jsonOptions={
        "prompt": "Extract the domain name, description, and any links on the page",
        "schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "description": {"type": "string"},
                "links": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string"},
                            "url": {"type": "string"}
                        }
                    }
                }
            }
        }
    }
)
# Returns: {title, description, links: [{text, url}]}
# Cost: ~5 credits
```

## 3. Web search

```python
mcp_firecrawl_firecrawl_search(
    query="best AI coding assistants 2025",
    limit=3
)
# Returns: {web: [{url, title, description}]}
# Cost: 2 credits
# Then call firecrawl_search_feedback with the searchId
```

## 4. Map -- discover URLs

```python
mcp_firecrawl_firecrawl_map(
    url="https://news.ycombinator.com",
    limit=5
)
# Returns: {links: [{url, title}]}
```

## 5. Extract -- from multiple pages (deprecated)

```python
mcp_firecrawl_firecrawl_extract(
    urls=["https://example.com", "https://httpbin.org"],
    prompt="Extract the homepage title and main description from these pages"
)
# Returns: {homepageTitle, mainDescription}
# Cost: 23 credits
# Warning: deprecated, use scrape + JSON format instead
```

## 6. Agent -- autonomous research (async)

```python
# Phase 1: Start
mcp_firecrawl_firecrawl_agent(
    prompt="Find the pricing page for Firecrawl.dev and tell me what plans they offer"
)
# Returns: {id: "019f937a-0852-..."}

# Phase 2: Poll (15-30s intervals, 2-5 min typical)
mcp_firecrawl_firecrawl_agent_status(id="019f937a-0852-...")
# Returns: {status: "processing"|"completed"|"failed", data?: {...}}
```

## 7. Monitor -- full lifecycle

```python
# --- CREATE ---
mcp_firecrawl_firecrawl_monitor_create(
    page="https://cursor.com/pricing",
    goal="Alert when any pricing tier name, price, billing period, or features change",
    scheduleText="every 6 hours"
)
# Returns: {id: "mon_019f9384-4562-...", status: "active", nextRunAt: "..."}

# --- RUN IMMEDIATELY ---
mcp_firecrawl_firecrawl_monitor_run(id="mon_019f9384-4562-...")
# Returns: {id: "chk_...", status: "queued"}

# --- LIST CHECKS ---
mcp_firecrawl_firecrawl_monitor_checks(
    id="mon_019f9384-4562-...",
    status="completed"
)
# Returns: [{id: "chk_...", status: "completed", summary: {new, changed, same, removed, error}}]

# --- VIEW CHECK DETAILS ---
mcp_firecrawl_firecrawl_monitor_check(
    id="mon_019f9384-4562-...",
    checkId="chk_019f9384-5402-..."
)
# Returns:
# pages: [{
#   url: "https://cursor.com/pricing",
#   status: "new",  # or "changed", "same", "removed"
#   diff: {text: "...", json: {...}},  # present when changed
#   judgment: {meaningful: true/false, reason: "..."}  # AI analysis
# }]

# --- LIST ALL MONITORS ---
mcp_firecrawl_firecrawl_monitor_list()

# --- DELETE ---
mcp_firecrawl_firecrawl_monitor_delete(id="mon_019f9384-4562-...")
```

**Monitor output from first check (baseline):**
```
status: "completed"
summary: {totalPages: 1, same: 0, changed: 0, new: 1, removed: 0}
```

## 8. Competitive Analysis -- 3 competitors in parallel

```python
# Schema shared across all competitors
schema = {
    "type": "object",
    "properties": {
        "headline":          {"type": "string"},
        "sub_headline":      {"type": "string"},
        "value_proposition": {"type": "string"},
        "cta_text":          {"type": "string"},
        "pricing_signal":    {"type": "string"},
        "target_audience":   {"type": "string"}
    }
}

# Call in parallel (separate tool invocations):
mcp_firecrawl_firecrawl_scrape(
    url="https://cursor.com",
    formats=["json"],
    jsonOptions={"prompt": "Extract...", "schema": schema}
)
mcp_firecrawl_firecrawl_scrape(
    url="https://github.com/features/copilot",
    formats=["json"],
    jsonOptions={"prompt": "Extract...", "schema": schema}
)
mcp_firecrawl_firecrawl_scrape(
    url="https://www.augmentcode.com",
    formats=["json"],
    jsonOptions={"prompt": "Extract...", "schema": schema}
)
```

**Result comparison table (produced manually from outputs):**

| Field | Cursor | GitHub Copilot | Augment Code |
|---|---|---|---|
| Headline | "...your coding agent..." | "Your AI accelerator" | "Orchestrate agents across your SDLC" |
| Value Prop | Agents turn ideas into code | AI throughout SDLC | Cosmos -- agent orchestration platform |
| CTA | Get started | Get started | Book a demo |
| Pricing | Free | Free / from $10/mo | Try Cosmos free |
| Audience | Developers & teams | Individuals, freelancers, business | Engineering teams |

## 9. Credit balance check

```bash
# API key is stored in MCP_FIRECRAWL_API_KEY in .env
source /c/Users/Admin/AppData/Local/hermes/.env 2>/dev/null
curl -s -X GET "https://api.firecrawl.dev/v1/team/credit-usage" \
  -H "Authorization: Bearer $MCP_FIRECRAWL_API_KEY"
# Returns: {remaining_credits, plan_credits, billing_period_start, billing_period_end}
```

**Example output (2026-07-24):**
```json
{
  "remaining_credits": 1021,
  "plan_credits": 1000,
  "billing_period_start": "2026-07-19T12:17:11.858Z",
  "billing_period_end": "2026-08-19T12:17:11.858Z"
}
```
