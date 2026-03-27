# Dashboard Patterns Reference

Self-contained HTML/JS dashboard patterns using Chart.js. All dashboards are single-file HTML — no server required, shareable as email attachments.

## Base Template

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard Title</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>
    <!-- Only needed for time-axis charts: -->
    <script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns@3.0.0/dist/chartjs-adapter-date-fns.bundle.min.js"></script>
    <style>/* See CSS System below */</style>
</head>
<body>
    <div class="dashboard-container">
        <header class="dashboard-header">
            <h1>Dashboard Title</h1>
            <div class="filters"><!-- Filter controls --></div>
        </header>
        <section class="kpi-row"><!-- KPI cards --></section>
        <section class="chart-row"><!-- Chart containers --></section>
        <section class="table-section"><!-- Data table --></section>
        <footer class="dashboard-footer">
            <span>Data as of: <span id="data-date"></span></span>
        </footer>
    </div>
    <script>
        const DATA = []; // Embedded query results
        class Dashboard {
            constructor(data) {
                this.rawData = data;
                this.filteredData = data;
                this.charts = {};
                this.init();
            }
            init() {
                this.setupFilters();
                this.renderKPIs();
                this.renderCharts();
                this.renderTable();
            }
            applyFilters() {
                this.filteredData = this.rawData.filter(row => { return true; });
                this.renderKPIs();
                this.updateCharts();
                this.renderTable();
            }
        }
        const dashboard = new Dashboard(DATA);
    </script>
</body>
</html>
```

## KPI Cards

```html
<div class="kpi-card">
    <div class="kpi-label">Total Revenue</div>
    <div class="kpi-value" id="kpi-revenue">$0</div>
    <div class="kpi-change positive" id="kpi-revenue-change">+0%</div>
</div>
```

```javascript
function renderKPI(elementId, value, previousValue, format = 'number') {
    const el = document.getElementById(elementId);
    const changeEl = document.getElementById(elementId + '-change');
    el.textContent = formatValue(value, format);
    if (previousValue && previousValue !== 0) {
        const pctChange = ((value - previousValue) / previousValue) * 100;
        const sign = pctChange >= 0 ? '+' : '';
        changeEl.textContent = `${sign}${pctChange.toFixed(1)}% vs prior period`;
        changeEl.className = `kpi-change ${pctChange >= 0 ? 'positive' : 'negative'}`;
    }
}

function formatValue(value, format) {
    switch (format) {
        case 'currency':
            if (value >= 1e6) return `$${(value / 1e6).toFixed(1)}M`;
            if (value >= 1e3) return `$${(value / 1e3).toFixed(1)}K`;
            return `$${value.toFixed(0)}`;
        case 'percent':
            return `${value.toFixed(1)}%`;
        case 'number':
            if (value >= 1e6) return `${(value / 1e6).toFixed(1)}M`;
            if (value >= 1e3) return `${(value / 1e3).toFixed(1)}K`;
            return value.toLocaleString();
        default:
            return value.toString();
    }
}
```

## Chart Patterns

### Line Chart

```javascript
const COLORS = ['#4C72B0', '#DD8452', '#55A868', '#C44E52', '#8172B3', '#937860'];

function createLineChart(canvasId, labels, datasets) {
    const ctx = document.getElementById(canvasId).getContext('2d');
    return new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: datasets.map((ds, i) => ({
                label: ds.label,
                data: ds.data,
                borderColor: COLORS[i % COLORS.length],
                backgroundColor: COLORS[i % COLORS.length] + '20',
                borderWidth: 2,
                fill: ds.fill || false,
                tension: 0.3,
                pointRadius: 3,
                pointHoverRadius: 6,
            }))
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: { position: 'top', labels: { usePointStyle: true, padding: 20 } },
                tooltip: {
                    callbacks: {
                        label: ctx => `${ctx.dataset.label}: ${formatValue(ctx.parsed.y, 'currency')}`
                    }
                }
            },
            scales: {
                x: { grid: { display: false } },
                y: {
                    beginAtZero: true,
                    ticks: { callback: value => formatValue(value, 'currency') }
                }
            }
        }
    });
}
```

### Bar Chart

```javascript
function createBarChart(canvasId, labels, data, options = {}) {
    const ctx = document.getElementById(canvasId).getContext('2d');
    const isHorizontal = options.horizontal || labels.length > 8;
    return new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: options.label || 'Value',
                data: data,
                backgroundColor: (options.colors || COLORS).map(c => c + 'CC'),
                borderColor: options.colors || COLORS,
                borderWidth: 1,
                borderRadius: 4,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: isHorizontal ? 'y' : 'x',
            plugins: { legend: { display: false } },
            scales: {
                x: { beginAtZero: true, grid: { display: isHorizontal } },
                y: { beginAtZero: !isHorizontal, grid: { display: !isHorizontal } }
            }
        }
    });
}
```

### Doughnut Chart

```javascript
function createDoughnutChart(canvasId, labels, data) {
    const ctx = document.getElementById(canvasId).getContext('2d');
    return new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: COLORS.map(c => c + 'CC'),
                borderColor: '#ffffff',
                borderWidth: 2,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '60%',
            plugins: {
                legend: { position: 'right', labels: { usePointStyle: true, padding: 15 } },
                tooltip: {
                    callbacks: {
                        label: ctx => {
                            const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                            const pct = ((ctx.parsed / total) * 100).toFixed(1);
                            return `${ctx.label}: ${formatValue(ctx.parsed, 'number')} (${pct}%)`;
                        }
                    }
                }
            }
        }
    });
}
```

### Updating Charts on Filter Change

```javascript
function updateChart(chart, newLabels, newData) {
    chart.data.labels = newLabels;
    if (Array.isArray(newData[0])) {
        newData.forEach((data, i) => { chart.data.datasets[i].data = data; });
    } else {
        chart.data.datasets[0].data = newData;
    }
    chart.update('none'); // 'none' = no animation for instant update
}
```

## Filters

### Dropdown Filter

```html
<div class="filter-group">
    <label for="filter-region">Region</label>
    <select id="filter-region" onchange="dashboard.applyFilters()">
        <option value="all">All Regions</option>
    </select>
