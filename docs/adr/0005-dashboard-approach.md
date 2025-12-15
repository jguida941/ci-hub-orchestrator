# ADR-0005: Dashboard Approach

- Status: Proposed
- Date: 2025-12-14

## Context

The hub produces `hub-report.json` with metrics across all repos. We need a way to visualize this data. Questions:
- What technology should power the dashboard?
- Where should it be hosted?
- How does it get updated?
- What level of interactivity is needed?

## Decision

**Approach:** Static JSON + GitHub Pages

1. **Data source:** `hub-report.json` artifact from each hub run
2. **Hosting:** GitHub Pages on the hub repository
3. **Updates:** Workflow commits updated JSON to `gh-pages` branch after each run
4. **Frontend:** Static HTML/JS that fetches and renders the JSON

**Architecture:**
```
hub-run-all / hub-orchestrator
    ↓
hub-report.json (artifact)
    ↓
publish-dashboard.yml (workflow)
    ↓
gh-pages branch: metrics.json, index.html
    ↓
https://user.github.io/ci-cd-hub/
```

**Dashboard Views:**

1. **Overview page:**
   - All repos in a table/card layout
   - Coverage and mutation scores with color coding
   - Pass/fail status badges
   - Last run timestamp

2. **Drill-down per repo:**
   - Historical trend (if we store multiple runs)
   - Tool-specific results
   - Links to GitHub Actions runs

## Alternatives Considered

1. **Grafana + InfluxDB/Prometheus:**
   - Pros: Rich visualization, alerting, historical data
   - Cons: Requires infrastructure, overkill for current needs
   - Decision: Rejected for MVP. Consider for v2 if historical trending needed.

2. **Dedicated metrics service (DataDog, New Relic):**
   - Pros: Professional tooling, integrations
   - Cons: Cost, vendor lock-in, external dependency
   - Decision: Rejected. Keep it simple and self-hosted.

3. **GitHub Actions step summary only:**
   - Pros: Zero infrastructure, already implemented
   - Cons: No persistent view, requires navigating to specific runs
   - Decision: Keep step summaries, but add dashboard for persistent overview.

4. **GitHub README badges only:**
   - Pros: Simple, visible on repo page
   - Cons: Limited data, no drill-down, no historical view
   - Decision: Add badges, but dashboard provides more detail.

## Consequences

**Positive:**
- Zero infrastructure cost (GitHub Pages is free)
- No external dependencies
- Updates automatically on each hub run
- Accessible via public URL
- Simple to maintain (static files)

**Negative:**
- No real-time updates (only on workflow run)
- Limited historical data (unless we append to JSON)
- Basic interactivity (no database queries)
- Requires workflow to commit to gh-pages branch

**Implementation Notes:**

1. **Dashboard files location:**
   ```
   dashboards/
   ├── index.html      # Overview page
   ├── repo.html       # Per-repo drill-down
   ├── styles.css      # Styling
   └── app.js          # Fetch and render logic
   ```

2. **Data file on gh-pages:**
   ```
   metrics.json        # Latest hub-report.json
   history/            # Optional: historical runs
   ```

3. **Publish workflow triggers:**
   - After hub-run-all completes
   - After hub-orchestrator completes
   - Commits to gh-pages branch

## Future Work

- Add historical trending (append runs to history/)
- Add filtering by language, status, date range
- Add Slack/email digest based on dashboard data
- Consider Grafana for advanced visualization needs

## Current Status

**NOT YET IMPLEMENTED.** This ADR documents the planned approach. Implementation is tracked in requirements/P1.md section 4.

