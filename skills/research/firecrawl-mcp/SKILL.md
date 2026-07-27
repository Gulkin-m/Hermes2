---
name: firecrawl-mcp
category: research
description: Complete guide to Firecrawl MCP tools — search, scrape, crawl, extract, monitor, and research agent. Covers competitive analysis, content gathering, SEO research, and market intelligence workflows.
---

# Firecrawl MCP — Web Data Toolkit

Everything you can do with Firecrawl MCP tools on this Hermes instance. Firecrawl is connected via MCP with a valid API key (`MCP_FIRECRAWL_API_KEY` in `.env`), 1021+ credits available.

## Quick Reference

| Tool | Credit Cost | Best For |
|---|---|---|
| `firecrawl_scrape` | 1 (markdown), 5 (JSON) | Single page — content or structured data |
| `firecrawl_search` | 2 per 10 results | Web search, optionally with scraping |
| `firecrawl_crawl` | 1 per page | Recursive site-wide collection |
| `firecrawl_map` | 1 | Discovering all URLs on a site |
| `firecrawl_extract` | ~23 | Multi-page structured extraction *(deprecated — use scrape+json instead)* |
| `firecrawl_agent` | varies | Autonomous multi-step research |
| `firecrawl_monitor_create` | ~2/check | Watching pages for changes over time |
| `firecrawl_interact` | varies | Clicking buttons, filling forms in browser |

## Connection Verification

```json
// Test connection + check credit balance
firecrawl_search("test", limit: 1)
// Then check balance via terminal:
// curl -X GET "https://api.firecrawl.dev/v1/team/credit-usage" -H "Authorization: Bearer $MCP_FIRECRAWL_API_KEY"
```

## Key Patterns

### 1. Single Page Scrape (markdown)
Best for: reading articles, documentation pages, blog posts.

```json
firecrawl_scrape(url: "https://example.com", formats: ["markdown"], onlyMainContent: true)
// Returns: clean markdown, 1 credit
```

### 2. Structured Data Extraction (JSON schema)
Best for: extracting specific data points (prices, headlines, features, metadata).

```json
firecrawl_scrape(
  url: "https://example.com",
  formats: ["json"],
  jsonOptions: {
    prompt: "Extract the headline, pricing, features...",
    schema: {
      type: "object",
      properties: {
        headline: { type: "string" },
        pricing: { type: "string" },
        features: { type: "array", items: { type: "string" } }
      }
    }
  }
)
// Returns: structured JSON, 5 credits
```

### 3. Web Search
Best for: discovery, finding URLs before scraping.

```json
firecrawl_search(query: "topic", limit: 5)
// Returns: titles + descriptions + URLs, 2 credits
// Add scrapeOptions: { formats: ["markdown"] } to also get full content
```

### 4. Site Map (URL Discovery)
Best for: finding all pages on a site before deciding what to scrape.

```json
firecrawl_map(url: "https://example.com/blog", limit: 100)
// Returns: array of {url, title} pairs, 1 credit
```

### 5. Recursive Crawl
Best for: collecting entire documentation sites, blogs, or knowledge bases.

```json
firecrawl_crawl(
  url: "https://example.com/docs",
  limit: 50,
  maxDiscoveryDepth: 2,
  scrapeOptions: { formats: ["markdown"] }
)
// Returns: array of scraped pages, 1 credit per page
```

### 6. Page Change Monitoring
Best for: watching competitor pricing, changelogs, or any page that changes.

```json
firecrawl_monitor_create(
  page: "https://competitor.com/pricing",
  goal: "Alert when any pricing tier name, price, or billing period changes",
  scheduleText: "every 6 hours"
)
// Auto-diffs on each check, AI judge filters noise
```

### 7. Autonomous Research Agent
Best for: complex multi-step research across many URLs.

```json
firecrawl_agent(
  prompt: "Research X and return structured data about Y",
  schema: { properties: { ... } }
)
// Returns job ID — poll with firecrawl_agent_status(id)
```

### 8. PDF Parsing (URL or Local File)
Best for: extracting content and structured data from PDFs (papers, contracts, reports).

