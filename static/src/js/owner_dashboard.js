/** @odoo-module **/
/**
 * Owner Executive Dashboard — rental_management
 * Oman-focused · Blue theme · Subproject/Building-centric
 */

import {registry}    from "@web/core/registry";
import {Component, onWillStart, useState, onMounted} from "@odoo/owl";
import {useService}  from "@web/core/utils/hooks";
import {loadJS}      from "@web/core/assets";

// ── Field lists ──────────────────────────────────────────────────────────────
const JSON_FIELDS = [
    "subprojects_by_status", "subprojects_by_type", "subprojects_by_city",
    "units_by_status", "revenue_by_month", "rent_vs_sale_revenue",
    "top_subprojects", "contract_status_data", "maintenance_by_month",
    "payment_status_breakdown", "occupancy_by_city", "map_subprojects",
    "monthly_new_contracts", "bed_availability_by_sub", "top_landlords",
];
const NUMERIC_FIELDS = [
    "total_subprojects", "active_subprojects",
    "total_units", "available_units", "rented_units", "sold_units", "booked_units",
    "occupancy_rate",
    "total_beds", "available_beds", "occupied_beds", "bed_occupancy_rate",
    "total_rent_revenue", "total_sale_revenue", "total_maintenance_cost",
    "outstanding_invoices", "collected_rent", "pending_rent",
    "active_rent_contracts", "expiring_soon_count", "expired_contracts",
    "active_sale_contracts",
    "total_customers", "total_landlords", "total_brokers",
];

const LEAFLET_CSS = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css";
const LEAFLET_JS  = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js";

function safeParse(val) {
    if (Array.isArray(val) || (val && typeof val === "object")) return val;
    try { return JSON.parse(val || "[]"); } catch { return []; }
}

function fmtCurrency(val) {
    if (!val) return "0";
    if (val >= 1_000_000) return (val / 1_000_000).toFixed(1) + "M";
    if (val >= 1_000)     return (val / 1_000).toFixed(1)     + "K";
    return val.toFixed(0);
}

// ── Component ────────────────────────────────────────────────────────────────
class OwnerPropertyDashboard extends Component {
    setup() {
        this.orm    = useService("orm");
        this.action = useService("action");
        this._leafletMap = null;

        this.state = useState({
            ...Object.fromEntries(NUMERIC_FIELDS.map(f => [f, 0])),
            ...Object.fromEntries(JSON_FIELDS.map(f => [f, []])),
            loading:      true,
            dashboardId:  null,
            dateFrom:     null,
            dateTo:       null,
            quickFilters: {today: false, thisWeek: false, thisMonth: false, lastMonth: false, thisYear: false},
        });

        onWillStart(async () => {
            await loadJS("/web/static/lib/Chart/Chart.js");
            if (!document.querySelector('link[href*="leaflet"]')) {
                const lk = document.createElement("link");
                lk.rel = "stylesheet"; lk.href = LEAFLET_CSS;
                document.head.appendChild(lk);
            }
            if (!window.L) await loadJS(LEAFLET_JS);
            await this.loadDashboardData();
        });

        onMounted(() => {
            if (!this.state.loading) { this.renderCharts(); this.renderMap(); }
        });
    }

    _allFields() { return [...NUMERIC_FIELDS, ...JSON_FIELDS]; }

    _applyData(record) {
        for (const f of NUMERIC_FIELDS) { if (f in record) this.state[f] = record[f] || 0; }
        for (const f of JSON_FIELDS)    { if (f in record) this.state[f] = safeParse(record[f]); }
    }

    // ── Data loading ──────────────────────────────────────────────────────────
    async loadDashboardData() {
        try {
            const ids = await this.orm.call("owner.property.dashboard", "search", [[]]);
            const id  = ids.length
                ? ids[0]
                : await this.orm.call("owner.property.dashboard", "create", [{}]);
            this.state.dashboardId = id;
            await this._readData(id);
            this.state.loading = false;
            setTimeout(() => { this.renderCharts(); this.renderMap(); }, 60);
        } catch (err) {
            console.error("Owner Dashboard Load Error", err);
            this.state.loading = false;
        }
    }

    async _readData(id) {
        const data = await this.orm.call("owner.property.dashboard", "read", [[id], this._allFields()]);
        if (data && data.length) this._applyData(data[0]);
    }

    async applyDateFilter() {
        if (!this.state.dashboardId) return;
        this.state.loading = true;
        try {
            await this.orm.call("owner.property.dashboard", "write", [[this.state.dashboardId], {
                date_from: this.state.dateFrom || false,
                date_to:   this.state.dateTo   || false,
            }]);
            await this._readData(this.state.dashboardId);
            this.state.loading = false;
            setTimeout(() => { this.renderCharts(); this.renderMap(); }, 60);
        } catch (err) {
            console.error("Filter error", err);
            this.state.loading = false;
        }
    }

