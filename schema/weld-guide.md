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

## Data MCP — Business Context (use this first)

Data MCP has a semantic layer with metric definitions and table descriptions. **Before writing any query, check this first.**

| Tool | When to use |
|---|---|
| `get_business_context` | Browse all available metrics and tables. Returns an index with names and short descriptions. Use this when you want to see what's available. |
| `get_context_for_question` | Pass a natural language question (e.g. "campaign ROAS") and get back the relevant metric definitions, table schemas, and query patterns. **This is the fastest way to answer a data question correctly.** |
| `get_metric_definition` | Get the full definition of a specific metric by name (e.g. "platform_roas"). Includes the SQL pattern, which tables to use, and caveats. |
| `get_table` / `get_table_context` | Get column details and usage notes for a specific table. |
| `run_query` / `preview_query` | Execute SQL against BigQuery (analysis.* and hubspot.* only). |

**The business context knows:**
- How every metric should be calculated (including which CTEs to separate, which joins to avoid)
- Which tables are deprecated and what replaced them
- Table grain (one row per what), row counts, and key columns
- Cross-table join patterns
- Domain-specific caveats (e.g. LinkedIn "campaign" = our adset)

**Workflow for answering a data question:**
1. Call `get_context_for_question` with the question → get relevant metrics + tables
2. Read the metric definition → understand the correct SQL pattern
3. Write and run the query using that pattern
4. This prevents the most common mistakes (wrong joins, wrong aggregation, wrong table)

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

### Answering a data question
```
1. Call get_context_for_question (Data MCP) with the question
2. Read the metric definition → correct SQL pattern, tables, caveats
3. Write query using that pattern
4. Run via Data MCP (analysis tables) or Weld run_query (staging/intermediate)
5. get_query_status → get_query_result
```

### Investigating why numbers look wrong
```
1. Identify which analysis table feeds the dashboard (check weld-architecture.txt)
2. get_transform with the transform ID → read the SQL
3. run_query on the analysis output to see current numbers
4. run_query on the intermediate/staging inputs to check upstream
5. Trace through the dependency chain until you find where data diverges
6. Report findings — don't change anything until root cause is clear
```

### Reading a transform
```
1. Find the transform ID from weld-architecture.txt or attribution-model.md
2. Call get_transform with the ID → returns full SQL, materialization, docs, dependencies
3. Call get_transform_schema to see output columns
```

### Modifying an existing transform

This is the most common change operation. Follow this sequence exactly.

```
1. BEFORE changing anything:
   a. get_transform → read current SQL and note the transform ID
   b. Check weld-architecture.txt for DOWNSTREAM dependencies
      (what other transforms SELECT FROM this one?)
   c. run_query to capture current output (row count + key metrics)
      → this is your baseline for verification

2. Make the change:
   a. Write the new sql_template
   b. Use {{folder.subfolder.transform_name}} for all table references
      (never hardcode BigQuery table names in transform SQL)
   c. Call update_transform with:
      - id: the transform ID
      - sql_template: the new SQL
      - documentation: update if the change affects what the transform does
      - publish: true
      - wait_for_completion: true

3. AFTER the change:
   a. run_query to check the output — compare to baseline
   b. If this transform has downstream dependencies:
      - rematerialize each downstream transform (wait_for_completion: true)
      - Verify those outputs too
   c. If numbers shifted, explain WHY in your Slack reply

4. If something went wrong:
   - You have the original SQL from step 1a — update_transform back to it
   - rematerialize to restore
```

**Critical: the `sql_template` field**
- Must use `{{weld_tag}}` references, not raw BigQuery table names
- Tags use dots: `{{staging.page_views.page_views}}` not `{{staging/page_views/page_views}}`
- The full SQL goes in `sql_template` as a string — no escaping needed beyond normal JSON
- Always test your SQL with `run_query` first before committing it to `update_transform`

### Creating a new transform

```
1. Decide the layer:
   - staging/ → cleaning a raw source
   - intermediate/ → joining/computing across staging tables
   - analysis/ → dashboard-ready output (most common for new tables)

2. Write and test the SQL:
   - Draft the SQL using {{weld_tags}} for all table references
   - Test with run_query to confirm it produces correct output
   - Check row count and grain (one row per what?)

3. Create the transform:
   - create_transform with:
     - name: descriptive_snake_case
     - folder: the appropriate layer folder (e.g. "analysis/demand_generation")
     - sql_template: the tested SQL
     - materialization: "table" (ALWAYS — never "view")
     - documentation: what it does, what grain, key columns

4. Wire it up:
   - attach_transform_to_orchestration with orchestration RPRe9-hoy6ayS1
   - rematerialize_transform with wait_for_completion: true
   - Verify the output with run_query

5. If it needs to be queryable via Data MCP / dashboards:
   - It MUST be in analysis/ — that's the only layer Data MCP can see
   - Update the business context (get_business_context) if you want
     the table to be discoverable there
```

### Rematerializing (re-running without SQL changes)

When upstream data changed and you need to refresh a transform:
```
1. rematerialize_transform with id and wait_for_completion: true
2. If it has downstream dependencies, rematerialize those too (in order)
3. To rematerialize the entire pipeline: request_orchestration_run on RPRe9-hoy6ayS1
   (this runs everything in dependency order — takes ~15-30 min)
```

### Querying different layers

**Analysis tables (Data MCP):**
```sql
SELECT conversion_touch_source, COUNT(*) as contacts
FROM analysis.demand_generation__contact_attribution
WHERE recent_conversion_ts >= '2026-08-01'
GROUP BY 1 ORDER BY 2 DESC
```

**Staging/intermediate tables (Weld MCP run_query):**
```sql
SELECT * FROM {{staging.page_views.page_views}}
WHERE event_date >= '2026-08-01'
LIMIT 100
```

**Raw source tables (Weld MCP run_query):**
```sql
SELECT * FROM {{raw.hubspot.contact}}
WHERE property_createdate >= '2026-08-01'
LIMIT 100
```
