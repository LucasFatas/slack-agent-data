# Weld Guide — How to Work with the Data Stack

## Architecture: stg → int → analysis

All data flows through three layers. This is enforced — no skipping layers.

```
Raw sources (ELT syncs)     Not transforms. Weld syncs these automatically.
  ↓                         Tables like: hubspot.contact, google_ads.campaign_stats
staging/{platform}/         Clean, rename, type-cast, extract UTMs. One transform per source table.
  ↓                         BigQuery: staging.{platform}__{table_name}
intermediate/{domain}/      Join across sources, sessionize, compute flags. Business logic lives here.
  ↓                         BigQuery: intermediate.{domain}__{table_name}
analysis/{domain}/          Dashboard-ready, one-row-per-entity grain. This is what people query.
  ↓                         BigQuery: analysis.{domain}__{table_name}
reverse_etl/{destination}/  Syncs back to tools (HubSpot, etc.)
                            BigQuery: reverse_etl.{destination}__{table_name}
```

### Why this matters
- **Data MCP (BigQuery direct)** can only query `analysis.*` and `hubspot.*` schemas
- **Weld MCP `run_query`** can query ANY layer using `{{weld_tags}}` syntax
- If someone asks about data in staging or intermediate, use Weld's `run_query`
- If someone asks about dashboard numbers, use Data MCP (it queries analysis tables)
- Any table that needs to be used by a person, dashboard, or external tool MUST be in `analysis/`

## Weld MCP Tools — When to Use Each

### Reading data

| Tool | When to use |
|---|---|
| `run_query` | Ad-hoc SQL queries. Use `{{tag.transform_name}}` to reference transforms. Returns query ID. |
| `get_query_status` | Check if a `run_query` has finished. |
| `get_query_result` | Fetch results of a completed query. |
| `get_transform` | Get a specific transform's full SQL, materialization, and config by ID. |
| `get_transform_schema` | Get output columns of a transform. |
| `list_transforms` | Browse all transforms. Use pagination. |

### Modifying transforms

| Tool | When to use |
|---|---|
| `update_transform` | Change a transform's SQL, documentation, or materialization. Set `publish: true` and `wait_for_completion: true` to apply immediately. |
| `create_transform` | Create a new transform. Always set `materialization: "table"`. |
| `publish_transform` | Publish a draft transform (if not using `publish: true` on update). |
| `rematerialize_transform` | Re-run a transform without changing its SQL. Use `wait_for_completion: true`. |

### Orchestrations

| Tool | When to use |
|---|---|
| `get_orchestration` | See what's in an orchestration and its schedule. |
| `attach_transform_to_orchestration` | Add a new transform to the pipeline. Use orchestration `RPRe9-hoy6ayS1` for attribution. |
| `request_orchestration_run` | Trigger a full pipeline run manually. |

## Weld Tag Syntax

In `run_query` and transform SQL, reference other transforms with double curly braces:

```sql
-- Reference a transform by its folder path
SELECT * FROM {{staging.page_views.page_views}}

-- This resolves to the BigQuery table: staging.page_views__page_views
-- But using tags ensures Weld tracks dependencies correctly
```

In `update_transform`, the `sql_template` field uses `{{folder.subfolder.transform_name}}` — no spaces inside braces.

## Rules (enforced, not guidelines)

1. **Always `materialization: "table"`** — views have caused dataset creation failures and BigQuery performance issues. No exceptions.

2. **Always attach to orchestration** — standalone transforms don't run on schedule. Attribution transforms go on `RPRe9-hoy6ayS1`.

3. **Set `documentation`** on every transform — brief description of what it does and why. This shows in the Weld UI.

4. **`publish: true, wait_for_completion: true`** when updating — otherwise the change is a draft that never runs.

5. **Verify with data** — after any transform change, run a query to confirm the output is correct. Compare row counts and key metrics before and after.

## Common Workflows

### "What does this transform do?"
```
1. Find the transform ID from weld-architecture.txt or attribution-model.md
2. Call get_transform with the ID
3. Read the SQL
```

### "Change a transform's SQL"
```
1. get_transform → read current SQL
2. Modify the SQL
3. update_transform with publish: true, wait_for_completion: true
4. run_query to verify the output
5. get_query_status → get_query_result to check
```

### "Add a new analysis table"
```
1. create_transform in analysis/{domain}/ with materialization: "table"
2. attach_transform_to_orchestration (RPRe9-hoy6ayS1)
3. rematerialize_transform with wait_for_completion: true
4. Verify with run_query
```

### "Debug why numbers look wrong"
```
1. Identify which analysis table feeds the dashboard
2. get_transform → read the SQL
3. run_query on the intermediate inputs to check
4. Trace upstream through the dependency chain in weld-architecture.txt
5. Find where the data diverges
```

### "Query staging/intermediate data"
```
-- Can't use Data MCP for these. Use Weld run_query:
SELECT * FROM {{staging.page_views.page_views}}
WHERE event_date >= '2026-08-01'
LIMIT 100
```

### "Query analysis data"
```
-- Use Data MCP (BigQuery) for analysis tables:
SELECT conversion_touch_source, COUNT(*) as contacts
FROM analysis.demand_generation__contact_attribution
WHERE recent_conversion_ts >= '2026-08-01'
GROUP BY 1
ORDER BY 2 DESC
```
