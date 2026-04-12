# CAPS ASCII MAP

```text
CAPS
|
+-- ROOT
|   |
|   +-- server/
|   +-- client/
|   +-- shared/
|   +-- deploy/
|   +-- docs/
|   +-- scripts/
|   +-- backend/   (legacy reference)
|   `-- frontend/  (legacy reference)
|
+-- OFFICIAL RUNTIME
|   |
|   +-- client/overlay
|   |   |
|   |   +-- auth
|   |   +-- session
|   |   +-- context
|   |   +-- live caption
|   |   +-- events
|   |   +-- reports
|   |   `-- history / retrieval brief
|   |
|   +-- server/app
|   |   |
|   |   +-- auth + workspace role
|   |   +-- session + participation
|   |   +-- context
|   |   +-- audio pipeline
|   |   +-- events
|   |   +-- report + sharing
|   |   +-- retrieval
|   |   `-- runtime monitor
|   |
|   `-- shared
|       |
|       +-- contracts
|       +-- enums
|       `-- schemas
|
+-- STORAGE NOW
|   |
|   +-- PostgreSQL
|   +-- pgvector
|   +-- server/data/reports/{session_id}/
|   `-- client local state
|
`-- OPTIONAL LATER
    |
    +-- Redis queue / lock / cache
    `-- dedicated workers
```

```text
REPORT PATH
|
+-- session end
+-- report_generation_job pending
+-- full STT / transcript
+-- markdown or pdf build
+-- save artifact
+-- share if needed
`-- retrieval indexing
```

```text
HISTORY PATH
|
+-- account/contact/thread filter
+-- recent sessions
+-- recent reports
+-- carry-over
`-- retrieval brief
```
