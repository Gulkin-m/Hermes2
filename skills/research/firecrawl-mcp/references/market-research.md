# AI Market Research with Firecrawl

## Workflow for Company/Startup Research

1. **Firecrawl Search** — find latest articles, funding news, company listings
   ```json
   firecrawl_search(query: "top AI startups 2026 funding valuation founders", limit: 10)
   ```

2. **Autonomous Agent** — deep structured research with JSON schema
   ```json
   firecrawl_agent(
     prompt: "Research 10 hottest AI startups of 2026 with name, product, valuation, founders",
     schema: {
       type: "object",
       properties: {
         startups: {
           type: "array",
           items: {
             type: "object",
             properties: {
               name: { type: "string" },
               product: { type: "string" },
               valuation_or_funding: { type: "string" },
               founders: { type: "string" }
             }
           }
         }
       }
     }
   )
   ```

3. **Scrape Company Pages** — individual landing pages for details (1-5 credits each)

## Top Sources for Market Data
- Forbes AI 50: `forbes.com/lists/ai50`
- TechCrunch (funding rounds): `techcrunch.com`
- Crunchbase: `crunchbase.com` (may need JSON extraction)
- ValueAddVC: `valueaddvc.com/blog`
- TopStartups: `topstartups.io`
- CB Insights research

## Typical Cost for Full Market Scan
- Search: 2 credits
- Agent: ~20-50 credits
- Individual company scrapes: 5-10 credits each in JSON mode
- Total: ~50-100 credits for comprehensive analysis