**Via URL** — use firecrawl_scrape on any PDF URL:
```json
firecrawl_scrape(
  url: "https://arxiv.org/pdf/1706.03762.pdf",
  formats: ["markdown", "json"],
  jsonOptions: {
    prompt: "Extract title, authors, abstract, key findings, methodology",
    schema: {
      type: "object",
      properties: {
        title: { type: "string" },
        authors: { type: "string" },
        abstract: { type: "string" },
        methodology: { type: "string" },
        key_findings: { type: "string" }
      }
    }
  }
)
```
Returns full markdown + structured JSON. Cost: 1 base + 1 per PDF page + 4 if JSON.

**Via local file** — use firecrawl_parse:
```json
firecrawl_parse(
  filePath: "C:/path/to/report.pdf",
  formats: ["markdown", "json"],
  jsonOptions: { prompt: "...", schema: { ... } }
)
```

### 9. Lead & Review Extraction
Best for: gathering customer reviews with names, ratings; extracting company contact data.

**Reviews with names, ratings, text:**
```json
firecrawl_scrape(
  url: "https://example.com/reviews",
  formats: ["json"],
  jsonOptions: {
    prompt: "Extract all reviews: reviewer name, review text, rating, date",
    schema: {
      type: "object",
      properties: {
        reviews: {
          type: "array",
          items: {
            type: "object",
            properties: {
              name: { type: "string" },
              review_text: { type: "string" },
              rating: { type: "string" },
              date: { type: "string" }
            }
          }
        }
      }
    }
  }
)
```

**Company lead schema** — see references/lead-extraction.md

### 10. Multi-page Extraction (deprecated)
Prefer scrape+json instead. Only use when you need to query 2+ URLs with one schema.

```json
firecrawl_extract(
  urls: ["url1", "url2", "url3"],
  prompt: "...",
  schema: { ... }
)
```

## Common Workflows

### Competitive Analysis
1. `firecrawl_scrape` each competitor's landing page (parallel calls) with JSON schema
2. Schema fields: headline, sub_headline, value_proposition, cta_text, pricing_signal, target_audience
3. Compare results side-by-side

### Course Content Collection
1. `firecrawl_map(url)` → discover all documentation URLs
2. `firecrawl_crawl(url, limit=N)` → bulk download as markdown
3. Each page is clean markdown, ready for course materials

### Course/Learning Platform Scraping
Extract course structure (modules, lessons, reviews) from platforms like Stepik:
1. `firecrawl_scrape(url, formats: ["json"], schema: {course_title, description, modules})` → get syllabus
2. `firecrawl_scrape(url + "/reviews", formats: ["json"], schema: {reviews: [{name, review_text, rating, date}]})` → get student reviews
3. Combine to analyze course quality, demand, and competitor content

### Blog/SEO Monitoring
1. `firecrawl_scrape(url, formats: ["json"], schema: {articles: [{title, url, date}]})` → extract headlines
2. OR `firecrawl_monitor_create(page: blog_url, goal: "new article")` → auto-alert on new posts

### Market Research
1. `firecrawl_search(query, limit=10)` → discover sources
2. `firecrawl_agent(prompt, schema)` → deep structured research
3. Combine results into comparison tables

## Pitfalls

- **firecrawl_extract is deprecated**: warning says use /v2/scrape with JSON format instead
- **Crawl pre-flight credit check**: Firecrawl checks your balance against `limit` before starting. If limit=10000 (default) and you have less than 10000 credits, it returns 402. Always set an explicit limit.
- **Rate limits**: frequent calls get 429. Use cache (maxAge) when freshness is not critical.
- **Agent takes time**: 30s-2min for complex queries. Poll firecrawl_agent_status every 15-30s.
- **Sites with anti-bot protection**: some sites (e.g. Russian sites behind Cloudflare) block Firecrawl proxies with ERR_TUNNEL_CONNECTION_FAILED or ERR_CONNECTION_CLOSED. Fall back to web_search + web_extract from other tools when this happens.
- **SPA/JS-heavy sites**: dynamic content (Udemy, Crunchbase) may not render. Try waitFor, proxy: stealth, or fall back to firecrawl_agent.
- **Credit monitoring**: Check balance via curl GET on /v1/team/credit-usage with Bearer token
- **Data retention**: Job results expire after 24h. Cache state defaults to 2 days freshness.
