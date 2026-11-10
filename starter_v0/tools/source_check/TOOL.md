---
name: source_check
track: core
kind: local_formatter
requires_env: []
inputs: [items]
outputs: [items, checked_count, valid_count, scope_note]
side_effect: false
---
# source_check

Checks already collected citations for a title, an HTTP/HTTPS URL, and duplicate
URLs. It can fill a missing source label from the URL host. It works locally and
does not contact websites, so it cannot confirm page availability or factual
accuracy.
