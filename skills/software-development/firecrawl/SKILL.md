---
name: firecrawl
description: "Use when web scraping, searching, crawling, or extracting structured data from websites via Firecrawl MCP tools. Covers scrape, search, crawl, map, extract, agent, parse, and interact."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [firecrawl, web-scraping, search, data-extraction, crawling]
    related_skills: []
---

# Firecrawl Web Scraping & Data Extraction

## Overview

Firecrawl is a web data platform available through Hermes MCP. It provides a suite of tools for scraping, searching, crawling, and extracting structured data from the web. Each tool has a specific purpose and credit cost.

The tools are accessed via `mcp_firecrawl_*` functions. All require a valid `MCP_FIRECRAWL_API_KEY` (set in `.env` as `fc-...`).

## Tool Reference

### `firecrawl_scrape` — Scrape a single URL
| Aspect | Detail |
|---|---|
| **Cost** | 1 credit (markdown), ~5 credits (JSON with schema) |
| **Best for** | Reading a specific page you already know the URL of |
| **Formats** | `markdown` (default), `json` + schema (structured), `screenshot`, `branding`, `query`, `html` |

**Markdown mode** (full page content):
```
firecrawl_scrape(url="https://...", formats=["markdown"], onlyMainContent=true)
```

**JSON mode** (specific data points — PREFERRED for extraction):
```
firecrawl_scrape(url="https://...", formats=["json"],
  jsonOptions={prompt: "Extract X", schema: {type: "object", properties: {...}}})
```

### `firecrawl_search` — Web search
| Aspect | Detail |
|---|---|
| **Cost** | 2 credits |
| **Best for** | Finding pages on a topic when you don't know the URL |
| **Sources** | `web`, `images`, `news` |

Always call `firecrawl_search_feedback(searchId, rating, ...)` after using results — refunds 1 credit.

```
firecrawl_search(query="...", limit=5, sources=[{type:"web"}])
```

### `firecrawl_crawl` — Crawl a website
| Aspect | Detail |
|---|---|
| **Cost** | 1 credit per crawled page |
| **Best for** | Getting all pages from a site or section |
| **Warning** | Default limit is 10,000 — ALWAYS set an explicit `limit` or pre-flight credit check will fail if balance < 10,000 |

```
firecrawl_crawl(url="https://example.com/blog/*", limit=20, maxDiscoveryDepth=2)
```

### `firecrawl_map` — Discover URLs on a site
| Aspect | Detail |
|---|---|
| **Cost** | Low (cheaper than crawl for discovery) |
| **Best for** | Finding the right URL when scrape returns empty or irrelevant content |
| **Pattern** | map → then scrape the found URL |

```
firecrawl_map(url="https://...", search="webhook events")
```

**IMPORTANT**: When `firecrawl_scrape` returns empty/minimal content, use `map` with `search` before reaching for `firecrawl_agent`. It's faster and cheaper.

### `firecrawl_extract` — Extract from multiple URLs (DEPRECATED)
| Aspect | Detail |
|---|---|
| **Cost** | ~23 credits |
| **Status** | Deprecated — use `firecrawl_scrape` with `formats: ["json"]` instead |
| **Best for** | Legacy use; prefer scrape + JSON |

### `firecrawl_agent` — Autonomous research agent
| Aspect | Detail |
|---|---|
| **Cost** | Higher (multi-step) |
| **Best for** | Complex multi-page research where you don't know exact URLs; JS-heavy SPAs that fail with regular scrape |
| **Flow** | Returns job ID immediately → poll with `firecrawl_agent_status` every 15-30s for 2-5 minutes |

```
# Start
firecrawl_agent(prompt="Find X on Y website")
# → returns {id: "uuid..."}

# Poll
firecrawl_agent_status(id="uuid...")
# → returns {status: "completed"|"processing"|"failed", data: {...}}
```

### `firecrawl_monitor_*` — Monitor pages for changes

| Aspect | Detail |
|---|---|
| **Cost** | ~1 credit per check (with judge), ~240/mo at 6h interval |
| **Best for** | Tracking competitor pricing, changelogs, landing page changes |
| **Key feature** | Built-in AI judge filters meaningful changes from noise |

**Simple path — monitor a single page:**
```
firecrawl_monitor_create(
  page="https://competitor.com/pricing",
  goal="Alert when pricing tier name, price, billing period, or features change",
  scheduleText="every 6 hours"
)
# Returns: {id: "mon_...", status: "active"}
```

