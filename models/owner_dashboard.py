# -*- coding: utf-8 -*-
# Owner Executive Dashboard — rental_management
# Oman-focused | Blue theme | Subproject/Building-centric analytics

import json
import random
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


# ── Oman governorate fallback coordinates ─────────────────────────────────────
OMAN_CITIES = {
    "Muscat":     (23.5880, 58.3829),
    "Salalah":    (17.0151, 54.0924),
    "Sohar":      (24.3475, 56.7570),
    "Nizwa":      (22.9333, 57.5333),
    "Sur":        (22.5679, 59.5289),
    "Ibri":       (23.2261, 56.5138),
    "Buraymi":    (24.2539, 55.7854),
    "Khasab":     (26.1842, 56.2479),
    "Duqm":       (19.6700, 57.7000),
    "Adam":       (22.3851, 57.5269),
    "Bahla":      (22.9699, 57.2993),
    "Ibra":       (22.6931, 58.5329),
    "Rustaq":     (23.3937, 57.4209),
    "Al Buraimi": (24.2539, 55.7854),
    "Haima":      (19.9500, 56.2800),
    "Seeb":       (23.6770, 58.1890),
    "Qurum":      (23.5957, 58.3892),
    "Madinat":    (23.5748, 58.3772),
    "Bowsher":    (23.5980, 58.3400),
    "Mutrah":     (23.6190, 58.5680),
    "Ruwi":       (23.6070, 58.5610),
    "Al Khuwair": (23.6000, 58.3700),
    "Ghubra":     (23.5847, 58.3520),
}

STATUS_COLORS = {
    "available": "#22c55e",
    "on_lease":  "#3b82f6",
    "booked":    "#f59e0b",
    "sale":      "#a855f7",
    "sold":      "#6b7280",
    "draft":     "#94a3b8",
    "closed":    "#374151",
    "cancel":    "#ef4444",
}


def _resolve_lat_lon(lat_str, lon_str, city_name=""):
    """
    Convert Char lat/lon (may be None/"") to float pair.
    Falls back to Oman city lookup, then Muscat default.
    Returns (lat, lon, is_exact) — is_exact=True when real coords found.
    """
    try:
        if lat_str and lon_str:
            lat = float(lat_str)
            lon = float(lon_str)
            if -90 <= lat <= 90 and -180 <= lon <= 180 and (lat != 0 or lon != 0):
                return lat, lon, True
    except (ValueError, TypeError):
        pass

    # City fallback
    city_lower = (city_name or "").lower()
    for key, coords in OMAN_CITIES.items():
        if key.lower() in city_lower or city_lower in key.lower():
            jlat = coords[0] + random.uniform(-0.008, 0.008)
            jlon = coords[1] + random.uniform(-0.008, 0.008)
            return jlat, jlon, False

    # Muscat default with spread
    return (23.5880 + random.uniform(-0.25, 0.25),
            58.3829 + random.uniform(-0.25, 0.25),
            False)