</div>
```

```javascript
function populateFilter(selectId, data, field) {
    const select = document.getElementById(selectId);
    const values = [...new Set(data.map(d => d[field]))].sort();
    values.forEach(val => {
        const option = document.createElement('option');
        option.value = val;
        option.textContent = val;
        select.appendChild(option);
    });
}

function getFilterValue(selectId) {
    const val = document.getElementById(selectId).value;
    return val === 'all' ? null : val;
}
```

### Date Range Filter

```html
<div class="filter-group">
    <label>Date Range</label>
    <input type="date" id="filter-date-start" onchange="dashboard.applyFilters()">
    <span>to</span>
    <input type="date" id="filter-date-end" onchange="dashboard.applyFilters()">
</div>
```

### Combined Filter Logic

```javascript
applyFilters() {
    const region = getFilterValue('filter-region');
    const category = getFilterValue('filter-category');
    const startDate = document.getElementById('filter-date-start').value;
    const endDate = document.getElementById('filter-date-end').value;

    this.filteredData = this.rawData.filter(row => {
        if (region && row.region !== region) return false;
        if (category && row.category !== category) return false;
        if (startDate && row.date < startDate) return false;
        if (endDate && row.date > endDate) return false;
        return true;
    });

    this.renderKPIs();
    this.updateCharts();
    this.renderTable();
}
```

## Sortable Data Table

```javascript
function renderTable(containerId, data, columns) {
    const container = document.getElementById(containerId);
    let sortCol = null;
    let sortDir = 'desc';

    function render(sortedData) {
        let html = '<table class="data-table"><thead><tr>';
        columns.forEach(col => {
            const arrow = sortCol === col.field ? (sortDir === 'asc' ? ' ▲' : ' ▼') : '';
            html += `<th onclick="sortTable('${col.field}')" style="cursor:pointer">${col.label}${arrow}</th>`;
        });
        html += '</tr></thead><tbody>';
        sortedData.forEach(row => {
            html += '<tr>';
            columns.forEach(col => {
                const value = col.format ? formatValue(row[col.field], col.format) : row[col.field];
                html += `<td>${value}</td>`;
            });
            html += '</tr>';
        });
        html += '</tbody></table>';
        container.innerHTML = html;
    }

    window.sortTable = function(field) {
        if (sortCol === field) { sortDir = sortDir === 'asc' ? 'desc' : 'asc'; }
        else { sortCol = field; sortDir = 'desc'; }
        const sorted = [...data].sort((a, b) => {
            const cmp = a[field] < b[field] ? -1 : a[field] > b[field] ? 1 : 0;
            return sortDir === 'asc' ? cmp : -cmp;
        });
        render(sorted);
    };

    render(data);
}
```

## CSS System

```css
:root {
    --bg-primary: #f8f9fa;
    --bg-card: #ffffff;
    --bg-header: #1a1a2e;
    --text-primary: #212529;
    --text-secondary: #6c757d;
    --text-on-dark: #ffffff;
    --color-1: #4C72B0;
    --color-2: #DD8452;
    --color-3: #55A868;
    --color-4: #C44E52;
    --color-5: #8172B3;
    --color-6: #937860;
    --positive: #28a745;
    --negative: #dc3545;
    --gap: 16px;
    --radius: 8px;
}

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: var(--bg-primary);
    color: var(--text-primary);
    line-height: 1.5;
}

.dashboard-container { max-width: 1400px; margin: 0 auto; padding: var(--gap); }