    async clearDateFilter() {
        this.state.dateFrom = null;
        this.state.dateTo   = null;
        this.resetQuickFilters();
        await this.applyDateFilter();
    }

    // ── Quick filters ─────────────────────────────────────────────────────────
    setQuickFilter(filter) {
        this.resetQuickFilters();
        this.state.quickFilters[filter] = true;
        const today = new Date();
        let df, dt;
        switch (filter) {
            case "today":
                df = dt = this._fmt(today); break;
            case "thisWeek": {
                const f = new Date(today); f.setDate(today.getDate() - today.getDay());
                const l = new Date(today); l.setDate(today.getDate() - today.getDay() + 6);
                df = this._fmt(f); dt = this._fmt(l); break;
            }
            case "thisMonth":
                df = this._fmt(new Date(today.getFullYear(), today.getMonth(), 1));
                dt = this._fmt(new Date(today.getFullYear(), today.getMonth() + 1, 0)); break;
            case "lastMonth":
                df = this._fmt(new Date(today.getFullYear(), today.getMonth() - 1, 1));
                dt = this._fmt(new Date(today.getFullYear(), today.getMonth(), 0)); break;
            case "thisYear":
                df = this._fmt(new Date(today.getFullYear(), 0, 1));
                dt = this._fmt(new Date(today.getFullYear(), 11, 31)); break;
        }
        this.state.dateFrom = df;
        this.state.dateTo   = dt;
        this.applyDateFilter();
    }

    resetQuickFilters() {
        Object.keys(this.state.quickFilters).forEach(k => this.state.quickFilters[k] = false);
    }

