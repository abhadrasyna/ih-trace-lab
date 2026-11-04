# Unified dashboard — plan and working folder

Goal: one dashboard for top management (bird's-eye project health) that replaces the separate MDRM, CTAP and Client Identity dashboards the team watches today, with drill-down for the SRE team.

Status: discovery (phase 1). Nothing built yet.

## Decisions so far

- Audience: top management for the summary view, the internal team for drill-down. Internal only, SSO behind the proxy.
- Data: multiple sources (Lightstep, Athena, others later). Freshness: live / auto-refresh.
- Design first with mock JSON, then data contract, then backend and wiring. Do not write one giant prompt; each phase ends in a written artifact and a review gate.

## Recommended stack

- Frontend: Next.js (React, TypeScript) + Tailwind + shadcn/ui + Apache ECharts (Tremor is a faster but less flexible alternative) + TanStack Query + Framer Motion.
- Backend: FastAPI (reuses this repo's Python and tenant-resolution code), one connector per source behind a common interface that returns a normalised timeseries/table shape.
- Live data: poll every 15-60s via TanStack Query (or SSE). Athena cannot be live: run scheduled queries, cache results, show a "last updated" badge.
- Risks: Lightstep rate limits (cache server-side so N viewers cause one upstream call); API keys must never reach the browser.
- Alternatives considered: Grafana (fast, but not customisable and Lightstep is not a native source); Streamlit / Evidence.dev (quick, but not a 2026 product look).

## Phases and gates

1. Discovery: requirements note covering the exec questions and 5-8 KPIs per product (MDRM, CTAP, Client Identity), each tied to the decision it supports. Gate: review.
2. UI design: information architecture, wireframes, design-token file, then a clickable Next.js prototype on mock JSON. Gate: look and feel approved.
3. Data contract: JSON schema per panel, then Lightstep and Athena connectors.
4. Backend, wiring, hardening.

## Exec-view design principles

- Top row of 4-6 health KPIs (RAG status, SLO, error rate, trend sparkline); one section per product, summary to detail drill-down.
- Dark-mode-first, a single accent colour, a "last updated" badge on every tile, only 3-4 chart types.

## Inputs needed (put them in `inputs/`)

- Screenshots or a list of the dashboards and metrics the team watches today.
- 2-3 dashboards you find visually good, as visual references.

## Starter prompt for phase 1 (discovery + IA + design tokens)

> Act as a product designer and frontend lead. Goal: a single unified dashboard replacing separate monitoring dashboards for MDRM, CTAP and Client Identity. Audience: top management (bird's-eye
> project health), with drill-down for my SRE team. Data comes later from Lightstep and Athena. Phase 1 only: (a) propose 5-8 exec KPIs per product with the decision each supports, (b) an information
> architecture and layout wireframe in Mermaid or ASCII, (c) a design-token spec for a modern 2026 look (dark-first, shadcn/ui, ECharts). Do not write code or call any data tool yet. Save to
> `docs/analysis/2026-11-04_unified-dashboard/`, then stop for my review.

## Next files in this folder

- `01-kpis.md`, `02-information-architecture.md`, `03-design-tokens.md` (phase 1 outputs); further phases get the next numbers.
