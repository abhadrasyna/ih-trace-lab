# MTN monthly error code analysis docs

Monthly error code analysis from Athena only, across every MTN OpCo in `config/tenants.yaml` (SA, NG, ZM, GH). Use dated files in this folder (`YYYY-MM-<opco|all>-findings.md`) for recurring-campaign
notes, per Rule B. Script usage lives in `usage.md`; retention rules in `../RETENTION.md`.

Layout: raw pulls in `../data/athena/<OPCO>/YYYY-MM/` (gitignored), reports in `../output/<OPCO>/`, scripts in `../scripts/`, tests in `../tests/`.