class OwnerPropertyDashboard(models.Model):
    _name = "owner.property.dashboard"
    _description = "Owner Executive Property Dashboard"

    name = fields.Char(default="Owner Executive Dashboard")

    # ── Date filters ──────────────────────────────────────────────────────────
    date_from = fields.Date(string="Date From")
    date_to   = fields.Date(string="Date To")

    # ── Portfolio KPIs (subproject-level) ────────────────────────────────────
    total_subprojects       = fields.Integer(compute="_compute_subproject_kpis")
    active_subprojects      = fields.Integer(compute="_compute_subproject_kpis")
    total_units             = fields.Integer(compute="_compute_subproject_kpis")
    available_units         = fields.Integer(compute="_compute_subproject_kpis")
    rented_units            = fields.Integer(compute="_compute_subproject_kpis")
    sold_units              = fields.Integer(compute="_compute_subproject_kpis")
    booked_units            = fields.Integer(compute="_compute_subproject_kpis")
    occupancy_rate          = fields.Float(compute="_compute_subproject_kpis")

    # Bed KPIs
    total_beds              = fields.Integer(compute="_compute_bed_kpis")
    available_beds          = fields.Integer(compute="_compute_bed_kpis")
    occupied_beds           = fields.Integer(compute="_compute_bed_kpis")
    bed_occupancy_rate      = fields.Float(compute="_compute_bed_kpis")

    # ── Financial KPIs ────────────────────────────────────────────────────────
    total_rent_revenue      = fields.Float(compute="_compute_financial_kpis")
    total_sale_revenue      = fields.Float(compute="_compute_financial_kpis")
    total_maintenance_cost  = fields.Float(compute="_compute_financial_kpis")
    outstanding_invoices    = fields.Float(compute="_compute_financial_kpis")
    collected_rent          = fields.Float(compute="_compute_financial_kpis")
    pending_rent            = fields.Float(compute="_compute_financial_kpis")

    # ── Contract KPIs ─────────────────────────────────────────────────────────
    active_rent_contracts   = fields.Integer(compute="_compute_contract_kpis")
    expiring_soon_count     = fields.Integer(compute="_compute_contract_kpis")
    expired_contracts       = fields.Integer(compute="_compute_contract_kpis")
    active_sale_contracts   = fields.Integer(compute="_compute_contract_kpis")

    # ── People KPIs ───────────────────────────────────────────────────────────
    total_customers         = fields.Integer(compute="_compute_people_kpis")
    total_landlords         = fields.Integer(compute="_compute_people_kpis")
    total_brokers           = fields.Integer(compute="_compute_people_kpis")

    # ── JSON chart / map data ─────────────────────────────────────────────────
    subprojects_by_status    = fields.Text(compute="_compute_subprojects_by_status")
    subprojects_by_type      = fields.Text(compute="_compute_subprojects_by_type")
    subprojects_by_city      = fields.Text(compute="_compute_subprojects_by_city")
    units_by_status          = fields.Text(compute="_compute_units_by_status")
    revenue_by_month         = fields.Text(compute="_compute_revenue_by_month")
    rent_vs_sale_revenue     = fields.Text(compute="_compute_rent_vs_sale_revenue")
    top_subprojects          = fields.Text(compute="_compute_top_subprojects")
    contract_status_data     = fields.Text(compute="_compute_contract_status_data")
    maintenance_by_month     = fields.Text(compute="_compute_maintenance_by_month")
    payment_status_breakdown = fields.Text(compute="_compute_payment_status")
    occupancy_by_city        = fields.Text(compute="_compute_occupancy_by_city")
    map_subprojects          = fields.Text(compute="_compute_map_subprojects")
    monthly_new_contracts    = fields.Text(compute="_compute_monthly_new_contracts")
    bed_availability_by_sub  = fields.Text(compute="_compute_bed_availability_by_sub")
    top_landlords            = fields.Text(compute="_compute_top_landlords")

    # ── Domain helpers ────────────────────────────────────────────────────────
    def _date_domain(self, date_field="create_date"):
        domain = []
        if self.date_from:
            domain.append((date_field, ">=", datetime.combine(self.date_from, datetime.min.time())))
        if self.date_to:
            domain.append((date_field, "<=", datetime.combine(self.date_to, datetime.max.time())))
        return domain

    def _month_range(self):
        result = []
        if self.date_from and self.date_to:
            cur = self.date_from.replace(day=1)
            while cur <= self.date_to:
                start = datetime.combine(cur, datetime.min.time())
                end   = datetime.combine((cur + relativedelta(months=1)) - timedelta(days=1), datetime.max.time())
                result.append((start, end, cur.strftime("%b %Y")))
                cur  += relativedelta(months=1)
        else:
            today = datetime.today()
            for i in range(11, -1, -1):
                m     = today - relativedelta(months=i)
                start = m.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                end   = (start + relativedelta(months=1)) - timedelta(seconds=1)
                result.append((start, end, m.strftime("%b %Y")))
        return result

    # ── Subproject KPIs ───────────────────────────────────────────────────────
    def _compute_subproject_kpis(self):
        Sub  = self.env["property.sub.project"]
        Prop = self.env["property.details"]
        for rec in self:
            all_subs  = Sub.search([])
            active    = all_subs.filtered(lambda s: s.status not in ("cancel", "closed"))
            total_u   = Prop.search_count([])
            available = Prop.search_count([("stage", "=", "available")])
            rented    = Prop.search_count([("stage", "=", "on_lease")])
            sold      = Prop.search_count([("stage", "=", "sold")])
            booked    = Prop.search_count([("stage", "=", "booked")])
            leasable  = total_u - sold
            rec.total_subprojects  = len(all_subs)
            rec.active_subprojects = len(active)
            rec.total_units        = total_u
            rec.available_units    = available
            rec.rented_units       = rented
            rec.sold_units         = sold
            rec.booked_units       = booked
            rec.occupancy_rate     = round(rented / leasable * 100, 1) if leasable else 0.0

    # ── Bed KPIs ──────────────────────────────────────────────────────────────
    def _compute_bed_kpis(self):
        Bed = self.env["property.bed"]
        for rec in self:
            all_beds   = Bed.search([])
            available  = all_beds.filtered(lambda b: b.state == "available")
            occupied   = all_beds.filtered(lambda b: b.state == "occupied")
            total      = len(all_beds)
            rec.total_beds         = total
            rec.available_beds     = len(available)
            rec.occupied_beds      = len(occupied)
            rec.bed_occupancy_rate = round(len(occupied) / total * 100, 1) if total else 0.0

    # ── Financial KPIs ────────────────────────────────────────────────────────
    def _compute_financial_kpis(self):
        RentInv   = self.env["rent.invoice"]
        SaleContr = self.env["property.vendor"]
        Maint     = self.env["account.move"]
        for rec in self:
            date_dom = rec._date_domain("invoice_date")
            rent_invoices = RentInv.search(date_dom + [("type", "=", "rent")])
            rec.total_rent_revenue = sum(rent_invoices.mapped("rent_amount"))
            paid_inv = rent_invoices.filtered(lambda r: r.payment_state == "paid")
            rec.collected_rent = sum(paid_inv.mapped("rent_amount"))
            rec.pending_rent   = rec.total_rent_revenue - rec.collected_rent

            sale_dom = rec._date_domain("date")
            sale_contracts = SaleContr.search(sale_dom + [("stage", "=", "sold")])
            rec.total_sale_revenue = sum(sale_contracts.mapped("price"))

            unpaid = RentInv.search(date_dom + [("payment_state", "!=", "paid")])
            rec.outstanding_invoices = sum(unpaid.mapped("rent_amount"))

            maint_moves = Maint.search([
                ("move_type", "=", "in_invoice"),
                ("state", "=", "posted"),
            ] + rec._date_domain("invoice_date"))
            rec.total_maintenance_cost = sum(
                maint_moves.filtered(
                    lambda m: m.ref and "maint" in (m.ref or "").lower()
                ).mapped("amount_total")
            )

    # ── Contract KPIs ─────────────────────────────────────────────────────────
    def _compute_contract_kpis(self):
        Rent  = self.env["tenancy.details"]
        Sale  = self.env["property.vendor"]
        today = fields.Date.today()
        soon  = today + timedelta(days=30)
        for rec in self:
            running = Rent.search([("contract_type", "=", "running_contract")])
            rec.active_rent_contracts = len(running)
            rec.expiring_soon_count = len(running.filtered(
                lambda r: r.end_date and today <= r.end_date <= soon
            ))
            rec.expired_contracts     = Rent.search_count([("contract_type", "=", "expire_contract")])
            rec.active_sale_contracts = Sale.search_count([("stage", "in", ["booked", "sold"])])

    # ── People KPIs ───────────────────────────────────────────────────────────
    def _compute_people_kpis(self):
        Partner = self.env["res.partner"]
        for rec in self:
            rec.total_customers = Partner.search_count([("user_type", "=", "customer")])
            rec.total_landlords = Partner.search_count([("user_type", "=", "landlord")])
            rec.total_brokers   = Partner.search_count([("user_type", "=", "broker")])

    # ── Subprojects by Status ─────────────────────────────────────────────────
    def _compute_subprojects_by_status(self):
        statuses = {
            "draft": "Draft", "available": "Available",
            "cancel": "Cancelled", "closed": "Closed",
        }
        for rec in self:
            Sub = self.env["property.sub.project"]
            result = [{"status": label, "count": Sub.search_count([("status", "=", key)])}
                      for key, label in statuses.items()]
            rec.subprojects_by_status = json.dumps(result)

    # ── Subprojects by Property Type ──────────────────────────────────────────
    def _compute_subprojects_by_type(self):
        types = {
            "residential": "Residential", "commercial": "Commercial",
            "land": "Land", "industrial": "Industrial",
        }
        for rec in self:
            Sub = self.env["property.sub.project"]
            result = [{"type": label, "count": Sub.search_count([("property_type", "=", key)])}
                      for key, label in types.items()]
            rec.subprojects_by_type = json.dumps(result)

    # ── Subprojects by City ───────────────────────────────────────────────────
    def _compute_subprojects_by_city(self):
        for rec in self:
            subs = self.env["property.sub.project"].search([])
            city_map = {}
            for s in subs:
                city = (s.city_id.name if s.city_id else None) or "Unknown"
                city_map[city] = city_map.get(city, 0) + 1
            result = [{"city": k, "count": v} for k, v in
                      sorted(city_map.items(), key=lambda x: -x[1])[:12]]
            rec.subprojects_by_city = json.dumps(result)

    # ── Units by Status ───────────────────────────────────────────────────────
    def _compute_units_by_status(self):
        stages = {
            "draft": "Draft", "available": "Available", "booked": "Booked",
            "on_lease": "On Rent", "sale": "In Sale", "sold": "Sold",
        }
        for rec in self:
            Prop = self.env["property.details"]
            result = [{"status": label, "count": Prop.search_count([("stage", "=", key)])}
                      for key, label in stages.items()]
            rec.units_by_status = json.dumps(result)

    # ── Monthly Revenue ───────────────────────────────────────────────────────
    def _compute_revenue_by_month(self):
        RentInv   = self.env["rent.invoice"]
        SaleContr = self.env["property.vendor"]
        for rec in self:
            data = []
            for start, end, label in rec._month_range():
                rent = sum(RentInv.search([
                    ("invoice_date", ">=", start.date()),
                    ("invoice_date", "<=", end.date()),
                    ("type", "=", "rent"),
                ]).mapped("rent_amount"))
                sale = sum(SaleContr.search([
                    ("date", ">=", start.date()),
                    ("date", "<=", end.date()),
                    ("stage", "=", "sold"),
                ]).mapped("price"))
                data.append({"month": label, "rent": rent, "sale": sale})
            rec.revenue_by_month = json.dumps(data)

    # ── Rent vs Sale Revenue ──────────────────────────────────────────────────
    def _compute_rent_vs_sale_revenue(self):
        for rec in self:
            rec.rent_vs_sale_revenue = json.dumps([
                {"label": "Rent Revenue", "value": rec.total_rent_revenue},
                {"label": "Sale Revenue", "value": rec.total_sale_revenue},
            ])

    # ── Top Subprojects (by unit count + occupancy) ───────────────────────────
    def _compute_top_subprojects(self):
        for rec in self:
            subs = self.env["property.sub.project"].search([])
            result = []
            Prop = self.env["property.details"]
            Bed  = self.env["property.bed"]
            for s in subs:
                total   = Prop.search_count([("subproject_id", "=", s.id)])
                avail   = Prop.search_count([("subproject_id", "=", s.id), ("stage", "=", "available")])
                rented  = Prop.search_count([("subproject_id", "=", s.id), ("stage", "=", "on_lease")])
                booked  = Prop.search_count([("subproject_id", "=", s.id), ("stage", "=", "booked")])

                # Count beds via property.bed
                unit_ids = Prop.search([("subproject_id", "=", s.id)]).ids
                t_beds   = Bed.search_count([("property_id", "in", unit_ids)])
                a_beds   = Bed.search_count([("property_id", "in", unit_ids), ("state", "=", "available")])

                if total:
                    result.append({
                        "id":        s.id,
                        "name":      s.name,
                        "project":   s.property_project_id.name or "",
                        "city":      (s.city_id.name if s.city_id else "—"),
                        "type":      s.property_type or "—",
                        "sale_lease": s.sale_lease or "—",
                        "total":     total,
                        "available": avail,
                        "rented":    rented,
                        "booked":    booked,
                        "sold":      total - avail - rented - booked,
                        "total_beds": t_beds,
                        "avail_beds": a_beds,
                        "rate":      round(rented / total * 100, 1) if total else 0,
                    })
            rec.top_subprojects = json.dumps(
                sorted(result, key=lambda x: -x["total"])[:15]
            )

    # ── Contract Status ───────────────────────────────────────────────────────
    def _compute_contract_status_data(self):
        Rent = self.env["tenancy.details"]
        statuses = {
            "new_contract":    "Draft",
            "running_contract": "Running",
            "cancel_contract": "Cancelled",
            "close_contract":  "Closed",
            "expire_contract": "Expired",
        }
        for rec in self:
            result = [{"status": label, "count": Rent.search_count([("contract_type", "=", key)])}
                      for key, label in statuses.items()]
            rec.contract_status_data = json.dumps(result)

    # ── Maintenance by Month ──────────────────────────────────────────────────
    def _compute_maintenance_by_month(self):
        Maint = self.env.get("maintenance.request")
        for rec in self:
            data = []
            for start, end, label in rec._month_range():
                cost = 0
                if Maint is not None:
                    cost = Maint.search_count([
                        ("create_date", ">=", start),
                        ("create_date", "<=", end),
                    ])
                data.append({"month": label, "requests": cost})
            rec.maintenance_by_month = json.dumps(data)

    # ── Payment Status Breakdown ──────────────────────────────────────────────
    def _compute_payment_status(self):
        RentInv = self.env["rent.invoice"]
        for rec in self:
            date_dom = rec._date_domain("invoice_date")
            all_inv  = RentInv.search(date_dom)
            states   = {"paid": 0, "not_paid": 0, "partial": 0, "in_payment": 0}
            for inv in all_inv:
                ps = inv.payment_state or "not_paid"
                if ps in states:
                    states[ps] += inv.rent_amount
                else:
                    states["not_paid"] += inv.rent_amount
            rec.payment_status_breakdown = json.dumps([
                {"label": "Paid",       "value": states["paid"]},
                {"label": "Not Paid",   "value": states["not_paid"]},
                {"label": "Partial",    "value": states["partial"]},
                {"label": "In Payment", "value": states["in_payment"]},
            ])

    # ── Occupancy by City (unit-level) ────────────────────────────────────────
    def _compute_occupancy_by_city(self):
        for rec in self:
            subs = self.env["property.sub.project"].search([])
            Prop = self.env["property.details"]
            city_data = {}
            for s in subs:
                city = (s.city_id.name if s.city_id else "Unknown")
                total  = Prop.search_count([("subproject_id", "=", s.id)])
                rented = Prop.search_count([("subproject_id", "=", s.id), ("stage", "=", "on_lease")])
                avail  = Prop.search_count([("subproject_id", "=", s.id), ("stage", "=", "available")])
                if city not in city_data:
                    city_data[city] = {"total": 0, "rented": 0, "available": 0}
                city_data[city]["total"]     += total
                city_data[city]["rented"]    += rented
                city_data[city]["available"] += avail
            result = []
            for city, d in city_data.items():
                result.append({
                    "city":      city,
                    "total":     d["total"],
                    "rented":    d["rented"],
                    "available": d["available"],
                    "rate": round(d["rented"] / d["total"] * 100, 1) if d["total"] else 0,
                })
            rec.occupancy_by_city = json.dumps(sorted(result, key=lambda x: -x["total"])[:10])

    # ── Map — one pin per SubProject ──────────────────────────────────────────
    def _compute_map_subprojects(self):
        for rec in self:
            subs = self.env["property.sub.project"].search([])
            Prop = self.env["property.details"]
            Bed  = self.env["property.bed"]
            features = []
            for s in subs:
                # ── Coordinates: own lat/lon first, then parent project, then city/default
                lat_str = s.latitude   # related from property_project_id.latitude
                lon_str = s.longitude
                city_name = (s.city_id.name if s.city_id else "") or ""
                lat, lon, is_exact = _resolve_lat_lon(lat_str, lon_str, city_name)

                # Unit stats
                total   = Prop.search_count([("subproject_id", "=", s.id)])
                avail   = Prop.search_count([("subproject_id", "=", s.id), ("stage", "=", "available")])
                rented  = Prop.search_count([("subproject_id", "=", s.id), ("stage", "=", "on_lease")])
                booked  = Prop.search_count([("subproject_id", "=", s.id), ("stage", "=", "booked")])

                # Bed stats
                unit_ids = Prop.search([("subproject_id", "=", s.id)]).ids
                t_beds   = Bed.search_count([("property_id", "in", unit_ids)])
                a_beds   = Bed.search_count([("property_id", "in", unit_ids), ("state", "=", "available")])

                # Pin color driven by availability ratio
                if total == 0:
                    color = STATUS_COLORS["draft"]
                elif avail == 0:
                    color = STATUS_COLORS["on_lease"]
                elif avail == total:
                    color = STATUS_COLORS["available"]
                else:
                    color = STATUS_COLORS["booked"]

                features.append({
                    "id":         s.id,
                    "name":       s.name,
                    "project":    s.property_project_id.name or "",
                    "city":       city_name or "—",
                    "type":       s.property_type or "—",
                    "sale_lease": s.sale_lease or "—",
                    "lat":        lat,
                    "lon":        lon,
                    "is_exact":   is_exact,
                    "total":      total,
                    "available":  avail,
                    "rented":     rented,
                    "booked":     booked,
                    "sold":       total - avail - rented - booked,
                    "total_beds": t_beds,
                    "avail_beds": a_beds,
                    "occ_rate":   round(rented / total * 100, 1) if total else 0,
                    "color":      color,
                })
            rec.map_subprojects = json.dumps(features)

    # ── Monthly New Contracts ─────────────────────────────────────────────────
    def _compute_monthly_new_contracts(self):
        Rent = self.env["tenancy.details"]
        Sale = self.env["property.vendor"]
        for rec in self:
            data = []
            for start, end, label in rec._month_range():
                rent = Rent.search_count([
                    ("create_date", ">=", start),
                    ("create_date", "<=", end),
                ])
                sale = Sale.search_count([
                    ("create_date", ">=", start),
                    ("create_date", "<=", end),
                ])
                data.append({"month": label, "rent": rent, "sale": sale})
            rec.monthly_new_contracts = json.dumps(data)

    # ── Bed Availability by Subproject (top 10 with beds) ────────────────────
    def _compute_bed_availability_by_sub(self):
        for rec in self:
            subs = self.env["property.sub.project"].search([])
            Prop = self.env["property.details"]
            Bed  = self.env["property.bed"]
            result = []
            for s in subs:
                unit_ids = Prop.search([("subproject_id", "=", s.id)]).ids
                if not unit_ids:
                    continue
                t_beds = Bed.search_count([("property_id", "in", unit_ids)])
                if not t_beds:
                    continue
                a_beds = Bed.search_count([("property_id", "in", unit_ids), ("state", "=", "available")])
                result.append({
                    "name":       s.name,
                    "total_beds": t_beds,
                    "avail_beds": a_beds,
                    "occ_beds":   t_beds - a_beds,
                    "rate":       round((t_beds - a_beds) / t_beds * 100, 1),
                })
            rec.bed_availability_by_sub = json.dumps(
                sorted(result, key=lambda x: -x["total_beds"])[:10]
            )

    # ── Top Landlords ─────────────────────────────────────────────────────────
    def _compute_top_landlords(self):
        for rec in self:
            landlords = self.env["res.partner"].search([("user_type", "=", "landlord")])
            result = []
            Prop = self.env["property.details"]
            for ll in landlords:
                props  = Prop.search_count([("landlord_id", "=", ll.id)])
                rented = Prop.search_count([("landlord_id", "=", ll.id), ("stage", "=", "on_lease")])
                subs   = self.env["property.sub.project"].search_count([
                    ("landlord_id", "=", ll.id)
                ])
                if props:
                    result.append({
                        "name":        ll.name,
                        "properties":  props,
                        "rented":      rented,
                        "subprojects": subs,
                    })
            rec.top_landlords = json.dumps(sorted(result, key=lambda x: -x["properties"])[:10])
