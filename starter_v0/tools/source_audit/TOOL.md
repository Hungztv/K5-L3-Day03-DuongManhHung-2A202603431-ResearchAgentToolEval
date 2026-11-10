---
name: source_audit
track: core
kind: local_formatter
requires_env: []
inputs: [items]
outputs: [item_count, issue_count, is_clean, items]
side_effect: false
---
# source_audit

Checks user-provided source records for missing titles or URLs, invalid URLs,
and duplicate links. It does not search for sources or verify factual accuracy.
