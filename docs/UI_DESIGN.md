# UI Design Spec — RetailPulse Dashboard

Derived from the attached reference screenshot (a "Dash" social-analytics dashboard). Same layout language, remapped to retail demand forecasting content.

## 1. Visual language (from reference)
- **Palette**: near-black sidebar/header (`#0F1211`-ish) with a lime/acid-green accent (`#C8F169`-ish) for active states, primary buttons, and highlight bars. White content background. Soft mint-green card backgrounds for stat tiles.
- **Typography**: bold, rounded sans-serif for headings; medium weight for stat numbers (large, ~28–32px); small uppercase-ish labels for section eyebrows.
- **Shape language**: fully rounded corners (16–24px radius) on cards, pill-shaped buttons/toggles, circular icon badges.
- **Density**: generous padding, card-based grid, no harsh borders — separation via background color and shadow only.

## 2. Layout structure

### Sidebar (left, dark, fixed width ~240px)
- Logo + app name at top (RetailPulse), collapse toggle.
- **Main menu**: Dashboard (active), Anomaly Feed (badge with open-anomaly count, like the reference's "Inbox: 7"), Forecast Explorer.
- **Workspace**: Products, Stores, Knowledge Graph *(V2)*, Analytics.
- **General**: File & Reports, Settings.
- Bottom-of-sidebar help card: "Need help with RetailPulse? → Go to docs" (mirrors reference's help widget), acid-green CTA button.

### Header (top bar)
- Page title ("Dashboard") left-aligned, bold.
- Right side: search icon, notification bell (badge = open anomalies), user avatar + name + role dropdown.

### Row 1 — Stat cards (3 cards, mint-green background, rounded, icon badge top-left)
Mirrors the reference's Total Reach / Paid Reach / Organic Reach cards:
- **Total Forecasted Demand** (this period) — big number + unit (units or $)
- **Total Actual Sales** — big number
- **Open Anomalies** — big number (red/amber accent instead of green if >0)

### Row 2 — Trend chart (large card, spans ~2/3 width)
- Line chart: **Actual vs Forecast** over time, third line optional for "Confidence band" (shaded area instead of a hard line).
- Top-right pill toggle: **Daily / Weekly / Monthly**, active state = dark pill on lime background (matches reference exactly).
- Hover tooltip on a data point shows a small popover card: date, Actual, Forecast, Anomaly flag if any — same interaction as the reference's "Jul 2021 — Reach / Paid Reach / Organic Reach" tooltip.
- X-axis: month or date labels depending on toggle.

### Row 3, left — "Demand Breakdown" donut (replaces reference's "Demographic")
- Donut chart: % of demand by product category, with legend dots.
- Adjacent mini bar-list: age-bracket style breakdown becomes **stock-status breakdown** — e.g., "In stock", "Low stock", "Stockout risk" — each with count + % bar, colored dot.
- "See Detail →" link top-right of card.

### Row 3, right — "Top Products at Risk" (replaces reference's "Top Channels")
- List rows, each with: icon/badge, product name + store, a metric (e.g., "Stockout in 2 days"), and a small horizontal progress/severity bar colored by risk level.
- "See Detail →" link top-right.

## 3. Component inventory to build
| Component | Notes |
|---|---|
| `Sidebar` | collapsible, active-item highlight in lime, badge counts |
| `TopBar` | search, notifications, user menu |
| `StatCard` | icon, label, big number, mint background, optional up/down delta chip |
| `TrendChart` | Plotly/Recharts line chart, hover tooltip card, Daily/Weekly/Monthly pill toggle |
| `DonutBreakdown` | donut + side legend/metric list |
| `RankedList` | icon + label + metric + mini progress bar, used for "Top Products at Risk" |
| `HelpCard` | small promo card pinned to sidebar bottom |
| `AnomalyBadge` | small numeric badge, reused in sidebar nav + notification bell |

## 4. Screens
1. **Overview** (the layout above) — default landing page.
2. **Forecast Explorer** — SKU/store picker, same `TrendChart` component scoped to one item, confidence band always shown.
3. **Anomaly Feed** — table/list of `predictions.anomaly` rows, filter by severity/type, "Acknowledge" action button (pill, lime).
4. **Knowledge Graph Explorer** *(V2)* — force-directed graph view of product/store/supplier relationships (can reuse a library like `react-force-graph` or Neo4j Bloom embed).

## 5. Responsiveness
- Sidebar collapses to icon-only rail below ~1024px.
- Row 2/3 cards stack vertically on mobile widths; stat cards go from 3-across to 1-across.

## 6. Notes for the builder (Antigravity)
- If building with Streamlit for MVP: approximate this with `st.columns` for the stat-card row, `st.plotly_chart` for the trend chart with a `st.radio`/segmented control for Daily/Weekly/Monthly, and custom CSS (via `st.markdown` with `<style>`) to get the rounded-card, dark-sidebar look.
- If building a separate React/Next.js frontend (optional polish pass) instead of Streamlit, this spec maps directly to a component library like shadcn/ui + Tailwind, matching the palette above.