.dashboard-header {
    background: var(--bg-header); color: var(--text-on-dark);
    padding: 20px 24px; border-radius: var(--radius); margin-bottom: var(--gap);
    display: flex; justify-content: space-between; align-items: center;
    flex-wrap: wrap; gap: 12px;
}
.dashboard-header h1 { font-size: 20px; font-weight: 600; }

.kpi-row {
    display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: var(--gap); margin-bottom: var(--gap);
}
.kpi-card {
    background: var(--bg-card); border-radius: var(--radius);
    padding: 20px 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}
.kpi-label { font-size: 13px; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px; }
.kpi-value { font-size: 28px; font-weight: 700; margin-bottom: 4px; }
.kpi-change { font-size: 13px; font-weight: 500; }
.kpi-change.positive { color: var(--positive); }
.kpi-change.negative { color: var(--negative); }

.chart-row {
    display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
    gap: var(--gap); margin-bottom: var(--gap);
}
.chart-container {
    background: var(--bg-card); border-radius: var(--radius);
    padding: 20px 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}
.chart-container h3 { font-size: 14px; font-weight: 600; margin-bottom: 16px; }
.chart-container canvas { max-height: 300px; }

.filters { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
.filter-group { display: flex; align-items: center; gap: 6px; }
.filter-group label { font-size: 12px; color: rgba(255,255,255,0.7); }
.filter-group select, .filter-group input[type="date"] {
    padding: 6px 10px; border: 1px solid rgba(255,255,255,0.2);
    border-radius: 4px; background: rgba(255,255,255,0.1);
    color: var(--text-on-dark); font-size: 13px;
}

.table-section {
    background: var(--bg-card); border-radius: var(--radius);
    padding: 20px 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); overflow-x: auto;
}
.data-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.data-table thead th {
    text-align: left; padding: 10px 12px; border-bottom: 2px solid #dee2e6;
    color: var(--text-secondary); font-weight: 600; font-size: 12px;
    text-transform: uppercase; letter-spacing: 0.5px; white-space: nowrap; user-select: none;
}
.data-table thead th:hover { color: var(--text-primary); background: #f8f9fa; }
.data-table tbody td { padding: 10px 12px; border-bottom: 1px solid #f0f0f0; }
.data-table tbody tr:hover { background: #f8f9fa; }

@media (max-width: 768px) {
    .dashboard-header { flex-direction: column; align-items: flex-start; }
    .kpi-row { grid-template-columns: repeat(2, 1fr); }
    .chart-row { grid-template-columns: 1fr; }
    .filters { flex-direction: column; align-items: flex-start; }
}

@media print {
    body { background: white; }
    .dashboard-container { max-width: none; }
    .filters { display: none; }
    .chart-container { break-inside: avoid; }
    .kpi-card { border: 1px solid #dee2e6; box-shadow: none; }
}
```

## Survey Dashboard Pattern

Survey dashboards have a different shape to time-series/revenue dashboards. Typical layout:

**KPI row:** Total respondents, key awareness/satisfaction metric, data quality flag (e.g., straight-liner %)

**Charts:**
- **Horizontal bar** — awareness/action rates sorted by %, with small-n segments highlighted
- **Stacked bar (100%)** — Likert distributions across multiple statements, diverging colour scale (red→amber→green)
- **Grouped bar** — cross-tab comparisons (metric by segment), with base sizes in labels: `"Scotland (n=67)"`

**Data table:** Regional or segment breakdown with all key metrics, small-n rows italicised with ⚠ marker

**Survey-specific tips:**
- Always show base sizes (n=) — survey readers expect them
- Exclude off-scale codes (e.g., 6="prefer not to say") from chart data but note the exclusion
- Highlight statistically significant differences if tested (bold bar, annotation)
- Use warm-to-cool diverging colours for Likert: `['#C44E52', '#DD8452', '#CCB974', '#55A868', '#4C72B0']` maps to strongly disagree → strongly agree

## Performance Guidelines

| Data Size | Approach |
|-----------|----------|
| <1,000 rows | Embed directly in HTML. Full interactivity. |
| 1,000–10,000 rows | Embed in HTML. Pre-aggregate for charts. |
| 10,000–100,000 rows | Pre-aggregate server-side. Embed only aggregated data. |
| >100,000 rows | Not suitable for client-side. Use a BI tool or paginate. |

**Chart limits:**
- Line charts: <500 data points per series (downsample if needed)
- Bar charts: <50 categories
- Scatter plots: <1,000 points (sample larger datasets)
- Disable animations for multi-chart dashboards: `animation: false`
- Use `chart.update('none')` for filter-triggered updates

**DOM limits:**
- Cap visible table rows at 100–200; add pagination for more
- Use `requestAnimationFrame` for coordinated multi-chart updates