**Monitor multiple pages:**
```
firecrawl_monitor_create(
  pages=["https://a.com/pricing", "https://a.com/changelog"],
  goal="Alert on pricing or feature announcements",
  webhookUrl="https://..."
)
```

**Search monitor — watch for new search results:**
```
firecrawl_monitor_create(
  queries=["new LLM release", "frontier model launch"],
  goal="Notify me about major new LLM model releases",
  searchWindow="24h",
  maxResults=10
)
```

**Lifecycle commands:**
| Action | Tool |
|---|---|
| Run immediately | `firecrawl_monitor_run(id="mon_...")` |
| List checks | `firecrawl_monitor_checks(id="mon_...", status="completed")` |
| View check details + diff | `firecrawl_monitor_check(id="mon_...", checkId="chk_...")` |
| List all monitors | `firecrawl_monitor_list()` |
| Pause/resume | `firecrawl_monitor_update(id="mon_...", body={status: "paused"})` |
| Delete | `firecrawl_monitor_delete(id="mon_...")` |

**Check detail (shows what changed):**
```
firecrawl_monitor_check(id="mon_...", checkId="chk_...")
# Returns pages[] with status: "new"|"changed"|"same"|"removed"|"error"
# When changed: includes diff (text/json), and judgment (meaningful: true/false)
```

**JSON-mode change tracking** for structured fields:
```
firecrawl_monitor_create(
  body={
    name: "Pricing watch",
    schedule: {text: "hourly"},
    goal: "Alert on pricing tier changes",
    targets: [{
      type: "scrape",
      urls: ["https://.../pricing"],
      scrapeOptions: {
        formats: [{type: "changeTracking", modes: ["json"],
          prompt: "Extract pricing tiers",
          schema: {type: "object", properties: {
            plans: {type: "array", items: {type: "object", properties: {
              name: {type: "string"},
              price: {type: "string"},
              features: {type: "array", items: {type: "string"}}
            }}}
          }}
        }]
      }
    }]
  }
)
# Check response: diff.json has per-field changes like "plans[0].price": {previous, current}
```

### `firecrawl_parse` — Parse local files
| Aspect | Detail |
|---|---|
| **Cost** | Per-file |
| **Best for** | PDFs, Word docs, Excel files, HTML files from disk |
| **Supported** | .html, .pdf, .docx, .odt, .rtf, .xlsx |

In hosted mode (current setup), requires a two-phase flow:
1. Call with `filePath` → returns upload instructions + `uploadRef`
2. Run the returned curl command locally
3. Call again with `uploadRef` to complete

### `firecrawl_interact` — Browser interaction
| Aspect | Detail |
|---|---|
| **Cost** | Per-action |
| **Best for** | Clicking buttons, filling forms, multi-step workflows on dynamic pages |
| **Params** | `url` (fresh page) or `scrapeId` (reuse loaded page); `prompt` or `code` |

```
firecrawl_interact(url="https://...", prompt="Click the first product and tell me its price")
```

## Use Case: Competitive Analysis

Scrape multiple competitor landing pages in parallel with a shared JSON schema. Compare positioning, pricing, and messaging in one pass.

**Workflow:**
1. Define a JSON schema with fields you care about (headline, sub-headline, value prop, CTA, pricing signal, target audience)
2. Call `firecrawl_scrape` with `formats=["json"]` on each competitor URL — run in parallel (separate tool calls)
3. Compare results side by side

**Schema template:**
```json
jsonOptions: {
  "prompt": "Extract the headline, sub-headline, main value proposition, CTA button text, pricing signal (free/paid/from $X), and target audience from this landing page",
  "schema": {
    "type": "object",
    "properties": {
      "headline":             {"type": "string"},
      "sub_headline":         {"type": "string"},
      "value_proposition":    {"type": "string"},
      "cta_text":             {"type": "string"},
      "pricing_signal":       {"type": "string"},
      "target_audience":      {"type": "string"}
    }
  }
}
```

**Cost:** ~5 credits per competitor (parallel → total = 5 × N)

## Use Case: Competitor Monitoring

Track competitor pricing pages, changelogs, or landing pages for changes. Firecrawl Monitor handles scheduling, diffing, and AI-based significance filtering.

**Pricing page monitor (most common):**
```
firecrawl_monitor_create(
  page="https://competitor.com/pricing",
  goal="Alert when any pricing tier name, price, billing period, or features change. Also alert if a new plan is added or an existing one is removed.",
  scheduleText="every 6 hours"
)
```

