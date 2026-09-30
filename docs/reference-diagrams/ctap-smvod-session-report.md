# Reference diagram — ctap-smvod-session-report

This project's migration value is its orchestration and report data flow, not an internal import graph.

## `run_pipeline.py` orchestration (BLUEPRINT steps 2–6b)

```mermaid
sequenceDiagram
    participant Operator as run_pipeline.py
    participant Merge as merge_ctap_smvod_csv.py
    participant Outcome as run_athena_playback_outcome.py
    participant Debug as run_athena_debug_events.py
    participant Final as merge_session_outcome.py
    participant Position as extract_position_report.py

    Operator->>Merge: Step 2 --date DDMMYYYY
    Merge-->>Operator: output/setupsession_DDMMYYYY.csv

    alt Step 3 not skipped
        Operator->>Outcome: Step 3 --date YYYY-MM-DD
        Outcome-->>Operator: inputCSV/athena_session_DDMMYYYY.csv
    end

    alt Step 4 not skipped
        Operator->>Debug: Step 4 --date YYYY-MM-DD
        Debug-->>Operator: inputCSV/debug_states_DDMMYYYY.csv
    end

    Operator->>Final: Step 5 --date DDMMYYYY
    Final-->>Operator: output/setupsession_with_outcome_DDMMYYYY.csv

    alt Step 6b not skipped
        Operator->>Position: Step 6b --date DDMMYYYY
        Position-->>Operator: output/position_report_DDMMYYYY.csv
    end
```

## Report data flow

```mermaid
flowchart LR
    EXPORTS["Manual Lightstep + Athena CSV exports"] --> PREP["flatten_debug_events.py<br/>lightstep_ctap_smvod_join.py"]
    PREP --> BASE["merge_ctap_smvod_csv.py<br/>base CTAP/SM-VOD merge"]
    BASE --> FINAL["merge_session_outcome.py<br/>Athena enrichment merge"]
    FINAL --> OUT["output/setupsession_with_outcome_DDMMYYYY.csv"]
    OUT --> REPORTS["analyze_* / extract_* / build_* report scripts"]
```

## Convergence target

This diagram supports `pipeline-migration`'s `ctap-smvod-investigation-migration` sub-story; it does not replace that story's actual migration work. The migrated target remains an investigation
pipeline under `investigations/ctap-smvod/`, reusing shared Athena/CSV/report helpers while preserving the export-driven orchestration shown here.