    _fmt(d) {
        return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}-${String(d.getDate()).padStart(2,"0")}`;
    }

    onDateFromChange(ev) { this.state.dateFrom = ev.target.value; this.resetQuickFilters(); }
    onDateToChange(ev)   { this.state.dateTo   = ev.target.value; this.resetQuickFilters(); }

    // ── Chart helpers ─────────────────────────────────────────────────────────
    _chart(id, type, data, options) {
        const canvas = document.getElementById(id);
        if (!canvas) return;
        const ex = Chart.getChart(canvas);
        if (ex) ex.destroy();
        new Chart(canvas, {type, data, options});
    }

    renderCharts() {
        if (this.state.loading) return;
        try {
            this._chartSubStatus();
            this._chartSubType();
            this._chartSubByCity();
            this._chartUnitStatus();
            this._chartPaymentStatus();
            this._chartRevByMonth();
            this._chartNewContracts();
            this._chartContractStatus();
            this._chartOccByCity();
            this._chartMaintByMonth();
            this._chartRentVsSale();
            this._chartBedAvail();
        } catch (e) { console.error("Chart error", e); }
    }

    _chartSubStatus() {
        const d = this.state.subprojects_by_status;
        this._chart("opdChartSubStatus", "doughnut", {
            labels: d.map(x => x.status),
            datasets: [{data: d.map(x => x.count), backgroundColor: ["#94a3b8","#22c55e","#ef4444","#374151"]}],
        }, {responsive:true, maintainAspectRatio:false, plugins:{legend:{position:"bottom"}}});
    }

    _chartSubType() {
        const d = this.state.subprojects_by_type;
        this._chart("opdChartSubType", "doughnut", {
            labels: d.map(x => x.type),
            datasets: [{data: d.map(x => x.count), backgroundColor: ["#3b82f6","#10b981","#f59e0b","#8b5cf6"]}],
        }, {responsive:true, maintainAspectRatio:false, plugins:{legend:{position:"bottom"}}});
    }

    _chartSubByCity() {
        const d = this.state.subprojects_by_city;
        this._chart("opdChartSubCity", "bar", {
            labels: d.map(x => x.city),
            datasets: [{label:"Buildings", data:d.map(x=>x.count), backgroundColor:"#3b82f6"}],
        }, {indexAxis:"y", responsive:true, maintainAspectRatio:false,
            scales:{x:{beginAtZero:true}}, plugins:{legend:{display:false}}});
    }

    _chartUnitStatus() {
        const d = this.state.units_by_status;
        const colors = ["#94a3b8","#22c55e","#f59e0b","#3b82f6","#a855f7","#6b7280"];
        this._chart("opdChartUnitStatus", "doughnut", {
            labels: d.map(x => x.status),
            datasets: [{data: d.map(x => x.count), backgroundColor: colors}],
        }, {responsive:true, maintainAspectRatio:false, plugins:{legend:{position:"bottom"}}});
    }

    _chartPaymentStatus() {
        const d = this.state.payment_status_breakdown;
        this._chart("opdChartPayment", "doughnut", {
            labels: d.map(x => x.label),
            datasets: [{data:d.map(x=>x.value), backgroundColor:["#10b981","#ef4444","#f59e0b","#60a5fa"]}],
        }, {responsive:true, maintainAspectRatio:false, plugins:{legend:{position:"bottom"}}});
    }

    _chartRevByMonth() {
        const d = this.state.revenue_by_month;
        this._chart("opdChartRevMonth", "line", {
            labels: d.map(x=>x.month),
            datasets: [
                {label:"Rent Revenue", data:d.map(x=>x.rent), borderColor:"#3b82f6", backgroundColor:"rgba(59,130,246,.15)", tension:0.4, fill:true},
                {label:"Sale Revenue", data:d.map(x=>x.sale), borderColor:"#10b981", backgroundColor:"rgba(16,185,129,.15)", tension:0.4, fill:true},
            ],
        }, {responsive:true, maintainAspectRatio:false, plugins:{legend:{position:"top"}}});
    }

    _chartNewContracts() {
        const d = this.state.monthly_new_contracts;
        this._chart("opdChartNewContracts", "bar", {
            labels: d.map(x=>x.month),
            datasets: [
                {label:"Rent Contracts", data:d.map(x=>x.rent), backgroundColor:"rgba(59,130,246,.75)"},
                {label:"Sale Contracts", data:d.map(x=>x.sale), backgroundColor:"rgba(16,185,129,.75)"},
            ],
        }, {responsive:true, maintainAspectRatio:false, plugins:{legend:{position:"top"}}});
    }

    _chartContractStatus() {
        const d = this.state.contract_status_data;
        this._chart("opdChartContractStatus", "pie", {
            labels: d.map(x=>x.status),
            datasets: [{data:d.map(x=>x.count), backgroundColor:["#94a3b8","#3b82f6","#ef4444","#64748b","#f59e0b"]}],
        }, {responsive:true, maintainAspectRatio:false, plugins:{legend:{position:"bottom"}}});
    }

    _chartOccByCity() {
        const d = this.state.occupancy_by_city;
        this._chart("opdChartOccCity", "bar", {
            labels: d.map(x=>x.city),
            datasets: [
                {label:"Total Units",     data:d.map(x=>x.total),     backgroundColor:"rgba(59,130,246,.25)"},
                {label:"Available Units", data:d.map(x=>x.available), backgroundColor:"rgba(34,197,94,.7)"},
                {label:"Rented Units",    data:d.map(x=>x.rented),    backgroundColor:"rgba(59,130,246,.85)"},
            ],
        }, {responsive:true, maintainAspectRatio:false, plugins:{legend:{position:"top"}}});
    }

    _chartMaintByMonth() {
        const d = this.state.maintenance_by_month;
        this._chart("opdChartMaint", "bar", {
            labels: d.map(x=>x.month),
            datasets: [{label:"Maintenance Requests", data:d.map(x=>x.requests), backgroundColor:"rgba(245,158,11,.8)"}],
        }, {responsive:true, maintainAspectRatio:false, plugins:{legend:{display:false}}});
    }

    _chartRentVsSale() {
        const d = this.state.rent_vs_sale_revenue;
        this._chart("opdChartRentVsSale", "doughnut", {
            labels: d.map(x=>x.label),
            datasets: [{data:d.map(x=>x.value), backgroundColor:["#3b82f6","#10b981"]}],
        }, {responsive:true, maintainAspectRatio:false, plugins:{legend:{position:"bottom"}}});
    }

    _chartBedAvail() {
        const d = this.state.bed_availability_by_sub;
        const canvas  = document.getElementById("opdChartBedAvail");
        const wrapper = document.getElementById("opdChartBedWrap");
        if (!canvas || !wrapper) return;
        const minW = Math.max(600, d.length * 90);
        wrapper.style.width = minW + "px";
        canvas.style.width  = minW + "px";
        const ex = Chart.getChart(canvas);
        if (ex) ex.destroy();
        new Chart(canvas, {
            type: "bar",
            data: {
                labels: d.map(x => x.name),
                datasets: [
                    {label:"Total Beds",     data:d.map(x=>x.total_beds), backgroundColor:"rgba(59,130,246,.25)"},
                    {label:"Occupied Beds",  data:d.map(x=>x.occ_beds),   backgroundColor:"rgba(239,68,68,.75)"},
                    {label:"Available Beds", data:d.map(x=>x.avail_beds), backgroundColor:"rgba(34,197,94,.8)"},
                ],
            },
            options:{
                responsive:false, maintainAspectRatio:false,
                scales:{x:{ticks:{maxRotation:35}}, y:{beginAtZero:true}},
                plugins:{legend:{position:"top"}},
            },
        });
    }

    // ── Oman Map (subproject pins) ────────────────────────────────────────────
    renderMap() {
        if (!window.L) return;
        const container = document.getElementById("opdOmanMap");
        if (!container) return;

        if (this._leafletMap) { this._leafletMap.remove(); this._leafletMap = null; }

        const map = L.map("opdOmanMap", {center:[23.58, 58.38], zoom:10, minZoom:5, maxZoom:18});
        this._leafletMap = map;

        L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
            attribution:'© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
            maxZoom:19,
        }).addTo(map);

        const subs = this.state.map_subprojects;

        subs.forEach(s => {
            const color     = s.color;
            const isExact   = s.is_exact;
            const ringColor = isExact ? "white" : "#fde68a";   // yellow ring = approx location

            // Circle size scales with total units (min 14, max 36)
            const size = Math.min(36, Math.max(14, 14 + Math.sqrt(s.total) * 2.5));
            const half = size / 2;

            const icon = L.divIcon({
                className: "",
                html: `<div style="
                    width:${size}px; height:${size}px;
                    border-radius:50%;
                    background:${color};
                    border:2.5px solid ${ringColor};
                    box-shadow:0 2px 8px rgba(0,0,0,0.35);
                    display:flex; align-items:center; justify-content:center;
                    color:white; font-size:${Math.max(9, half - 2)}px; font-weight:700;
                    font-family:Inter,sans-serif;
                ">${s.total}</div>`,
                iconSize:   [size, size],
                iconAnchor: [half, half],
            });

            const occRate  = s.total ? Math.round(s.rented / s.total * 100) : 0;
            const bedLine  = s.total_beds
                ? `<tr><td>Beds Available</td><td><b style="color:#22c55e">${s.avail_beds}</b> / ${s.total_beds}</td></tr>`
                : "";

            L.marker([s.lat, s.lon], {icon}).addTo(map).bindPopup(`
                <div style="font-family:Inter,sans-serif;min-width:220px;">
                    <div style="background:linear-gradient(135deg,#1e3a8a,#1d4ed8);color:white;margin:-13px -20px 10px;padding:10px 14px;border-radius:4px 4px 0 0;">
                        <strong style="font-size:0.95rem">${s.name}</strong><br>
                        <span style="font-size:0.75rem;opacity:.8">${s.project}</span>
                    </div>
                    <table style="width:100%;border-collapse:collapse;font-size:0.8rem;">
                        <tr><td style="padding:3px 0;color:#64748b">City</td><td><b>${s.city}</b></td></tr>
                        <tr><td style="color:#64748b">Type</td><td><b>${s.type}</b></td></tr>
                        <tr style="background:#f0f9ff"><td style="color:#64748b;padding:4px 0">Total Units</td><td><b style="color:#1d4ed8;font-size:1rem">${s.total}</b></td></tr>
                        <tr><td style="color:#64748b">Available</td><td><b style="color:#22c55e">${s.available}</b></td></tr>
                        <tr><td style="color:#64748b">Rented</td><td><b style="color:#3b82f6">${s.rented}</b></td></tr>
                        <tr><td style="color:#64748b">Booked</td><td><b style="color:#f59e0b">${s.booked}</b></td></tr>
                        ${bedLine}
                        <tr style="background:#f0f9ff"><td style="color:#64748b;padding:4px 0">Occupancy</td>
                            <td><b style="color:${occRate>75?'#22c55e':occRate>40?'#f59e0b':'#ef4444'}">${occRate}%</b></td></tr>
                        ${!s.is_exact ? '<tr><td colspan="2" style="color:#92400e;font-size:0.7rem;padding-top:5px">⚠ Approximate location (set exact GPS on subproject)</td></tr>' : ''}
                    </table>
                </div>
            `, {maxWidth: 280});
        });

        // Fit to pins, fall back to Muscat area
        const valid = subs.filter(s => s.is_exact);
        if (valid.length > 0) {
            const bounds = L.latLngBounds(valid.map(s => [s.lat, s.lon]));
            map.fitBounds(bounds, {padding: [40, 40]});
        } else if (subs.length > 0) {
            map.fitBounds(L.latLngBounds(subs.map(s => [s.lat, s.lon])), {padding:[40,40]});
        } else {
            map.setView([23.58, 58.38], 10);
        }
    }

    // ── Navigation helpers ────────────────────────────────────────────────────
    openView(model, name, domain = []) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name,
            res_model: model,
            views: [[false, "list"], [false, "form"]],
            domain,
        });
    }

    fmt(val)   { return fmtCurrency(val); }
    pct(v, t)  { return t ? Math.round(v / t * 100) : 0; }
}

OwnerPropertyDashboard.template = "rental_management.OwnerPropertyDashboard";
registry.category("actions").add("owner_property_dashboard", OwnerPropertyDashboard);
