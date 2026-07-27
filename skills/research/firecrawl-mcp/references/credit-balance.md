# Firecrawl Credit Balance Check

## Via Terminal (direct API call)

```bash
curl -X GET "https://api.firecrawl.dev/v1/team/credit-usage" \
  -H "Authorization: Bearer $MCP_FIRECRAWL_API_KEY"
```

## Response Shape

```json
{
  "success": true,
  "data": {
    "remaining_credits": 1021,
    "plan_credits": 1000,
    "billing_period_start": "2026-07-19T12:17:11.858Z",
    "billing_period_end": "2026-08-19T12:17:11.858Z"
  }
}
```

## Credit Costs Quick Sheet

| Operation | Credits |
|---|---|
| Scrape (markdown) | 1 |
| Scrape (JSON mode) | 5 (1 + 4 JSON) |
| Scrape (branding) | 1 |
| Search (per 10 results) | 2 |
| Crawl (per page) | 1 |
| Crawl + JSON (per page) | 5 |
| Map | 1 |
| Extract (multi-page) | ~23 |
| Monitor check (basic) | ~1-2 |
| Monitor check (with AI judging) | ~2 |
| Agent | varies (5-50+) |
| PDF parse (per page) | 1 |
| Enhanced proxy | +4/page |
| Screenshot | +0.5/page |
