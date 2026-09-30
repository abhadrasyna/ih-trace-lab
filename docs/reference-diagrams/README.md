# Reference folder diagrams

Start with the flat overview: [`docs/reference-architecture.md`](../reference-architecture.md) — it gives file counts and the one-page cross-project map, while the pages below zoom into the folders
that are actually in migration scope.

## Diagram index

<table> <thead>
    <tr>
      <th>Folder</th>
      <th>Diagram</th>
      <th>Purpose</th>
      <th>Supports</th>
    </tr>
</thead> <tbody>
    <tr>
      <td><code>applauseInvestigation</code></td>
      <td><a href="./applauseInvestigation.md">applauseInvestigation.md</a></td>
      <td>Generated script flowchart plus Athena/HAR/CSV/report convergence notes.</td>
      <td><code>reference-code-gap-migration/applause-investigation-migration</code></td>
    </tr>
    <tr>
      <td><code>astro-events-household-report</code></td>
      <td><a href="./astro-events-household-report.md">astro-events-household-report.md</a></td>
      <td>Generated script flowchart plus CSV/report convergence notes.</td>
      <td><code>reference-code-gap-migration/astro-events-household-investigation-migration</code></td>
    </tr>
    <tr>
      <td><code>shaka-6001-sa-error-analysis</code></td>
      <td><a href="./shaka-6001-sa-error-analysis.md">shaka-6001-sa-error-analysis.md</a></td>
      <td>Generated flowchart for the local Athena/auth/user-agent helpers.</td>
      <td><code>reference-code-gap-migration/shaka-6001-sa-investigation-migration</code></td>
    </tr>
    <tr>
      <td>root <code>scripts/</code></td>
      <td><a href="./scripts.md">scripts.md</a></td>
      <td>Generated flowchart for reference-repo maintenance scripts and the FCT-6 overlap note.</td>
      <td><code>reference-code-gap-migration/root-scripts-tool-migration</code></td>
    </tr>
    <tr>
      <td><code>vod-asset-ingestion-mapping</code></td>
      <td><a href="./vod-asset-ingestion-mapping.md">vod-asset-ingestion-mapping.md</a></td>
      <td>Hand-authored ADI/OpsHub/Mongo/CTAP/HAR/Lightstep field and ID mapping diagram.</td>
      <td><code>reference-code-gap-migration/vod-asset-ingestion-investigation-migration</code></td>
    </tr>
    <tr>
      <td><code>mtn-zm-session-device-investigation</code></td>
      <td><a href="./mtn-zm-session-device-investigation.md">mtn-zm-session-device-investigation.md</a></td>
      <td>Generated flowchart plus the <code>classify_session_outcomes.py</code> state diagram.</td>
      <td><code>reference-code-gap-migration/mtn-zm-device-investigation-migration</code></td>
    </tr>
    <tr>
      <td><code>mtn-network-traffic</code></td>
      <td><a href="./mtn-network-traffic.md">mtn-network-traffic.md</a></td>
      <td>Generated diagnostics-tool flowchart with the “stay local” note.</td>
      <td><code>reference-code-gap-migration/mtn-network-traffic-tool-migration</code></td>
    </tr>
    <tr>
      <td>root <code>investigations/</code></td>
      <td><a href="./investigations.md">investigations.md</a></td>
      <td>Generated flowchart marking the scripts blocked on <code>mpd</code> and <code>crypto_signing</code>.</td>
      <td><code>reference-code-gap-migration/root-investigations-migration</code></td>
    </tr>
    <tr>
      <td><code>vod-playback-timing-probe</code></td>
      <td><a href="./vod-playback-timing-probe.md">vod-playback-timing-probe.md</a></td>
      <td>CLI-chain flowchart plus the cross-project <code>mpd</code> convergence diagram.</td>
      <td><code>reference-code-gap-migration/vod-playback-timing-probe-tool-migration</code> + <code>src-lib-migration</code> (<code>mpd</code>)</td>
    </tr>
    <tr>
      <td><code>smarttv-mtntv</code></td>
      <td><a href="./smarttv-mtntv.md">smarttv-mtntv.md</a></td>
      <td>Small convergence diagram for the duplicated JWS/JSON-signing logic.</td>
      <td><code>reference-code-gap-migration/smarttv-mtntv-tool-migration</code> + <code>src-lib-migration</code> (<code>crypto_signing</code>)</td>
    </tr>
    <tr>
      <td><code>aws-access-cli</code></td>
      <td><a href="./aws-access-cli.md">aws-access-cli.md</a></td>
      <td>Dense generated flowchart plus the <code>run_daily_reports.py</code> orchestration sequence.</td>
      <td><code>pipeline-migration/aws-access-cli-pipeline-migration</code></td>
    </tr>
    <tr>
      <td><code>ctap-smvod-session-report</code></td>
      <td><a href="./ctap-smvod-session-report.md">ctap-smvod-session-report.md</a></td>
      <td><code>run_pipeline.py</code> orchestration sequence plus export-to-report data-flow diagram.</td>
      <td><code>pipeline-migration/ctap-smvod-investigation-migration</code></td>
    </tr>
</tbody> </table>

## Deliberate exclusion

`oasis-athena-mcp` has no diagram here. GAP-1 confirmed it is superseded by the `athena-mcp-server` submodule, so it carries no migration work of its own and therefore nothing to diagram in this
story.
