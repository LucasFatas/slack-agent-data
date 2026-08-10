#!/usr/bin/env python3
"""
Refresh the Weld schema reference file.

Run this at the start of a session or when transforms have changed.
It pulls all transform metadata from Weld and writes schema/weld-transforms.json.

Usage: python3 scripts/refresh-schema.py

Requires: Weld MCP to be connected (the script asks Claude to run it,
or it can be run via the Weld API directly if credentials are available).

Since this needs Weld MCP access, the recommended approach is:
1. In Claude Code, say: "refresh the schema"
2. Claude runs this logic via Weld MCP tools
3. The output is saved to schema/weld-transforms.json

This file documents the expected structure for manual reference.
"""

# This script is designed to be run BY Claude Code using Weld MCP tools.
# When the user says "refresh schema", Claude should:
#
# 1. Call mcp__claude_ai_Weld__list_transforms() with pagination
# 2. For each transform in folders:
#    - staging/page_views/
#    - staging/google_ads/
#    - staging/meta/
#    - staging/linkedin/
#    - staging/microsoft_ads/
#    - staging/google_analytics/
#    - intermediate/page_views/
#    - intermediate/ad_metrics/
#    - analysis/demand_generation/
#    - reverse_etl/hubspot/
#    - commercial/ (key tables only)
#    Call get_transform to get the full SQL
#
# 3. Write the output to schema/weld-transforms.json with structure:
#    {
#      "generated_at": "2026-07-23T12:00:00Z",
#      "transforms": {
#        "staging/page_views/page_views": {
#          "id": "ILkp3u-JHpQRzw",
#          "name": "page_views",
#          "folder_path": "staging/page_views",
#          "materialization": "table",
#          "orchestration_workflow_id": "RPRe9-hoy6ayS1",
#          "sql_template": "WITH raw AS (...)",
#          "parameters": [...],
#          "output_columns": ["event_id", "object_id", ...],
#          "dependencies": ["raw.hubspot_page_views.raw_events", "raw.google_ads.campaign_stats"]
#        },
#        ...
#      }
#    }

print("""
This script documents the schema refresh process.
To actually refresh, ask Claude Code: "refresh the schema"
Claude will use Weld MCP to pull all transforms and write schema/weld-transforms.json
""")
