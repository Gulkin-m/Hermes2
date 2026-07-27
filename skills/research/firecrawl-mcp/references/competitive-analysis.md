# Competitive Analysis with Firecrawl MCP

## JSON Schema for Landing Page Analysis

```json
{
  "prompt": "Extract the headline, sub-headline, main value proposition, CTA button text, pricing signal (free/paid/from $X), and target audience from this landing page",
  "schema": {
    "type": "object",
    "properties": {
      "headline": { "type": "string" },
      "sub_headline": { "type": "string" },
      "value_proposition": { "type": "string" },
      "cta_text": { "type": "string" },
      "pricing_signal": { "type": "string" },
      "target_audience": { "type": "string" }
    }
  }
}
```

## Pricing Page Schema

```json
{
  "prompt": "Extract the pricing plans: name, price, billing period, and key features",
  "schema": {
    "type": "object",
    "properties": {
      "plans": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "name": { "type": "string" },
            "price": { "type": "string" },
            "billing": { "type": "string" },
            "features": { "type": "array", "items": { "type": "string" } }
          }
        }
      }
    }
  }
}
```

## Blog/Article Headlines Schema

```json
{
  "prompt": "Extract article titles, their URLs, and dates from this page",
  "schema": {
    "type": "object",
    "properties": {
      "articles": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "title": { "type": "string" },
            "url": { "type": "string" },
            "date": { "type": "string" }
          }
        }
      }
    }
  }
}
```

## Monitor Goal Examples

- Pricing: `"Alert when any pricing tier name, price, billing period, or features change"`
- Blog: `"Alert when a new blog post is published with a new headline"`
- Changelog: `"Alert when new product features or releases are announced"`
- Positioning: `"Alert if the headline, sub-headline, or value proposition changes"`

## Parallel Scraping Strategy

For comparing 3-5 competitors, send parallel `firecrawl_scrape` calls. Each costs ~5 credits (JSON mode). Total cost for 3 competitors: ~15 credits.

## Monitoring Cost Estimation

- 1 page checked every 6 hours = ~120 checks/month
- Estimated monthly credits: ~120 (basic mode) to ~240 (with AI judging)

See also: SKILL.md "firecrawl-mcp" for full tool reference.
