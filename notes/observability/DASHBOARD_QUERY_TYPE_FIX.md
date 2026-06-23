# Grafana Dashboard Query Type Fix

## Issue

After adding `span.operation.type` attributes to traces, the Neuroglia Framework dashboard still showed "No data found in response" for all trace panels despite:

- ✅ Attributes being correctly set in traces (verified with `check_span_attributes.py`)
- ✅ Tempo API returning traces when queried with tags
- ✅ Command-line queries working correctly

## Root Cause

The dashboard was using **TraceQL query syntax** with `queryType: "traceqlSearch"`:

```json
{
  "query": "{service.name=\"mario-pizzeria\" && span.operation.type=\"command\"}",
  "queryType": "traceqlSearch"
}
```

This TraceQL syntax was not working with the Tempo 2.6.1 version or configuration, causing Grafana to show "No data found".

## Solution

Changed all three trace panels to use **native search syntax** with `queryType: "nativeSearch"`:

```json
{
  "query": "service.name=mario-pizzeria span.operation.type=command",
  "queryType": "nativeSearch"
}
```

### Files Modified

- `deployment/grafana/dashboards/json/neuroglia-framework.json`
  - Panel 1 (Command Traces): Changed query type and syntax
  - Panel 2 (Query Traces): Changed query type and syntax
  - Panel 3 (Repository Traces): Changed query type and syntax

### Changes Applied

| Panel                        | Old Query                                                             | New Query                                                    |
| ---------------------------- | --------------------------------------------------------------------- | ------------------------------------------------------------ |
| Recent Command Traces        | `{service.name="mario-pizzeria" && span.operation.type="command"}`    | `service.name=mario-pizzeria span.operation.type=command`    |
| Recent Query Traces          | `{service.name="mario-pizzeria" && span.operation.type="query"}`      | `service.name=mario-pizzeria span.operation.type=query`      |
| Recent Repository Operations | `{service.name="mario-pizzeria" && span.operation.type="repository"}` | `service.name=mario-pizzeria span.operation.type=repository` |

## Verification

The native search query format matches the tags-based API that we verified works:

```bash
# This works:
curl 'http://localhost:3200/api/search?tags=service.name%3Dmario-pizzeria&tags=span.operation.type%3Dcommand'

# Grafana now uses equivalent syntax:
service.name=mario-pizzeria span.operation.type=command
```

## Deployment

1. Updated dashboard JSON file
2. Restarted Grafana container:
   ```bash
   docker restart mario-pizzeria-grafana-1
   ```
3. Dashboard automatically reloaded with new configuration

## Result

✅ All three trace panels now display data correctly
✅ Queries match the working API format
✅ No code changes needed - dashboard configuration only

## Notes

- Tempo 2.6.1 may have limited TraceQL support
- Native search syntax is more reliable for tag-based queries
- The `span.operation.type` attributes are correctly set in traces
- Future Tempo versions may improve TraceQL support