**Changelog monitor (track new features/releases):**
```
firecrawl_monitor_create(
  page="https://competitor.com/changelog",
  goal="Alert when a new blog post, changelog entry, or product announcement appears",
  scheduleText="every 12 hours"
)
```

**Landing page monitor (positioning changes):**
```
firecrawl_monitor_create(
  page="https://competitor.com",
  goal="Alert if the headline, sub-headline, CTA, or main value proposition changes",
  scheduleText="daily"
)
```

**What a change alert looks like:**
```
check pages[].status = "changed"
  → diff.text (unified diff of markdown) OR
    diff.json (per-field: "plans[0].price": {previous, current})
  → judgment.meaningful (true/false — AI says if it's real or noise)
  → judgment.meaningfulChanges[] (structured: before/after/reason)
```

## Use Case: Content Aggregation

Use `firecrawl_crawl` or `firecrawl_search` + `firecrawl_scrape` to collect content from multiple sources for analysis, summarization, or archiving.

## Credit Balance Check

Check remaining credits via direct API call:

```bash
curl -s -X GET "https://api.firecrawl.dev/v1/team/credit-usage" \
  -H "Authorization: Bearer $MCP_FIRECRAWL_API_KEY"
```

Returns: `{remaining_credits, plan_credits, billing_period_start, billing_period_end}`

The `.env` key is `MCP_FIRECRAWL_API_KEY`. Export it before the curl call:
```bash
source /c/Users/Admin/AppData/Local/hermes/.env 2>/dev/null
# or
export $(grep '^MCP_FIRECRAWL_API_KEY' /c/Users/Admin/AppData/Local/hermes/.env | xargs)
curl -s -X GET "https://api.firecrawl.dev/v1/team/credit-usage" -H "Authorization: Bearer $MCP_FIRECRAWL_API_KEY"
```

## Tool Selection Guide

| Situation | Tool | Credits |
|---|---|---|
| Read a known page | `scrape` (markdown) | 1 |
| Extract specific data from one page | `scrape` (JSON + schema) | ~5 |
| Find pages on a topic | `search` | 2 |
| Discover URLs on a site | `map` | Low |
| Collect content from many pages | `crawl` | 1/page |
| Research across multiple unknown sites | `agent` | Higher |
| Parse a local PDF/Word/Excel | `parse` | Per-file |
| Click/fill forms on a page | `interact` | Per-action |
| **Monitor a page for changes** | **`monitor_create`** | **~1/check** |
| **Compare N competitors** | **`scrape` x N (JSON)** | **~5 x N** |
| **Track pricing pages long-term** | **`monitor_create` + `monitor_check`** | **~240/mo** |

## Common Pitfalls

1. **Not setting `limit` on crawl.** Default is 10,000. Pre-flight check requires balance ≥ that. Always pass explicit `limit`.
2. **Using `extract` instead of `scrape` + JSON.** Extract is deprecated. Use `scrape` with `formats: ["json"]` and a `jsonOptions.schema`.
3. **Using `agent` before `map` + `scrape`.** When a page returns empty content, `map` with `search` first. Agent is the last resort — it's slower and more expensive.
4. **Not polling `agent` long enough.** Agents take 1-5 minutes. Poll every 15-30 seconds for at least 2-3 minutes before giving up.
5. **Forgetting search feedback.** Call `firecrawl_search_feedback(searchId, rating, ...)` after using search results to get a 1-credit refund.
6. **JSON schema on heavy JS pages.** If JSON returns nav-only content, add `waitFor: 5000-10000` to allow JS to render. If still fails, try `map` to find the right URL.
7. **MaxAge for performance.** Add `maxAge` parameter for ~500% faster scrapes from cached data.
8. **Forgetting to clean up test monitors.** Every active monitor burns credits on schedule. Delete demo monitors with `monitor_delete` when done testing.
9. **No `searchWindow` on search monitors.** Web monitors without `searchWindow` default to 24h -- if you need different recency, set it explicitly (`5m`, `15m`, `1h`, `6h`, `24h`, `7d`).
10. **Relying on first `monitor_check` for diff.** The first check always shows "new" (baseline). Only subsequent checks produce diffs.
11. **Not verifying subagent results.** Delegated subagents self-report -- stat the file or read it back to confirm writes succeeded.

## Verification Checklist

- [ ] Tool selection matches the task (one page vs. search vs. full crawl)
- [ ] `limit` set explicitly on crawl calls
- [ ] JSON schema defined when extracting specific data points
- [ ] Agent polling continues for 2+ minutes
- [ ] Search feedback submitted after each search
- [ ] Credit balance checked before large crawl jobs
