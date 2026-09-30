# Project taxonomy

Use this guide before creating any new top-level work folder in `ih-trace-lab`. It names the four project categories this repo accepts, the boundary between them, and the folder/document rules later
sections build on.

## Categories

**Pipeline** — recurring, scheduled data collection or reporting with no open-ended investigation question and no case deliverable to write up. The model is `github_copilot/aws-access-cli`:
cron-driven Athena adoption/session reports plus SSO refresh automation. The nearest neighbor is an investigation; the deciding test is simple: if there is no live product question and no mandatory
case doc, it is a pipeline, not an investigation.

**Investigation** — a campaign or case tied to a live product question, whether that work closes as a bounded case or continues as a recurring, no-close-event campaign with dated outputs. The model is
`github_copilot/applauseInvestigation`, `github_copilot/mtn-zm-session-device-investigation`, and `github_copilot/ctap-smvod-session-report`, with the last one treated here as a plain folder rather
than a separate category or submodule. The nearest neighbors are pipelines and experiments: unlike a pipeline it has an open question plus mandatory docs, and within the category the distinction is
case-close-out versus rolling retention, not a fifth top-level label.

**Tool** — reusable software with its own interface or protocol, kept alive across many callers rather than one campaign's immediate question. The model is `github_copilot/oasis-athena-mcp` and
`github_copilot/mtn-network-traffic`, both maintained as software products rather than case folders. The nearest neighbor is an experiment; if the output needs a stable interface other work can call
and you expect ongoing enhancement, it is a tool, not a throwaway probe.

**Experiment** — a short-lived probe answering one narrow question, expected to be thrown away or absorbed once it proves or disproves that point. The model is
`github_copilot/vod-playback-timing-probe`, while noting the open tension recorded in `docs/plan/reference-code-gap-migration/README.md` that this example may read more like a tool on a later pass.
The nearest neighbor is an investigation; if the work is a disposable probe rather than a real product question with mandatory case docs, it is an experiment, not an investigation.
