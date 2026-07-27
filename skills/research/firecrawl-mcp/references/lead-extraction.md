# Lead & Review Extraction with Firecrawl MCP

## Company Lead Schema

```json
{
  "prompt": "Extract company name, description, location, industry, founders, funding, email, phone, and social links",
  "schema": {
    "type": "object",
    "properties": {
      "company_name": { "type": "string" },
      "description": { "type": "string" },
      "location": { "type": "string" },
      "industry": { "type": "string" },
      "founders": { "type": "string" },
      "funding": { "type": "string" },
      "email": { "type": "string" },
      "phone": { "type": "string" },
      "social_links": { "type": "array", "items": { "type": "string" } }
    }
  }
}
```

## Review/Feedback Schema

```json
{
  "prompt": "Extract all reviews: reviewer name, review text, rating, date",
  "schema": {
    "type": "object",
    "properties": {
      "reviews": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "name": { "type": "string" },
            "review_text": { "type": "string" },
            "rating": { "type": "string" },
            "date": { "type": "string" }
          }
        }
      }
    }
  }
}
```

## Lead Discovery Workflow

1. **Search** — find sources of leads
   ```json
   firecrawl_search(query: "AI startups San Francisco founders", limit: 10)
   // Returns LinkedIn profiles, Crunchbase entries, company websites
   ```

2. **Scrape each URL** with the company lead schema

3. **Combine results** into a unified lead table

## Lead Sources That Work Well

- Y Combinator directory: ycombinator.com/companies
- Company /about pages
- Crunchbase (search results)
- LinkedIn profile URLs (via search, not logged-in profiles)
- Startup directories (topstartups.io, raising.fi)

## Limitations

- LinkedIn logged-in profiles require authentication (Firecrawl cannot bypass login)
- Paywalled databases (Crunchbase full profiles) may not render
- Some directories are JS-heavy SPAs — try firecrawl_agent or proxy: stealth as fallback

## Typical Cost

- Search: 2 credits
- Per-company scrape (JSON): 5 credits
- 10 leads from search results: ~52 credits total
