# -*- coding: utf-8 -*-
# Copyright 2026-Baramej®.
# Part of Baramej®. See LICENSE file for full copyright and licensing details.
import datetime
import logging
import re
from datetime import timedelta

from dateutil.relativedelta import relativedelta
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT

_logger = logging.getLogger(__name__)


class TenancyDetails(models.Model):
    """Property Rent Contract"""

    _name = "tenancy.details"
    _description = "Information Related To customer Tenancy while Creating Contract"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = "tenancy_seq"

    # Tenancy Details
    tenancy_seq = fields.Char(
        string="Sequence",
        required=True,
        readonly=True,
        copy=False,
        default=lambda self: _("New"),
    )
    close_contract_state = fields.Boolean(string="Contract State")
    active_contract_state = fields.Boolean(string="Active State")
    contract_type = fields.Selection(
        [
            ("new_contract", "Draft"),
            ("pending_approval", "Pending Approval"),
            ("approved", "Approved"),
            ("running_contract", "Running"),
            ("cancel_contract", "Cancel"),
            ("close_contract", "Close"),
            ("expire_contract", "Expire"),
        ],
        string="Contract Type",
        tracking=True,
    )
    days_left = fields.Integer(string="Days Left", compute="compute_days_left")
    responsible_id = fields.Many2one(
        "res.users",
        default=lambda self: self.env.user and self.env.user.id or False,
        string="Responsible",
    )

    # Company & Currency
    company_id = fields.Many2one(
        "res.company", string="Company", default=lambda self: self.env.company
    )
    currency_id = fields.Many2one(
        "res.currency", related="company_id.currency_id", string="Currency"
    )

    # Property Information
    property_id = fields.Many2one(
        "property.details", string="Property", domain=[("stage", "=", "available")]
    )
    property_type = fields.Selection(
        related="property_id.type", string="Type ", store=True
    )
    property_subtype_id = fields.Many2one(
        related="property_id.property_subtype_id", string="Sub Type", store=True
    )
    property_project_id = fields.Many2one(
        related="property_id.property_project_id", string="Project", store=True
    )
    subproject_id = fields.Many2one(
        related="property_id.subproject_id", string="Sub Project", store=True
    )
    region_id = fields.Many2one(related="property_id.region_id")
    street = fields.Char(related="property_id.street")
    street2 = fields.Char(related="property_id.street2")
    city_id = fields.Many2one(related="property_id.city_id")
    zip = fields.Char(related="property_id.zip")
    state_id = fields.Many2one(related="property_id.state_id")
    country_id = fields.Many2one(related="property_id.country_id")

    # Landlord
    property_landlord_id = fields.Many2one(
        related="property_id.landlord_id", string="Landlord", store=True
    )
    landlord_phone = fields.Char(
        related="property_landlord_id.phone", string="Landlord Phone"
    )
    landlord_email = fields.Char(
        related="property_landlord_id.email", string="Landlord Email"
    )

    # Customer / Tenant
    tenancy_id = fields.Many2one(
        "res.partner", string="Tenant", domain=[("user_type", "=", "customer")]
    )
    customer_phone = fields.Char(related="tenancy_id.phone", string="Customer Phone")
    customer_email = fields.Char(related="tenancy_id.email", string="Customer Email")

    # Extend Contract Ref.
    extended = fields.Boolean(string="Is Extended")
    is_extended = fields.Boolean(string="Is Extended Contract")
    extend_from = fields.Char(string="Extend From.")
    extend_ref = fields.Char(string="Extend Ref.")
    new_contract_id = fields.Many2one("tenancy.details", string="Contract Ref")

    # Contract & Payment Details
    payment_term = fields.Selection(
        [
            ("monthly", "Monthly"),
            ("full_payment", "Full Payment"),
            ("quarterly", "Quarterly"),
            ("half_year", "Half Year"),
            ("year", "Yearly"),
            ("daily", "Daily"),
            ("bi_monthly", "Bi-Monthly"),
        ],
        string="Payment Term",
    )
    duration_ids = fields.Many2many(
        "contract.duration", string="Durations", compute="_compute_durations_ids"
    )
    duration_id = fields.Many2one("contract.duration", string="Duration")
    month = fields.Integer(related="duration_id.month", string="Month")
    total_rent = fields.Monetary(string="Rent")
    final_rent_unit = fields.Selection(
        [("Day", "Day"), ("Month", "Month"), ("Year", "Year")], string="Rent Unit "
    )
    rent_unit = fields.Selection(
        [("Day", "Day"), ("Month", "Month"), ("Year", "Year")],
        compute="_compute_rent_unit",
    )
    start_date = fields.Date(string="Start Date", default=fields.Date.today())
    end_date = fields.Date(
        string="End Date", compute="_compute_end_date", search="_search_end_date"
    )
    invoice_start_date = fields.Date(
        string="Invoice Start From", default=fields.Date.today()
    )
    last_invoice_payment_date = fields.Date(string="Last Invoice Payment Date")
    rent_invoice_ids = fields.One2many("rent.invoice", "tenancy_id", string="Invoices")
    total_area = fields.Float(related="property_id.total_area")
    usable_area = fields.Float(related="property_id.usable_area")
    measure_unit = fields.Selection(related="property_id.measure_unit")
    type = fields.Selection(
        [
            ("automatic", "Auto Installment"),
            ("manual", "Manual Installment (List out all rent installment)"),
        ],
        default="automatic",
    )
    is_any_deposit = fields.Boolean(string="Deposit")
    deposit_amount = fields.Monetary(string="Security Deposit")
    terminate_date = fields.Date(string="Terminate Date")

    # Utility Service
    is_extra_service = fields.Boolean(
        related="property_id.is_extra_service", string="Any Extra Services"
    )
    extra_services_ids = fields.One2many(
        "tenancy.service.line", "tenancy_id", string="Services"
    )
    extra_service_invoice = fields.Selection(
        [("merge", "Merge With Installment"), ("separate", "Separate")], default="merge"
    )

    # Maintenance
    is_maintenance_service = fields.Boolean(
        related="property_id.is_maintenance_service", string="Is Any Maintenance"
    )
    maintenance_rent_type = fields.Selection(
        related="property_id.maintenance_rent_type", string="Maintenance Type"
    )
    total_maintenance = fields.Monetary(
        related="property_id.total_maintenance", string="Total Maintenance"
    )
    maintenance_type = fields.Selection(related="property_id.maintenance_type")
    per_area_maintenance = fields.Monetary(related="property_id.per_area_maintenance")
    maintenance_service_invoice = fields.Selection(
        [("merge", "Merge With Installment"), ("separate", "Separate")], default="merge"
    )

    # Broker details
    is_any_broker = fields.Boolean(string="Any Broker")
    broker_invoice_state = fields.Boolean(string="Broker invoice State")
    broker_invoice_id = fields.Many2one("account.move", string="Bill ")
    broker_id = fields.Many2one(
        "res.partner", string="Broker", domain=[("user_type", "=", "broker")]
    )
    commission = fields.Monetary(
        string="Commission ", compute="_compute_broker_commission"
    )
    rent_type = fields.Selection(
        [("once", "One Month"), ("e_rent", "All Month")], string="Brokerage Type"
    )
    commission_type = fields.Selection(
        [("f", "Fix"), ("p", "Percentage")], string="Commission Type"
    )
    broker_commission = fields.Monetary(string="Commission")
    broker_commission_percentage = fields.Float(string="Percentage")
    commission_from = fields.Selection(
        [
            ("customer", "Customer"),
            (
                "landlord",
                "Landlord",
            ),
        ],
        string="Commission From",
    )

    # Instalment Item
    installment_item_id = fields.Many2one(
        "product.product",
        string="Installment Item",
        default=lambda self: self.env.ref(
            "rental_management.property_product_1", raise_if_not_found=False
        ),
    )
    deposit_item_id = fields.Many2one(
        "product.product",
        string="Deposit Item",
        default=lambda self: self.env.ref(
            "rental_management.property_product_2", raise_if_not_found=False
        ),
    )
    broker_item_id = fields.Many2one(
        "product.product",
        string="Broker Item",
        default=lambda self: self.env.ref(
            "rental_management.property_product_3", raise_if_not_found=False
        ),
    )
    maintenance_item_id = fields.Many2one(
        "product.product",
        string="Maintenance Item",
        default=lambda self: self.env.ref(
            "rental_management.property_product_4", raise_if_not_found=False
        ),
    )

    # Taxes
    instalment_tax = fields.Boolean(string="Taxes on Installment ?")
    deposit_tax = fields.Boolean(string="Taxes on Deposit ?")
    service_tax = fields.Boolean(string="Taxes on Services ?")
    tax_ids = fields.Many2many("account.tax", string="Taxes")

    # Agreement
    agreement_template_id = fields.Many2one(
        "agreement.template", string="Agreement Template"
    )
    agreement = fields.Html(string="Agreement")
    contract_agreement = fields.Binary(string="Contract Agreement")
    file_name = fields.Char(string="File Name", translate=True)

    # Terms  & Conditions
    term_condition = fields.Html(string="Term and Condition")

    # Tenancy Calculation
    total_tenancy = fields.Monetary(
        string="Untaxed Amount", compute="_compute_tenancy_calculation"
    )
    tax_amount = fields.Monetary(
        string="Tax Amount", compute="_compute_tenancy_calculation"
    )
    total_amount = fields.Monetary(
        string="Total Amount", compute="_compute_tenancy_calculation"
    )
    paid_tenancy = fields.Monetary(
        string="Paid Amount", compute="_compute_tenancy_calculation"
    )
    remain_tenancy = fields.Monetary(
        string="Remaining Amount", compute="_compute_tenancy_calculation"
    )

    # Count
    invoice_count = fields.Integer(
        string="Invoice Count", compute="_compute_invoice_count"
    )
    total_bill_amount = fields.Monetary(
        string="Total Bill", compute="_compute_total_bill_amount"
    )
    paid_bill_amount = fields.Monetary(
        string="Paid Bill", compute="_compute_total_bill_amount"
    )
    remaining_bill_amount = fields.Monetary(
        string="Remaining Bill", compute="_compute_total_bill_amount"
    )
    maintenance_request_count = fields.Integer(
        string="Maintenance Request Count", compute="_compute_maintenance_request_count"
    )
    rent_bill_ids = fields.One2many("rent.bill", "tenancy_id")

    # Profit and Loss (P/L)
    total_invoiced = fields.Monetary(
        string="Total Invoice", compute="_compute_total_amount"
    )
    total_bills = fields.Monetary(string="Total Bills", compute="_compute_total_amount")
    margin = fields.Monetary(string="Margin", compute="_compute_total_amount")
    invoice_paid_amount = fields.Monetary(
        string="Invoice", compute="_compute_total_amount"
    )
    bill_paid_amount = fields.Monetary(string="Bill", compute="_compute_total_amount")
    invoice_residual = fields.Monetary(
        string="Invoice Residual", compute="_compute_total_amount"
    )
    bill_residual = fields.Monetary(
        string="Bill Residual", compute="_compute_total_amount"
    )
    actual_margin = fields.Monetary(
        string="Actual Margin", compute="_compute_total_amount"
    )
    margin_percentage = fields.Float(
        string="Margin Percentage", compute="_compute_total_amount"
    )

    # Contract Time Period
    is_contract_period_available = fields.Boolean(
        compute="_compute_is_contract_period_available"
    )

    # Duration Type
    duration_type = fields.Selection(
        [("by_duration", "By Duration"), ("by_date", "By Date")], default="by_duration"
    )
    duration_end_date = fields.Date()

    # Total Days
    total_days = fields.Integer(compute="_compute_total_days")

    # Added Service
    is_added_services = fields.Boolean(string="Extra Services ?")
    added_service_ids = fields.One2many(
        comodel_name="contract.extra.service.line", inverse_name="contract_id"
    )
    added_service_invoice = fields.Selection(
        [("merge", "Merge With Installment"), ("separate", "Separate")], default="merge"
    )

    # Penalty Details
    is_penalty_applied = fields.Boolean(string="Is Any Penalty?")
    penalty_days_after_due = fields.Integer(string="Apply Penalty After (Days)")
    penalty_percentage = fields.Integer(string="Percentage ")
    penalty_invoice_ids = fields.One2many(
        "penalty.invoice", "rent_contract_id", string="Penalty Invoices"
    )

    # Expiry Reminder Fields
    is_expiry_reminder_sent = fields.Boolean(
        string="Expiry Reminder Sent",
        default=False,
        copy=False,
        help="Technical field to track if 90-day expiry reminder has been sent",
    )
    expiry_reminder_date = fields.Date(
        string="Reminder Date",
        readonly=True,
        copy=False,
        help="Date when the 90-day expiry reminder was sent",
    )

    termination_type = fields.Selection(
        [("normal", "Normal Expiry"), ("early", "Early Termination"), ("renewal", "Non-Renewal")],
        string="Termination Type", default="normal", copy=False,
    )
    move_out_date = fields.Date(string="Move Out Date", copy=False)
    key_handover_date = fields.Date(string="Date of Key Handover", copy=False)

    final_maintenance_line_ids = fields.One2many(
        "tenancy.final.maintenance.line", "tenancy_id", string="Maintenance / Repair Charges"
    )
    final_utility_line_ids = fields.One2many(
        "tenancy.final.utility.line", "tenancy_id", string="Utility Charges"
    )
    final_maintenance_amount = fields.Monetary(
        string="Total Maintenance Amount", compute="_compute_final_charge_totals", store=True
    )
    final_utility_amount = fields.Monetary(
        string="Total Utility Amount", compute="_compute_final_charge_totals", store=True
    )

    @api.depends("final_maintenance_line_ids.amount", "final_utility_line_ids.amount")
    def _compute_final_charge_totals(self):
        for rec in self:
            rec.final_maintenance_amount = sum(rec.final_maintenance_line_ids.mapped("amount"))
            rec.final_utility_amount = sum(rec.final_utility_line_ids.mapped("amount"))

    # ── Rent settlement, derived directly from rent_invoice_ids ──
    rent_paid_upto = fields.Date(
        string="Rent Paid Upto", compute="_compute_rent_settlement"
    )
    rent_due_amount = fields.Monetary(
        string="Rent Due", compute="_compute_rent_settlement"
    )

    @api.depends("rent_invoice_ids.rent_invoice_id", "rent_invoice_ids.rent_invoice_id.payment_state")
    def _compute_rent_settlement(self):
        for rec in self:
            rent_lines = rec.rent_invoice_ids.filtered(
                lambda l: l.type in ("rent", "full_rent") and l.rent_invoice_id
            )
            paid_lines = rent_lines.filtered(
                lambda l: l.rent_invoice_id.payment_state == "paid"
            ).sorted(key=lambda l: l.invoice_date or fields.Date.today())
            rec.rent_paid_upto = paid_lines[-1].invoice_date if paid_lines else False

            unpaid_lines = rent_lines.filtered(
                lambda l: l.rent_invoice_id.payment_state not in ("paid", "reversed")
            )
            rec.rent_due_amount = sum(unpaid_lines.mapped("rent_invoice_id.amount_residual"))

    payment_due_to_tenant = fields.Monetary(
        string="Payment Due to Tenant", compute="_compute_payment_due_to_tenant"
    )

    @api.depends(
        "deposit_amount", "final_maintenance_amount", "final_utility_amount", "rent_due_amount"
    )
    def _compute_payment_due_to_tenant(self):
        for rec in self:
            rec.payment_due_to_tenant = (
                    rec.deposit_amount
                    - rec.final_maintenance_amount
                    - rec.final_utility_amount
                    - rec.rent_due_amount
            )

    def action_print_final_statement(self):
        self.ensure_one()
        return self.env.ref("rental_management.action_report_final_statement").report_action(self)

    # Create, Write, Name get...
    @api.model_create_multi
    def create(self, vals_list):
        """Contract create method"""
        for vals in vals_list:
            if vals.get("tenancy_seq", "New") == "New":
                vals["tenancy_seq"] = (
                    self.env["ir.sequence"].next_by_code("tenancy.details") or "New"
                )
        res = super(TenancyDetails, self).create(vals_list)
        return res

    @api.constrains("start_date", "duration_type", "duration_end_date")
    def _check_end_date(self):
        """Check end date is always greater than start date"""
        for rec in self:
            if (
                rec.duration_type == "by_date"
                and rec.start_date
                and rec.duration_end_date
                and rec.duration_end_date < rec.start_date
            ):
                raise ValidationError(_("End date should be greater than start date"))

    def unlink(self):
        """Set property stage to draft when contract is deleted"""
        for rec in self:
            if rec.contract_type == "new_contract":
                rec.property_id.stage = "draft"
        return super(TenancyDetails, self).unlink()

    # On delete
    @api.ondelete(at_uninstall=False)
    def _unlink_tenant_rent_contract(self):
        """Prevent contract to unlink when contract in running_contract or expire_contract"""
        for rec in self:
            if rec.contract_type in ["running_contract", "expire_contract"]:
                raise ValidationError(
                    _(
                        "To delete a rent contract, you must cancel or close the contract."
                    )
                )

    def write(self, vals):
        """Write Method"""
        if "payment_term" in vals:
            valid_payment_terms = {
                "Day": [
                    "Monthly",
                    "Bi-Monthly",
                    "Quarterly",
                    "Half Year",
                    "Year",
                    "Daily",
                ],
                "Month": ["Monthly", "Bi-Monthly", "Quarterly", "Half Year"],
                "Year": ["Year"],
            }
            rent_unit = self.rent_unit
            payment_term = vals.get("payment_term")
            if rent_unit in valid_payment_terms and payment_term not in [
                term.lower().replace(" ", "_")
                for term in valid_payment_terms[rent_unit]
            ]:
                raise ValidationError(
                    _(
                        f"For Rent Unit '{rent_unit}', "
                        f"Payment Term should be one "
                        f"of {', '.join(valid_payment_terms[rent_unit])}"
                    )
                )
        return super().write(vals)

    # Compute
    # Contract End Date
    @api.depends(
        "start_date",
        "month",
        "rent_unit",
        "payment_term",
        "duration_type",
        "duration_end_date",
    )
    def _compute_end_date(self):
        """Compute end date"""
        for rec in self:
            end_date = None
            if rec.duration_type == "by_duration" and rec.start_date:
                if rec.rent_unit == "Day":
                    delta = relativedelta(days=rec.month)
                elif rec.rent_unit == "Year" or rec.payment_term == "year":
                    delta = relativedelta(years=rec.month)
                else:
                    delta = relativedelta(months=rec.month)
                end_date = rec.start_date + delta - relativedelta(days=1)
            if rec.duration_type == "by_date" and rec.duration_end_date:
                end_date = rec.duration_end_date
            rec.end_date = end_date

    # Search End Date
    def _search_end_date(self, operator, value):
        """End Date search for compute method"""
        contracts = []
        contracts_ids = self.env["tenancy.details"].search([])
        for rec in contracts_ids:
            end_date = rec.end_date
            if value and end_date:
                if isinstance(value, str):
                    end_date = datetime.datetime.strftime(end_date, DATE_FORMAT)
                if operator == "=" and end_date == value:
                    contracts.append(rec.id)
                elif operator == ">=" and end_date >= value:
                    contracts.append(rec.id)
                elif operator == "<=" and end_date <= value:
                    contracts.append(rec.id)
                elif operator == ">" and end_date > value:
                    contracts.append(rec.id)
                elif operator == "<" and end_date < value:
                    contracts.append(rec.id)
                elif operator == "!=" and end_date != value:
                    contracts.append(rec.id)
        return [("id", "in", contracts)]

    # Broker Commission
    @api.depends(
        "is_any_broker",
        "month",
        "broker_commission",
        "broker_commission_percentage",
        "commission_type",
        "rent_type",
        "total_rent",
    )
    def _compute_broker_commission(self):
        """Compute broker commission"""
        for rec in self:
            commission = 0.0
            total_commission = 0.0
            if rec.is_any_broker:
                if rec.commission_type == "f":
                    commission = rec.broker_commission
                if rec.commission_type == "p":
                    commission = rec.broker_commission_percentage * rec.total_rent / 100
                if rec.rent_type == "once":
                    total_commission = commission
                if rec.rent_type == "e_rent":
                    total_commission = commission * rec.month
            rec.commission = total_commission

    # Days Left
    @api.depends("start_date", "end_date", "contract_type")
    def compute_days_left(self):
        """Compute days left"""
        for rec in self:
            days_left = 0
            days = 0
            todays_date = fields.Date.today()
            if rec.contract_type == "running_contract" and rec.end_date:
                days = (rec.end_date - todays_date).days
                days_left = days if days > 0 else 0
            rec.days_left = days_left

    @api.depends("start_date", "end_date")
    def _compute_total_days(self):
        """Compute total days"""
        for rec in self:
            total_days = 0
            if rec.start_date and rec.end_date:
                total_days = (rec.end_date - rec.start_date).days + 1
            rec.total_days = total_days

    # Tenancy Calculation
    @api.depends(
        "rent_invoice_ids", "rent_invoice_ids.rent_invoice_id", "contract_type"
    )
    def _compute_tenancy_calculation(self):
        """Compute tenancy calculation"""
        for rec in self:
            untaxed = 0.0
            tax_amount = 0.0
            paid = 0.0
            for data in rec.rent_invoice_ids:
                if data.rent_invoice_id:
                    # Credit notes (deposit refund on settlement) reduce what
                    # the tenant owes, so they count negatively.
                    sign = -1 if data.rent_invoice_id.move_type == "out_refund" else 1
                    untaxed = untaxed + sign * data.rent_invoice_id.amount_untaxed
                    tax_amount = tax_amount + sign * (
                        data.rent_invoice_id.amount_total
                        - data.rent_invoice_id.amount_untaxed
                    )
                    paid = paid + sign * (
                        data.rent_invoice_id.amount_total
                        - data.rent_invoice_id.amount_residual
                    )
            rec.total_amount = untaxed + tax_amount
            rec.total_tenancy = untaxed
            rec.tax_amount = tax_amount
            rec.paid_tenancy = paid
            if rec.contract_type == "running_contract":
                rec.remain_tenancy = untaxed + tax_amount - paid
            else:
                rec.remain_tenancy = 0.0

    # Count
    @api.depends("rent_invoice_ids")
    def _compute_invoice_count(self):
        """Compute invoice count"""
        for rec in self:
            rec.invoice_count = self.env["rent.invoice"].search_count(
                [("tenancy_id", "in", [rec.id])]
            )

    @api.depends("rent_bill_ids")
    def _compute_total_bill_amount(self):
        """Compute total bill amount"""
        for rec in self:
            bills = self.env["rent.bill"].search([("tenancy_id", "=", rec.id)])
            total = 0.0
            paid = 0.0
            for bill in bills:
                total += bill.amount
                if bill.rent_bill_id.payment_state == "paid":
                    paid = paid + bill.rent_bill_id.amount_total
            rec.total_bill_amount = total
            rec.paid_bill_amount = paid
            rec.remaining_bill_amount = total - paid

    def _compute_maintenance_request_count(self):
        """Comoute maintenance request count"""
        for rec in self:
            request_count = self.env["maintenance.request"].search_count(
                [("rent_contract_id", "in", [rec.id])]
            )
            rec.maintenance_request_count = request_count

    # Profit and Loss (P/L)
    @api.depends("rent_invoice_ids", "rent_bill_ids")
    def _compute_total_amount(self):
        """Compute total amount"""
        for rec in self:
            invoice_amount = 0.0
            invoice_residual = 0.0
            bill_amount = 0.0
            bill_residual = 0.0
            invoices = (
                self.env["account.move"]
                .sudo()
                .search(
                    [
                        ("tenancy_id", "=", rec.id),
                        # ``out_refund`` covers the deposit credit note issued
                        # on settlement; its signed amounts are negative.
                        ("move_type", "in", ("out_invoice", "out_refund")),
                        ("state", "=", "posted"),
                    ]
                )
            )
            for invoice in invoices:
                invoice_amount += invoice.amount_total_signed
                invoice_residual += invoice.amount_residual_signed

            bills = (
                self.env["account.move"]
                .sudo()
                .search(
                    [
                        ("tenancy_id", "=", rec.id),
                        ("move_type", "=", "in_invoice"),
                        ("state", "=", "posted"),
                    ]
                )
            )
            for bill in bills:
                bill_amount += bill.amount_total_signed
                bill_residual += bill.amount_residual_signed

            rec.total_invoiced = invoice_amount
            rec.invoice_residual = invoice_residual
            rec.invoice_paid_amount = invoice_amount - invoice_residual
            rec.total_bills = bill_amount
            rec.bill_residual = bill_residual
            rec.bill_paid_amount = bill_amount - bill_residual
            rec.actual_margin = (
                invoice_amount - invoice_residual - (-(bill_amount - bill_residual))
            )
            rec.margin = invoice_amount - (-bill_amount)
            if rec.total_invoiced != 0:
                rec.margin_percentage = (rec.margin * 100) / rec.total_invoiced
            else:
                rec.margin_percentage = 0

    # Compute Rent Unit
    @api.depends("property_id", "property_id.rent_unit", "final_rent_unit")
    def _compute_rent_unit(self):
        """Compute rent unit for new 'final_rent_unit' field"""
        for rec in self:
            if rec.final_rent_unit:
                rec.rent_unit = rec.final_rent_unit
            else:
                rec.rent_unit = rec.property_id.rent_unit

    @api.depends(
        "property_id",
        "contract_type",
        "start_date",
        "end_date",
        "duration_id",
        "payment_term",
    )
    def _compute_is_contract_period_available(self):
        """Check weather contract period is available or not"""
        for rec in self:
            is_period_available = True
            if rec.start_date and rec.end_date:
                contract = self.env["tenancy.details"].search(
                    [
                        ("start_date", "<=", rec.end_date),
                        ("end_date", ">", rec.start_date),
                        ("property_id", "=", rec.property_id.id),
                        ("contract_type", "=", "running_contract"),
                    ]
                )
                if contract:
                    is_period_available = False
            rec.is_contract_period_available = is_period_available

    @api.depends("payment_term", "rent_unit")
    def _compute_durations_ids(self):
        """Compute Durations as per rent unit"""
        for rec in self:
            domain = []
            duration_record = self.env["contract.duration"].sudo()
            if rec.rent_unit == "Day":
                domain = [("rent_unit", "=", "Day")]
            if rec.rent_unit == "Year":
                domain = [("rent_unit", "=", "Year")]
            if rec.rent_unit == "Month":
                if rec.payment_term == "quarterly":
                    domain = [("month", ">=", 3), ("rent_unit", "=", "Month")]
                elif rec.payment_term == "half_year":
                    domain = [("month", ">=", 6), ("rent_unit", "=", "Month")]
                elif rec.payment_term == "bi_monthly":
                    domain = [("month", ">=", 2), ("rent_unit", "=", "Month")]
                elif rec.payment_term == "year":
                    domain = [("rent_unit", "=", "Year")]
                else:
                    domain = [("month", ">", 0), ("rent_unit", "=", "Month")]
            rec.duration_ids = duration_record.search(domain).mapped("id")

    # Onchange
    @api.onchange("rent_unit")
    def _onchange_rent_unit(self):
        """Change payment term based on rent unit"""
        for rec in self:
            if rec.rent_unit == "Day":
                rec.payment_term = "full_payment"
            elif rec.rent_unit == "Year":
                rec.payment_term = "year"
            else:
                rec.payment_term = False

    @api.onchange("duration_type")
    def _onchange_duration_type(self):
        """Onchange duration type"""
        for rec in self:
            if rec.duration_type == "by_date":
                rec.final_rent_unit = "Day"

    # Button
    # Smart Button
    def action_invoices(self):
        """View contract invoices"""
        return {
            "type": "ir.actions.act_window",
            "name": "Invoice",
            "res_model": "rent.invoice",
            "domain": [("tenancy_id", "=", self.id)],
            "view_mode": "list,form",
            "target": "current",
        }

    def action_bills(self):
        """View contract bills"""
        return {
            "type": "ir.actions.act_window",
            "name": "Bill",
            "res_model": "rent.bill",
            "domain": [("tenancy_id", "=", self.id)],
            "view_mode": "list,form",
            "target": "current",
        }

    def action_maintenance_request(self):
        """View maintenance request"""
        return {
            "type": "ir.actions.act_window",
            "name": "Request",
            "res_model": "maintenance.request",
            "domain": [("rent_contract_id", "=", self.id)],
            "context": {"create": False},
            "view_mode": "kanban,list,form",
            "target": "current",
        }

    #  Close Contract
    def action_close_contract(self):
        """Open close contract wizard with readings and inspection"""
        self.ensure_one()

        if self.contract_type != "running_contract":
            return self._do_close_contract()

        # An outstanding balance no longer blocks closure.  The wizard warns
        # about it and the unpaid invoices stay open so they remain
        # collectible after the contract is closed.
        # Open the close contract wizard instead of closing directly
        return {
            "type": "ir.actions.act_window",
            "name": _("Close Contract - Final Readings & Inspection"),
            "res_model": "close.contract.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "active_id": self.id,
                "active_model": "tenancy.details",
            },
        }

    def _do_close_contract(self, maintenance_lines=None):
        """Internal method to actually perform contract closure

        ``maintenance_lines`` is a list of dicts, one per closing charge
        entered on the close wizard, each shaped as:
            {
                "product_id": int,
                "description": str or None,
                "amount": float,
            }
        All lines are merged into a single invoice, and their sum is what
        gets deducted from the security deposit before it is credited back.
        """
        self.ensure_one()
        maintenance_lines = maintenance_lines or []

        # A contract may be closed with money still due.  The unpaid invoices
        # are left posted and open so they stay collectible; record the
        # outstanding balance in the chatter for audit purposes.
        outstanding = self.remain_tenancy
        self.close_contract_state = True
        self.property_id.write({"stage": "available"})
        self.contract_type = "close_contract"
        self.terminate_date = fields.Date.today()
        self._process_close_settlement(maintenance_lines=maintenance_lines)
        if outstanding > 0:
            self.message_post(
                body=_(
                    "Contract closed with an outstanding balance of "
                    "%(amount)s. The unpaid invoices remain open and "
                    "collectible.",
                    amount=self.currency_id.format(outstanding)
                    if self.currency_id
                    else outstanding,
                )
            )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "success",
                "title": _("Contract Closed"),
                "message": _("The contract has been closed successfully."),
                "sticky": False,
                "next": {
                    "type": "ir.actions.act_window_close",
                },
            },
        }

    # Closing Settlement
    def _get_deposit_invoice(self):
        """Posted invoice holding the security deposit of this contract"""
        self.ensure_one()
        return (
            self.env["account.move"]
            .sudo()
            .search(
                [
                    ("tenancy_id", "=", self.id),
                    ("move_type", "=", "out_invoice"),
                    ("is_deposit_invoice", "=", True),
                    ("state", "=", "posted"),
                ],
                order="id desc",
                limit=1,
            )
        )

    def _get_settlement_record(self):
        """Settlement already recorded for this contract, if any"""
        self.ensure_one()
        return (
            self.env["rent.invoice"]
            .sudo()
            .search(
                [("tenancy_id", "=", self.id), ("type", "=", "settlement")], limit=1
            )
        )

    def _process_close_settlement(self, maintenance_lines=None):
        """Settle the contract on closure.

        Invoices maintenance/repair charges and utility charges as two
        separate invoices (each independent of the deposit), and separately
        credits back the full security deposit.  The credit note is left
        as an open credit on the tenant's account: unpaid rent invoices
        stay untouched and the refund is registered manually.
        """
        self.ensure_one()
        if self._get_settlement_record():
            return self.env["rent.invoice"]

        maintenance_lines = maintenance_lines or []
        repair_lines = [l for l in maintenance_lines if l.get("charge_type") != "utility"]
        utility_lines = [l for l in maintenance_lines if l.get("charge_type") == "utility"]

        repair_amount = sum(line.get("amount", 0.0) for line in repair_lines)
        utility_amount = sum(line.get("amount", 0.0) for line in utility_lines)

        maintenance_invoice_id = self.env["account.move"]
        if repair_lines and repair_amount > 0:
            maintenance_invoice_id = self._create_closing_maintenance_invoice(
                repair_lines, invoice_type="maintenance"
            )

        utility_invoice_id = self.env["account.move"]
        if utility_lines and utility_amount > 0:
            utility_invoice_id = self._create_closing_maintenance_invoice(
                utility_lines, invoice_type="utility"
            )

        deposit_invoice_id = self._get_deposit_invoice()
        if not deposit_invoice_id:
            if maintenance_invoice_id or utility_invoice_id:
                self.message_post(
                    body=_(
                        "Closing maintenance of %(maint)s and utility charges of "
                        "%(util)s invoiced. No posted security deposit invoice was "
                        "found for this contract, so no deposit credit note was created.",
                        maint=self.currency_id.format(repair_amount),
                        util=self.currency_id.format(utility_amount),
                    )
                )
            return self.env["rent.invoice"]

        # Refund the full deposit, independent of any maintenance/utility charge.
        deposit_amount = deposit_invoice_id.amount_total
        credit_note_id = self.env["account.move"]
        if self.currency_id.compare_amounts(deposit_amount, 0.0) > 0:
            credit_note_id = self._create_deposit_credit_note(
                deposit_invoice_id, deposit_amount
            )

        settlement_id = (
            self.env["rent.invoice"]
            .sudo()
            .create(
                {
                    "tenancy_id": self.id,
                    "type": "settlement",
                    "invoice_date": fields.Date.today(),
                    "description": _(
                        "Settlement of %(property)s : deposit refund %(deposit)s",
                        property=self.property_id.name,
                        deposit=self.currency_id.format(deposit_amount),
                    ),
                    "amount": deposit_amount,
                    "rent_invoice_id": credit_note_id.id,
                }
            )
        )
        self.message_post(
            body=_(
                "Contract settled: security deposit %(deposit)s refunded in full. "
                "Maintenance of %(maintenance)s and utility charges of %(utility)s "
                "invoiced separately.",
                deposit=self.currency_id.format(deposit_amount),
                maintenance=self.currency_id.format(repair_amount),
                utility=self.currency_id.format(utility_amount),
            )
        )
        return settlement_id

    def _create_closing_maintenance_invoice(self, lines, invoice_type="maintenance"):
        """Invoice a group of closing charges (maintenance/repair OR utility).

        ``lines`` is a list of dicts:
            {"product_id": int, "description": str or None, "amount": float}
        All are merged into one invoice per ``invoice_type``, one line each.
        No tax is added on top of any line — this keeps the deposit
        deduction exact.
        """
        self.ensure_one()
        invoice_lines = []
        for line in lines:
            amount = line.get("amount") or 0.0
            if amount <= 0:
                continue
            product = (
                self.env["product.product"].browse(line.get("product_id"))
                if line.get("product_id")
                else self.maintenance_item_id
            )
            default_desc = (
                _("Closing utility charge of %(property)s", property=self.property_id.name)
                if invoice_type == "utility"
                else _("Closing maintenance of %(property)s", property=self.property_id.name)
            )
            description = line.get("description") or default_desc
            invoice_lines.append(
                (
                    0,
                    0,
                    {
                        "product_id": product.id,
                        "name": description,
                        "quantity": 1,
                        "price_unit": amount,
                        "tax_ids": False,
                    },
                )
            )

        if not invoice_lines:
            return self.env["account.move"]

        invoice_post_type = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("rental_management.invoice_post_type")
        )
        invoice_id = (
            self.env["account.move"]
            .sudo()
            .create(
                {
                    "partner_id": self.tenancy_id.id,
                    "move_type": "out_invoice",
                    "invoice_date": fields.Date.today(),
                    "tenancy_id": self.id,
                    "invoice_line_ids": invoice_lines,
                }
            )
        )
        if invoice_post_type == "automatically":
            invoice_id.action_post()

        rent_invoice_desc = (
            _("Closing utility charges of %(property)s", property=self.property_id.name)
            if invoice_type == "utility"
            else _("Closing maintenance of %(property)s", property=self.property_id.name)
        )
        self.env["rent.invoice"].sudo().create(
            {
                "tenancy_id": self.id,
                "type": invoice_type,
                "invoice_date": fields.Date.today(),
                "description": rent_invoice_desc,
                "amount": invoice_id.amount_total,
                "rent_invoice_id": invoice_id.id,
            }
        )
        return invoice_id

    def _create_deposit_credit_note(self, deposit_invoice_id, amount):
        """Credit note refunding what is left of the security deposit"""
        self.ensure_one()
        invoice_post_type = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("rental_management.invoice_post_type")
        )
        credit_note_id = (
            self.env["account.move"]
            .sudo()
            .create(
                {
                    "partner_id": self.tenancy_id.id,
                    "move_type": "out_refund",
                    "invoice_date": fields.Date.today(),
                    "tenancy_id": self.id,
                    "is_deposit_invoice": True,
                    "reversed_entry_id": deposit_invoice_id.id,
                    "ref": deposit_invoice_id.name,
                    "invoice_line_ids": [
                        (
                            0,
                            0,
                            {
                                "product_id": self.deposit_item_id.id,
                                "name": _(
                                    "Security deposit refund of %(property)s",
                                    property=self.property_id.name,
                                ),
                                "quantity": 1,
                                "price_unit": amount,
                                "tax_ids": False,
                            },
                        )
                    ],
                }
            )
        )
        if invoice_post_type == "automatically":
            credit_note_id.action_post()
        return credit_note_id

    # Renew Contract
    def action_renew_contract(self):
        """Open contract wizard for renewal"""
        self.ensure_one()
        if self.contract_type != "running_contract":
            message = {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "type": "info",
                    "title": (_("User Error !")),
                    "message": (_("Only running contracts can be renewed.")),
                    "next": {"type": "ir.actions.act_window_close"},
                    "sticky": False,
                },
            }
            return message

        return {
            "type": "ir.actions.act_window",
            "name": "Renew Contract",
            "res_model": "contract.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "active_id": self.id,
                "active_model": "tenancy.details",
            },
        }

    def get_payment_term_qty(self):
        """Get qty bases on payment term"""
        payment_term_qty = {
            "half_year": 6,
            "quarterly": 3,
            "bi_monthly": 2,
            "monthly": 1,
            "year": 1,
            "daily": 1,
        }
        return payment_term_qty.get(self.payment_term)

    # Deposit Invoice
    def _create_deposit_invoice(self):
        """Create a standalone invoice for the security deposit.

        The deposit is always billed on its own invoice, never merged with
        the first rent installment, so it can be tracked, paid and refunded
        independently of the rent.
        """
        self.ensure_one()
        if not self.is_any_deposit or not self.deposit_amount:
            return self.env["account.move"]
        invoice_post_type = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("rental_management.invoice_post_type")
        )
        deposit_invoice_id = (
            self.env["account.move"]
            .sudo()
            .create(
                {
                    "partner_id": self.tenancy_id.id,
                    "move_type": "out_invoice",
                    "invoice_date": self.invoice_start_date,
                    "tenancy_id": self.id,
                    "is_deposit_invoice": True,
                    "invoice_line_ids": [
                        (
                            0,
                            0,
                            {
                                "product_id": self.deposit_item_id.id,
                                "name": "Deposit of " + self.property_id.name,
                                "quantity": 1,
                                "price_unit": self.deposit_amount,
                                "tax_ids": self.tax_ids.ids
                                if self.deposit_tax
                                else False,
                            },
                        )
                    ],
                }
            )
        )
        if invoice_post_type == "automatically":
            deposit_invoice_id.action_post()
        self.env["rent.invoice"].create(
            {
                "tenancy_id": self.id,
                "type": "deposit",
                "invoice_date": self.invoice_start_date,
                "description": "Deposit of " + self.property_id.name,
                "rent_invoice_id": deposit_invoice_id.id,
                "amount": deposit_invoice_id.amount_total,
            }
        )
        return deposit_invoice_id

    # Active Contract
    def action_active_contract(self):
        """Process auto Installment for Rent Unit : Month and Year"""
        # Approval-workflow state guard.  Only ``approved`` contracts may
        # be activated.  This is a defensive check — the UI hides the
        # Active button on other states, but RPC / cron / future code
        # paths could still call this method directly.
        self.ensure_one()
        if self.contract_type != "approved":
            raise UserError(
                _(
                    "Only approved rent contracts can be activated. "
                    "Please submit the contract for approval and wait for "
                    "manager approval first. (Current state: %(state)s)",
                    state=self.contract_type,
                )
            )
        invoice_post_type = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("rental_management.invoice_post_type")
        )
        payment_term = {
            "monthly": "Month",
            "bi_monthly": "Bi-Month",
            "half_year": "Half Year",
            "quarterly": "Quarter",
            "year": "Year",
        }
        invoice_lines = []
        # Broker Invoice
        if self.is_any_broker:
            self.action_broker_invoice()
        # Add Installment Line
        invoice_lines.append(
            (
                0,
                0,
                {
                    "product_id": self.installment_item_id.id,
                    "quantity": self.get_payment_term_qty(),
                    "name": f"First {payment_term.get(self.payment_term)} "
                    f"Invoice of {self.property_id.name}",
                    "tax_ids": self.tax_ids.ids if self.instalment_tax else False,
                    "price_unit": self.total_rent,
                },
            )
        )
        # Add Maintenance Line
        if self.is_maintenance_service and self.maintenance_service_invoice == "merge":
            qty = 1
            if self.payment_term == "quarterly":
                qty = 3
            elif self.payment_term == "bi_monthly":
                qty = 2
            invoice_lines.append(
                (
                    0,
                    0,
                    {
                        "product_id": self.maintenance_item_id.id,
                        "name": "Maintenance of " + self.property_id.name,
                        "quantity": qty,
                        "price_unit": self.total_maintenance,
                    },
                )
            )
        # Add Extra Service
        if (
            self.is_added_services
            and self.added_service_ids
            and self.added_service_invoice == "merge"
        ):
            for line in self.added_service_ids:
                invoice_lines.append(
                    (
                        0,
                        0,
                        {
                            "product_id": line.service_id.id,
                            "name": line.service_id.name,
                            "quantity": 1,
                            "price_unit": line.price,
                        },
                    )
                )
        if (
            self.is_added_services
            and self.added_service_ids
            and self.added_service_invoice == "separate"
        ):
            self._process_separate_added_services()
        # Add Utility Services
        if self.is_extra_service and self.extra_service_invoice == "merge":
            for service in self.extra_services_ids:
                service_type = "Once" if service.service_type == "once" else "Recurring"
                invoice_lines.append(
                    (
                        0,
                        0,
                        {
                            "product_id": service.service_id.id,
                            "name": f"Service Type : {service_type} - {service.service_id.name}",
                            "quantity": 3
                            if self.payment_term == "quarterly"
                            else (2 if self.payment_term == "bi_monthly" else 1),
                            "price_unit": service.price,
                            "tax_ids": self.tax_ids.ids if self.service_tax else False,
                        },
                    )
                )

        # Create First Installment Invoice
        invoice_id = (
            self.env["account.move"]
            .sudo()
            .create(
                {
                    "partner_id": self.tenancy_id.id,
                    "move_type": "out_invoice",
                    "invoice_date": self.invoice_start_date,
                    "invoice_line_ids": invoice_lines,
                    "tenancy_id": self.id,
                }
            )
        )
        if invoice_post_type == "automatically":
            invoice_id.action_post()
        self.action_create_rent_invoice_entry(
            amount=invoice_id.amount_total, invoice_id=invoice_id
        )
        # Separate Deposit Invoice
        self._create_deposit_invoice()
        self.action_send_active_contract()
        # Process Separate Installment: Maintenance and Services
        if (
            self.is_maintenance_service
            and self.maintenance_service_invoice == "separate"
        ):
            self._process_separate_invoices(maintenance=True)
        if self.is_extra_service and self.extra_service_invoice == "separate":
            self._process_separate_invoices(utility=True)
        # Post Processing
        self.write(
            {
                "contract_type": "running_contract",
                "active_contract_state": True,
                "last_invoice_payment_date": invoice_id.invoice_date,
                "type": "automatic",
            }
        )

    def action_active_rent_contract(self):
        """Active contract & open wizard bases on rent Unit"""
        if self.rent_unit == "Day":
            wizard_id = (
                self.env["active.contract"]
                .with_context(active_id=self.id)
                .sudo()
                .create({"contract_id": self.id, "type": "manual"})
            )
            if wizard_id:
                wizard_id.action_create_contract()
        else:
            action = self.env["ir.actions.act_window"]._for_xml_id(
                "rental_management.active_contract_action"
            )
            action["context"] = {"active_id": self.id}
            return action

    # ------------------------------------------------------------------ #
    #  Approval workflow                                                #
    #  ----------------------------------------------------------------  #
    #  Drafts (``new_contract``) are submitted for manager approval.    #
    #  Managers receive an email + a chatter activity per request.     #
    #  On approval, the contract moves to ``approved`` (the existing   #
    #  Active button is then visible).  On rejection (with mandatory   #
    #  reason captured by ``tenancy.reject.wizard``) the contract is   #
    #  returned to ``new_contract`` for the user to edit and resubmit. #
    # ------------------------------------------------------------------ #
    def action_submit_for_approval(self):
        """Move a Draft contract to Pending Approval.

        Guards:
            * state must be ``new_contract``;
            * at least one user must be in ``property_rental_manager``
              (otherwise the request can never be approved).

        Side effects:
            * Schedules a chatter activity for every manager;
            * Sends the approval-request email to every manager;
            * Writes ``submitted_by`` / ``submitted_date`` and flips
              ``contract_type`` to ``pending_approval``;
            * Posts an audit note in the chatter.
        """
        self.ensure_one()
        if self.contract_type != "new_contract":
            raise UserError(
                _(
                    "Only Draft rent contracts can be submitted for approval. "
                    "(Current state: %(state)s)",
                    state=self.contract_type,
                )
            )

        # Validate that at least one manager is configured.
        manager_partners = self._get_rental_manager_partners()
        manager_users = self._get_rental_manager_users()
        if not manager_users:
            raise UserError(
                _(
                    "No Rental Manager is configured. Please contact your "
                    "administrator before submitting a contract for approval."
                )
            )

        now = fields.Datetime.now()

        # Schedule a chatter activity for every manager so the request
        # also shows up in the Odoo inbox / activity widget.
        # ``activity_schedule`` takes the activity-type XML ID as a string
        # and resolves it internally via ``ir.model.data._xmlid_to_res_id``.
        for mgr_user in manager_users:
            self.activity_schedule(
                "mail.mail_activity_data_todo",
                user_id=mgr_user.id,
                summary=_("Approve contract %s", self.tenancy_seq or ""),
                note=_(
                    "Rent contract %(seq)s was submitted for approval by "
                    "%(user)s on %(date)s.",
                    seq=self.tenancy_seq,
                    user=self.env.user.name,
                    date=fields.Datetime.to_string(now),
                ),
                date_deadline=fields.Date.add(fields.Date.today(), days=3),
            )

        # Send the email.  The template's ``partner_to`` is set to
        # ``False`` — recipients are passed in ``recipient_ids``.
        template = self.env.ref(
            "rental_management.tenancy_approval_request_mail_template",
            raise_if_not_found=False,
        )
        if template and manager_partners:
            template.send_mail(
                self.id,
                force_send=True,
                email_values={
                    "recipient_ids": [(4, p.id) for p in manager_partners],
                },
            )

        # Persist the state change + audit fields.
        self.write(
            {
                "submitted_by": self.env.user.id,
                "submitted_date": now,
                "contract_type": "pending_approval",
            }
        )

        # Audit note in the chatter.
        self.message_post(
            body=_(
                "<b>Contract Submitted for Approval</b><br/>"
                "Submitted by <b>%(user)s</b> on %(date)s.<br/>"
                "Notified %(count)d manager(s).",
                user=self.env.user.name,
                date=fields.Datetime.to_string(now),
                count=len(manager_users),
            ),
            subject=_("Rent Contract Submitted for Approval"),
            message_type="comment",
            subtype_xmlid="mail.mt_note",
        )

    def action_approve(self):
        """Manager action — approve a pending rent contract.

        Guards:
            * state must be ``pending_approval``;
            * current user must be in ``property_rental_manager``;
            * current user must NOT be the submitter (separation of
              duties).

        Side effects:
            * Dismisses any open approval activities;
            * Sends the approval email to the submitter;
            * Writes ``approved_by`` / ``approved_date`` and flips
              ``contract_type`` to ``approved``;
            * Posts an audit note in the chatter.
        """
        self.ensure_one()
        if self.contract_type != "pending_approval":
            raise UserError(
                _(
                    "Only contracts pending approval can be approved. "
                    "(Current state: %(state)s)",
                    state=self.contract_type,
                )
            )

        if not self.env.user.has_group(
            "rental_management.property_rental_manager"
        ):
            raise UserError(
                _(
                    "Only users in the Rental Manager group can approve "
                    "rent contracts."
                )
            )

        if self.submitted_by and self.submitted_by == self.env.user:
            raise UserError(
                _(
                    "You cannot approve a rent contract that you submitted. "
                    "Another manager must perform the approval."
                )
            )

        now = fields.Datetime.now()

        # Dismiss the approval activities (best-effort — see also the
        # reject wizard's similar handling).
        try:
            self.activity_feedback(["mail.mail_activity_data_todo"])
        except Exception:  # pylint: disable=broad-except
            _logger.warning(
                "Failed to clear approval activities for tenancy %s",
                self.id,
                exc_info=True,
            )

        # Email the submitter.
        submitter_partner = self.submitted_by.partner_id if self.submitted_by else False
        template = self.env.ref(
            "rental_management.tenancy_approval_approved_mail_template",
            raise_if_not_found=False,
        )
        if template and submitter_partner and submitter_partner.email:
            template.send_mail(
                self.id,
                force_send=True,
                email_values={"recipient_ids": [(4, submitter_partner.id)]},
            )

        # Persist the state change + audit fields.
        self.write(
            {
                "approved_by": self.env.user.id,
                "approved_date": now,
                "contract_type": "approved",
            }
        )

        # Audit note in the chatter.
        self.message_post(
            body=_(
                "<b>Contract Approved</b><br/>"
                "Approved by <b>%(user)s</b> on %(date)s.",
                user=self.env.user.name,
                date=fields.Datetime.to_string(now),
            ),
            subject=_("Rent Contract Approved"),
            message_type="comment",
            subtype_xmlid="mail.mt_note",
        )

    def action_open_reject_wizard(self):
        """Open the rejection wizard for the current contract.

        The wizard (``tenancy.reject.wizard``) is responsible for
        validating the mandatory reason, persisting the rejection, and
        sending the rejection email.
        """
        self.ensure_one()
        if self.contract_type != "pending_approval":
            raise UserError(
                _(
                    "Only contracts pending approval can be rejected. "
                    "(Current state: %(state)s)",
                    state=self.contract_type,
                )
            )
        return {
            "type": "ir.actions.act_window",
            "name": _("Reject Rent Contract"),
            "res_model": "tenancy.reject.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_tenancy_id": self.id},
        }

    def _process_separate_added_services(self):
        """Add Extra Service Invoice : Separate"""
        invoice_lines = []
        for data in self.added_service_ids:
            invoice_lines.append(
                (
                    0,
                    0,
                    {
                        "product_id": data.service_id.id,
                        "name": data.service_id.name,
                        "quantity": 1,
                        "price_unit": data.price,
                    },
                )
            )
        if invoice_lines:
            invoice_id = (
                self.env["account.move"]
                .sudo()
                .create(
                    {
                        "partner_id": self.tenancy_id.id,
                        "move_type": "out_invoice",
                        "invoice_date": self.invoice_start_date,
                        "invoice_line_ids": invoice_lines,
                        "tenancy_id": self.id,
                    }
                )
            )
            self.added_service_ids.write({"invoice_id": invoice_id.id})

    def _process_separate_invoices(
        self, maintenance=None, utility=None, quarter_qty=None
    ):
        """Process Utility and Maintenance Separate Invoices"""
        quarter = quarter_qty if quarter_qty else 3
        if maintenance:
            maintenance_invoice_id = self.env["account.move"].create(
                {
                    "partner_id": self.tenancy_id.id,
                    "move_type": "out_invoice",
                    "invoice_date": self.invoice_start_date,
                    "tenancy_id": self.id,
                    "invoice_line_ids": [
                        (
                            0,
                            0,
                            {
                                "product_id": self.maintenance_item_id.id,
                                "name": "Maintenance of " + self.property_id.name,
                                "quantity": quarter
                                if self.payment_term == "quarterly"
                                else 1,
                                "price_unit": self.total_maintenance,
                            },
                        )
                    ],
                }
            )
            self.env["rent.invoice"].create(
                {
                    "tenancy_id": self.id,
                    "type": "maintenance",
                    "invoice_date": self.invoice_start_date,
                    "amount": maintenance_invoice_id.amount_total,
                    "description": "Maintenance of " + self.property_id.name,
                    "rent_invoice_id": maintenance_invoice_id.id,
                }
            )
        if utility:
            service_invoice_lines = []
            for line in self.extra_services_ids:
                service_type = "Once" if line.service_type == "once" else "Recurring"
                service_invoice_lines.append(
                    (
                        0,
                        0,
                        {
                            "product_id": line.service_id.id,
                            "name": f"Service Type : {service_type} - {line.service_id.name}",
                            "quantity": quarter
                            if self.payment_term == "quarterly"
                            else 1,
                            "price_unit": line.price,
                            "tax_ids": self.tax_ids.ids if self.service_tax else False,
                        },
                    )
                )
            service_invoice_id = self.env["account.move"].create(
                {
                    "partner_id": self.tenancy_id.id,
                    "move_type": "out_invoice",
                    "invoice_date": self.invoice_start_date,
                    "tenancy_id": self.id,
                    "invoice_line_ids": service_invoice_lines,
                }
            )
            self.env["rent.invoice"].create(
                {
                    "tenancy_id": self.id,
                    "type": "other",
                    "invoice_date": self.invoice_start_date,
                    "amount": service_invoice_id.amount_total,
                    "description": "Utility Services",
                    "rent_invoice_id": service_invoice_id.id,
                }
            )

    # Rent Invoice Record
    def action_create_rent_invoice_entry(self, amount, invoice_id):
        """Create rent invoice entry"""
        rent_invoice = {
            "tenancy_id": self.id,
            "type": "rent",
            "invoice_date": self.invoice_start_date,
            "rent_invoice_id": invoice_id.id,
            "amount": amount,
        }
        if self.payment_term == "monthly":
            rent_invoice["description"] = "First Rent"
        if self.payment_term == "quarterly":
            rent_invoice["description"] = "First Quarter Rent"
        if self.payment_term == "half_year":
            rent_invoice["description"] = "First Half Year Rent"
        if self.payment_term == "year":
            rent_invoice["description"] = "First Year Rent"
        self.env["rent.invoice"].create(rent_invoice)

    # Cancel Contract

    def action_cancel_contract(self):
        """Status : Close rent contract"""
        self.close_contract_state = True
        self.property_id.write({"stage": "available"})
        self.contract_type = "cancel_contract"
        self.terminate_date = fields.Date.today()

    # Send active Contract Mail
    def action_send_active_contract(self):
        """Send main notification on active contract"""
        mail_template = self.env.ref(
            "rental_management.active_contract_mail_template", raise_if_not_found=False
        )
        if mail_template:
            mail_template.send_mail(self.id, force_send=True)

    # Send Tenancy reminder Mail
    def action_send_tenancy_reminder(self):
        """Send tenancy reminder to tenant"""
        mail_template = self.env.ref(
            "rental_management.tenancy_reminder_mail_template", raise_if_not_found=False
        )
        if mail_template:
            mail_template.send_mail(
                self.id,
                email_values={"author_id": self.company_id.partner_id.id},
                force_send=True,
            )

    # Broker Invoice
    def action_broker_invoice(self):
        """Create Broker Invoices"""
        invoice_post_type = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("rental_management.invoice_post_type")
        )
        record = {
            "product_id": self.broker_item_id.id,
            "name": "Brokerage of " + self.property_id.name,
            "quantity": 1,
            "price_unit": self.commission,
        }
        invoice_lines = [(0, 0, record)]
        data = {
            "partner_id": self.broker_id.id,
            "move_type": "in_invoice",
            "invoice_date": self.invoice_start_date,
            "invoice_line_ids": invoice_lines,
        }
        invoice_id = self.env["account.move"].sudo().create(data)
        invoice_id.tenancy_id = self.id
        invoice_id.action_post()
        self.broker_invoice_state = True
        self.broker_invoice_id = invoice_id.id
        if self.commission_from == "customer":
            customer_invoice_id = self.env["account.move"].create(
                {
                    "partner_id": self.tenancy_id.id,
                    "move_type": "out_invoice",
                    "invoice_date": self.invoice_start_date,
                    "invoice_line_ids": [
                        (
                            0,
                            0,
                            {
                                "product_id": self.broker_item_id.id,
                                "name": "Broker Brokerage of" + self.property_id.name,
                                "quantity": 1,
                                "price_unit": self.commission,
                            },
                        )
                    ],
                }
            )
            if invoice_post_type == "automatically":
                customer_invoice_id.action_post()
            self.env["rent.invoice"].create(
                {
                    "tenancy_id": self.id,
                    "type": "rent",
                    "invoice_date": customer_invoice_id.invoice_date,
                    "description": "Broker Brokerage",
                    "rent_invoice_id": customer_invoice_id.id,
                    "amount": customer_invoice_id.amount_total,
                    "rent_amount": customer_invoice_id.amount_total,
                }
            )

    @api.model
    def tenancy_recurring_invoice(self):
        """
        Scheduler : Tenancy recurring invoice for monthly payment term & automatic installments
        """
        # today_date = datetime.date(2023, 8, 1)
        today_date = fields.Date.today()
        reminder_days = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("rental_management.reminder_days")
        )
        invoice_post_type = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("rental_management.invoice_post_type")
        )
        tenancy_contracts = (
            self.env["tenancy.details"]
            .sudo()
            .search(
                [
                    ("contract_type", "=", "running_contract"),
                    ("payment_term", "=", "monthly"),
                    ("final_rent_unit", "=", "Month"),
                    ("type", "=", "automatic"),
                ]
            )
        )
        for rec in tenancy_contracts:
            if (
                rec.contract_type == "running_contract"
                and rec.payment_term == "monthly"
            ):
                if today_date < rec.end_date:
                    invoice_date = rec.last_invoice_payment_date + relativedelta(
                        months=1
                    )
                    next_invoice_date = (
                        rec.last_invoice_payment_date
                        + relativedelta(months=1)
                        - relativedelta(days=int(reminder_days))
                    )
                    if today_date == next_invoice_date:
                        record = {
                            "product_id": rec.installment_item_id.id,
                            "name": "Installment of " + rec.property_id.name,
                            "quantity": 1,
                            "price_unit": rec.total_rent,
                            "tax_ids": rec.tax_ids.ids if rec.instalment_tax else False,
                        }
                        invoice_lines = [(0, 0, record)]
                        if (
                            rec.is_extra_service
                            and rec.extra_service_invoice == "merge"
                        ):
                            for line in rec.extra_services_ids.filtered(
                                lambda line: line.service_type == "monthly"
                            ):
                                if line.service_type == "monthly":
                                    invoice_lines.append(
                                        (
                                            0,
                                            0,
                                            {
                                                "product_id": line.service_id.id,
                                                "name": "Service Type : Recurring"
                                                + "\n"
                                                + f"Service : {line.service_id.name}",
                                                "quantity": 1,
                                                "price_unit": line.price,
                                                "tax_ids": rec.tax_ids.ids
                                                if rec.service_tax
                                                else False,
                                            },
                                        )
                                    )
                        if (
                            rec.is_maintenance_service
                            and rec.maintenance_rent_type == "recurring"
                            and rec.maintenance_service_invoice == "merge"
                        ):
                            invoice_lines.append(
                                (
                                    0,
                                    0,
                                    {
                                        "product_id": rec.maintenance_item_id.id,
                                        "name": "Recurring Monthly Maintenance of "
                                        + rec.property_id.name,
                                        "quantity": 1,
                                        "price_unit": rec.total_maintenance,
                                    },
                                )
                            )
                        invoice_id = (
                            self.env["account.move"]
                            .sudo()
                            .create(
                                {
                                    "partner_id": rec.tenancy_id.id,
                                    "move_type": "out_invoice",
                                    "invoice_date": invoice_date,
                                    "invoice_line_ids": invoice_lines,
                                    "tenancy_id": rec.id,
                                }
                            )
                        )
                        if invoice_post_type == "automatically":
                            invoice_id.action_post()
                        rec.last_invoice_payment_date = invoice_id.invoice_date
                        # Automatically link PDC cheques to newly created invoice
                        if rec.pdc_enabled and rec.pdc_generated:
                            rec.action_update_pdc_invoice_links()
                        self.env["rent.invoice"].create(
                            {
                                "tenancy_id": rec.id,
                                "type": "rent",
                                "invoice_date": invoice_date,
                                "description": "Installment of " + rec.property_id.name,
                                "rent_invoice_id": invoice_id.id,
                                "amount": invoice_id.amount_total,
                                "rent_amount": self.total_rent,
                            }
                        )
                        # Process Separate Invoice
                        if (
                            rec.is_maintenance_service
                            and rec.maintenance_service_invoice == "separate"
                        ):
                            rec._process_separate_invoices(maintenance=True)
                        if (
                            rec.is_extra_service
                            and rec.extra_service_invoice == "separate"
                        ):
                            rec._process_separate_invoices(utility=True)
                        # Send Reminder
                        rec.action_send_tenancy_reminder()

    # Expire Contract Scheduler
    @api.model
    def tenancy_expire(self):
        """
        Scheduler : Expire rent contract
        """
        today_date = fields.Date.today()
        tenancy_contracts = (
            self.env["tenancy.details"]
            .sudo()
            .search([("contract_type", "=", "running_contract")])
        )
        for rec in tenancy_contracts:
            if rec.contract_type == "running_contract" and today_date > rec.end_date:
                rec.contract_type = "expire_contract"

    # 90 days expiry reminder
    @api.model
    def tenancy_expiry_reminder_90_days(self):
        """
        Scheduler: Send reminder email to customer and responsible user
        when contract is expiring in 90 days or less.
        Runs daily. Sends only once per contract unless reset.
        """
        today = fields.Date.today()
        reminder_threshold = 90

        # Fetch all running contracts - filter entirely in Python
        all_running = self.sudo().search([("contract_type", "=", "running_contract")])

        expiring_contracts = all_running.filtered(
            lambda c: (
                c.end_date
                and c.days_left > 0
                and c.days_left <= reminder_threshold
                and not c.is_expiry_reminder_sent
            )
        )

        for contract in expiring_contracts:
            contract.action_send_90_days_expiry_reminder()
            contract.write(
                {
                    "is_expiry_reminder_sent": True,
                    "expiry_reminder_date": today,
                }
            )

        # Reset for extended contracts
        reminded_contracts = all_running.filtered(
            lambda c: (
                c.is_expiry_reminder_sent
                and c.end_date
                and (c.days_left > reminder_threshold or c.days_left <= 0)
            )
        )

        if reminded_contracts:
            reminded_contracts.write(
                {
                    "is_expiry_reminder_sent": False,
                    "expiry_reminder_date": False,
                }
            )

    def action_send_90_days_expiry_reminder(self):
        """Send 90 days expiry reminder email to customer and responsible user"""
        self.ensure_one()

        template = self.env.ref(
            "rental_management.tenancy_90_days_expiry_reminder_template",
            raise_if_not_found=False,
        )

        if not template:
            return False

        # Send to customer
        if self.tenancy_id and self.tenancy_id.email:
            template.send_mail(
                self.id,
                force_send=True,
                email_values={
                    "recipient_ids": [(4, self.tenancy_id.id)],
                },
            )

        # Send to responsible user
        if (
            self.responsible_id
            and self.responsible_id.partner_id
            and self.responsible_id.partner_id.email
        ):
            template.send_mail(
                self.id,
                force_send=True,
                email_values={
                    "recipient_ids": [(4, self.responsible_id.partner_id.id)],
                },
            )

        return True

    def action_print_agreement(self):
        self.ensure_one()
        if self.agreement_template_id and self.agreement_template_id.template_type == "printable" and self.agreement_template_id.report_id:
            return self.agreement_template_id.report_id.report_action(self)
        raise UserError(_("The selected agreement template has no printable format configured."))

    # Quarterly Recurring Invoice
    @api.model
    def tenancy_recurring_quarterly_invoice(self):
        """
        Scheduler : Tenancy recurring invoice for quarterly payment term & automatic installments
        """
        today_date = fields.Date.today()
        # today_date = datetime.date(2024, 4, 1)
        reminder_days = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("rental_management.reminder_days")
        )
        invoice_post_type = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("rental_management.invoice_post_type")
        )
        tenancy_contracts = (
            self.env["tenancy.details"]
            .sudo()
            .search(
                [
                    ("contract_type", "=", "running_contract"),
                    ("payment_term", "=", "quarterly"),
                    ("type", "=", "automatic"),
                    ("final_rent_unit", "=", "Month"),
                ]
            )
        )
        for rec in tenancy_contracts:
            if (
                rec.contract_type == "running_contract"
                and rec.payment_term == "quarterly"
            ):
                if today_date < rec.end_date:
                    invoice_date = rec.last_invoice_payment_date + relativedelta(
                        months=3
                    )
                    next_next_invoice_date = invoice_date + relativedelta(months=3)
                    next_invoice_date = (
                        rec.last_invoice_payment_date
                        + relativedelta(months=3)
                        - relativedelta(days=int(reminder_days))
                    )
                    if rec.end_date < next_next_invoice_date:
                        delta = relativedelta(next_next_invoice_date, rec.end_date)
                        diff = delta.months
                    else:
                        diff = 0
                    if today_date == next_invoice_date:
                        record = {
                            "product_id": rec.installment_item_id.id,
                            "name": "Quarterly Installment of " + rec.property_id.name,
                            "quantity": 1,
                            "price_unit": rec.total_rent * (3 - diff),
                            "tax_ids": rec.tax_ids.ids if rec.instalment_tax else False,
                        }
                        invoice_lines = [(0, 0, record)]
                        if (
                            rec.is_extra_service
                            and rec.extra_service_invoice == "merge"
                        ):
                            for line in rec.extra_services_ids.filtered(
                                lambda line: line.service_type == "monthly"
                            ):
                                invoice_lines.append(
                                    (
                                        0,
                                        0,
                                        {
                                            "product_id": line.service_id.id,
                                            "name": "Service Type : Quarterly"
                                            + "\n"
                                            + f"Service : {line.service_id.name}",
                                            "quantity": (3 - diff),
                                            "price_unit": line.price * (3 - diff),
                                            "tax_ids": rec.tax_ids.ids
                                            if rec.service_tax
                                            else False,
                                        },
                                    )
                                )
                        if (
                            rec.is_maintenance_service
                            and rec.maintenance_rent_type == "recurring"
                            and rec.maintenance_service_invoice == "merge"
                        ):
                            invoice_lines.append(
                                (
                                    0,
                                    0,
                                    {
                                        "product_id": rec.maintenance_item_id.id,
                                        "name": "Recurring Quarterly Maintenance of "
                                        + rec.property_id.name,
                                        "quantity": (3 - diff),
                                        "price_unit": rec.total_maintenance
                                        * (3 - diff),
                                    },
                                )
                            )
                        invoice_id = (
                            self.env["account.move"]
                            .sudo()
                            .create(
                                {
                                    "partner_id": rec.tenancy_id.id,
                                    "move_type": "out_invoice",
                                    "invoice_date": invoice_date,
                                    "invoice_line_ids": invoice_lines,
                                }
                            )
                        )
                        invoice_id.tenancy_id = rec.id
                        if invoice_post_type == "automatically":
                            invoice_id.action_post()
                        rec.last_invoice_payment_date = invoice_id.invoice_date
                        # Automatically link PDC cheques to newly created invoice
                        if rec.pdc_enabled and rec.pdc_generated:
                            rec.action_update_pdc_invoice_links()
                        rent_invoice = {
                            "tenancy_id": rec.id,
                            "type": "rent",
                            "invoice_date": invoice_date,
                            "description": "Quarterly Installment of "
                            + rec.property_id.name,
                            "rent_invoice_id": invoice_id.id,
                            "amount": invoice_id.amount_total,
                            "rent_amount": self.total_rent * (3 - diff),
                        }
                        self.env["rent.invoice"].create(rent_invoice)
                        # Process Separate Invoice
                        if (
                            rec.is_maintenance_service
                            and rec.maintenance_service_invoice == "separate"
                        ):
                            rec._process_separate_invoices(
                                maintenance=True, quarter_qty=(3 - diff)
                            )
                        if (
                            rec.is_extra_service
                            and rec.extra_service_invoice == "separate"
                        ):
                            rec._process_separate_invoices(
                                utility=True, quarter_qty=(3 - diff)
                            )
                        # Send Reminder
                        rec.action_send_tenancy_reminder()

    # Yearly Recurring Invoice
    @api.model
    def tenancy_yearly_invoice(self):
        """
        Scheduler : Tenancy recurring invoice for yearly payment term & automatic installments
        """
        today_date = fields.Date.today()
        # today_date = datetime.date(2024, 7, 1)
        reminder_days = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("rental_management.reminder_days")
        )
        invoice_post_type = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("rental_management.invoice_post_type")
        )
        tenancy_contracts = (
            self.env["tenancy.details"]
            .sudo()
            .search(
                [
                    ("contract_type", "=", "running_contract"),
                    ("type", "=", "automatic"),
                    ("payment_term", "=", "year"),
                    ("final_rent_unit", "=", "Year"),
                ]
            )
        )
        for rec in tenancy_contracts:
            if today_date < rec.end_date:
                invoice_date = rec.last_invoice_payment_date + relativedelta(years=1)
                next_invoice_date = (
                    rec.last_invoice_payment_date
                    + relativedelta(years=1)
                    - relativedelta(days=int(reminder_days))
                )
                if today_date == next_invoice_date:
                    record = {
                        "product_id": rec.installment_item_id.id,
                        "name": "Yearly installment of " + str(rec.property_id.name),
                        "quantity": 1,
                        "price_unit": rec.total_rent,
                        "tax_ids": rec.tax_ids.ids if rec.instalment_tax else False,
                    }
                    invoice_lines = [(0, 0, record)]
                    if rec.is_extra_service and rec.extra_service_invoice == "merge":
                        for line in rec.extra_services_ids.filtered(
                            lambda line: line.service_type == "monthly"
                        ):
                            invoice_lines.append(
                                (
                                    0,
                                    0,
                                    {
                                        "product_id": line.service_id.id,
                                        "name": "Service Type : Recurring"
                                        + "\n"
                                        + f"Service : {line.service_id.name}",
                                        "quantity": 1,
                                        "price_unit": line.price,
                                        "tax_ids": rec.tax_ids.ids
                                        if rec.service_tax
                                        else False,
                                    },
                                )
                            )

                    if (
                        rec.is_maintenance_service
                        and rec.maintenance_rent_type == "recurring"
                        and rec.maintenance_service_invoice == "merge"
                    ):
                        invoice_lines.append(
                            (
                                0,
                                0,
                                {
                                    "product_id": rec.maintenance_item_id.id,
                                    "name": "Recurring Monthly Maintenance of "
                                    + rec.property_id.name,
                                    "quantity": 1,
                                    "price_unit": rec.total_maintenance,
                                },
                            )
                        )
                    invoice_id = (
                        self.env["account.move"]
                        .sudo()
                        .create(
                            {
                                "partner_id": rec.tenancy_id.id,
                                "move_type": "out_invoice",
                                "invoice_date": invoice_date,
                                "invoice_line_ids": invoice_lines,
                                "tenancy_id": rec.id,
                            }
                        )
                    )
                    if invoice_post_type == "automatically":
                        invoice_id.action_post()
                    rec.last_invoice_payment_date = invoice_id.invoice_date
                    # Automatically link PDC cheques to newly created invoice
                    if rec.pdc_enabled and rec.pdc_generated:
                        rec.action_update_pdc_invoice_links()
                    rent_invoice = {
                        "tenancy_id": rec.id,
                        "type": "rent",
                        "invoice_date": invoice_date,
                        "description": "Installment of " + rec.property_id.name,
                        "rent_invoice_id": invoice_id.id,
                        "amount": invoice_id.amount_total,
                        "rent_amount": self.total_rent,
                    }
                    self.env["rent.invoice"].create(rent_invoice)
                    # Process Separate Invoice
                    if (
                        rec.is_maintenance_service
                        and rec.maintenance_service_invoice == "separate"
                    ):
                        rec._process_separate_invoices(maintenance=True)
                    if rec.is_extra_service and rec.extra_service_invoice == "separate":
                        rec._process_separate_invoices(utility=True)
                    # Send Reminder
                    rec.action_send_tenancy_reminder()

    # Manual Invoice Rent Invoice Line
    @api.model
    def tenancy_manual_invoice(self):
        """
        Scheduler : Create invoice for manual installments
        """
        today_date = fields.Date.today()
        # today_date = datetime.date(2023, 8, 2)
        reminder_days = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("rental_management.reminder_days")
        )
        tenancy_contracts = (
            self.env["tenancy.details"]
            .sudo()
            .search(
                [("contract_type", "=", "running_contract"), ("type", "=", "manual")]
            )
        )
        for data in tenancy_contracts:
            for rec in data.rent_invoice_ids:
                if not rec.rent_invoice_id:
                    invoice_date = rec.invoice_date - relativedelta(
                        days=int(reminder_days)
                    )
                    if today_date == invoice_date:
                        rec.action_create_invoice()
            data.action_send_tenancy_reminder()

    # Bi-Monthly Recurring Invoice
    @api.model
    def tenancy_recurring_bi_monthly_invoice(self):
        """
        Scheduler : Tenancy recurring invoice for bi-monthly installments
        """
        today_date = fields.Date.today()
        reminder_days = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("rental_management.reminder_days")
        )
        invoice_post_type = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("rental_management.invoice_post_type")
        )
        tenancy_contracts = (
            self.env["tenancy.details"]
            .sudo()
            .search(
                [
                    ("contract_type", "=", "running_contract"),
                    ("payment_term", "=", "bi_monthly"),
                    ("type", "=", "automatic"),
                    ("final_rent_unit", "=", "Month"),
                ]
            )
        )
        for rec in tenancy_contracts:
            if (
                rec.contract_type == "running_contract"
                and rec.payment_term == "bi_monthly"
            ):
                if today_date < rec.end_date:
                    invoice_date = rec.last_invoice_payment_date + relativedelta(
                        months=2
                    )
                    next_next_invoice_date = invoice_date + relativedelta(months=2)
                    next_invoice_date = (
                        rec.last_invoice_payment_date
                        + relativedelta(months=2)
                        - relativedelta(days=int(reminder_days))
                    )
                    if rec.end_date < next_next_invoice_date:
                        delta = relativedelta(next_next_invoice_date, rec.end_date)
                        diff = delta.months
                    else:
                        diff = 0
                    if today_date == next_invoice_date:
                        record = {
                            "product_id": rec.installment_item_id.id,
                            "name": "Bi-Monthly Installment of " + rec.property_id.name,
                            "quantity": 1,
                            "price_unit": rec.total_rent * (2 - diff),
                            "tax_ids": rec.tax_ids.ids if rec.instalment_tax else False,
                        }
                        invoice_lines = [(0, 0, record)]
                        if (
                            rec.is_extra_service
                            and rec.extra_service_invoice == "merge"
                        ):
                            for line in rec.extra_services_ids.filtered(
                                lambda line: line.service_type == "monthly"
                            ):
                                invoice_lines.append(
                                    (
                                        0,
                                        0,
                                        {
                                            "product_id": line.service_id.id,
                                            "name": "Service Type : Bi-Monthly"
                                            + "\n"
                                            + f"Service : {line.service_id.name}",
                                            "quantity": (2 - diff),
                                            "price_unit": line.price * (2 - diff),
                                            "tax_ids": rec.tax_ids.ids
                                            if rec.service_tax
                                            else False,
                                        },
                                    )
                                )
                        if (
                            rec.is_maintenance_service
                            and rec.maintenance_rent_type == "recurring"
                            and rec.maintenance_service_invoice == "merge"
                        ):
                            invoice_lines.append(
                                (
                                    0,
                                    0,
                                    {
                                        "product_id": rec.maintenance_item_id.id,
                                        "name": "Recurring Bi-Monthly Maintenance of "
                                        + rec.property_id.name,
                                        "quantity": (2 - diff),
                                        "price_unit": rec.total_maintenance
                                        * (2 - diff),
                                    },
                                )
                            )
                        invoice_id = (
                            self.env["account.move"]
                            .sudo()
                            .create(
                                {
                                    "partner_id": rec.tenancy_id.id,
                                    "move_type": "out_invoice",
                                    "invoice_date": invoice_date,
                                    "invoice_line_ids": invoice_lines,
                                }
                            )
                        )
                        invoice_id.tenancy_id = rec.id
                        if invoice_post_type == "automatically":
                            invoice_id.action_post()
                        rec.last_invoice_payment_date = invoice_id.invoice_date
                        # Automatically link PDC cheques to newly created invoice
                        if rec.pdc_enabled and rec.pdc_generated:
                            rec.action_update_pdc_invoice_links()
                        rent_invoice = {
                            "tenancy_id": rec.id,
                            "type": "rent",
                            "invoice_date": invoice_date,
                            "description": "Bi-Monthly Installment of "
                            + rec.property_id.name,
                            "rent_invoice_id": invoice_id.id,
                            "amount": invoice_id.amount_total,
                            "rent_amount": self.total_rent * (2 - diff),
                        }
                        self.env["rent.invoice"].create(rent_invoice)
                        # Process Separate Invoice
                        if (
                            rec.is_maintenance_service
                            and rec.maintenance_service_invoice == "separate"
                        ):
                            rec._process_separate_invoices(
                                maintenance=True, quarter_qty=(2 - diff)
                            )
                        if (
                            rec.is_extra_service
                            and rec.extra_service_invoice == "separate"
                        ):
                            rec._process_separate_invoices(
                                utility=True, quarter_qty=(2 - diff)
                            )
                        # Send Reminder
                        rec.action_send_tenancy_reminder()

    @api.model
    def get_default_product(self):
        """
        Scheduler: For older versions, if the maintenance product is not available
        in the rent contract, this scheduler will populate that product.
        :return:
        """
        tenancy_record = self.env["tenancy.details"].search(
            [("contract_type", "=", "running_contract")]
        )
        for rec in tenancy_record:
            if rec.is_maintenance_service and not rec.maintenance_item_id:
                config_maintenance_item = (
                    self.env["ir.config_parameter"]
                    .sudo()
                    .get_param("rental_management.account_maintenance_item_id")
                )
                default_maintenance_item = self.env.ref(
                    "rental_management.property_product_4", raise_if_not_found=False
                )
                if config_maintenance_item:
                    rec.maintenance_item_id = int(config_maintenance_item)
                elif not config_maintenance_item and default_maintenance_item:
                    rec.maintenance_item_id = default_maintenance_item.id
                else:
                    new_maintenance_item = self.env["product.product"].create(
                        {"name": "Maintenance Item", "type": "service"}
                    )
                    rec.maintenance_item = new_maintenance_item.id

    @api.onchange("agreement_template_id")
    def _onchange_agreement_template_id(self):
        """
        Process tenant agreement bases on agreement template configuration
        """
        for rec in self:
            agreement_data = ""
            if (
                rec.agreement_template_id
                and rec.agreement_template_id.template_variable_ids
            ):
                body = rec.agreement_template_id.agreement
                variable_dict = {}
                body_var = set(re.findall(r"{{[1-9][0-9]*}}", body or ""))
                for var in rec.agreement_template_id.template_variable_ids:
                    variable_dict[var.name] = var.demo
                    if var.field_type == "free_text":
                        variable_dict[var.name] = (
                            var.free_text if var.free_text else var.name
                        )
                    elif var.field_type == "field":
                        variable_dict[var.name] = (
                            self.mapped(var.field_name)[0]
                            if self.mapped(var.field_name)
                            else var.name
                        )
                for data in body_var:
                    body = body.replace(data, str(variable_dict.get(data)))
                agreement_data = body
            elif (
                rec.agreement_template_id
                and not rec.agreement_template_id.template_variable_ids
            ):
                agreement_data = rec.agreement_template_id.agreement
            rec.agreement = agreement_data

    @api.model
    def retrieve_contract_list_dashboard_data(self):
        """
        This function returns the values to populate the custom dashboard in
        the Contract List views.
        """
        tenancy_obj = self.env["tenancy.details"].sudo()
        stages = ["new_contract", "running_contract", "expire_contract"]
        payment_terms = [
            "monthly",
            "full_payment",
            "quarterly",
            "half_year",
            "year",
            "daily",
            "bi_monthly",
        ]
        duration_types = ["by_duration", "by_date"]
        data = {}

        for stage in stages:
            data[f"{stage}_count"] = tenancy_obj.search_count(
                [("contract_type", "=", stage)]
            )
        for payment_term in payment_terms:
            data[f"{payment_term}_count"] = tenancy_obj.search_count(
                [("payment_term", "=", payment_term)]
            )
        for duration_type in duration_types:
            data[f"{duration_type}_count"] = tenancy_obj.search_count(
                [("duration_type", "=", duration_type)]
            )
        return data

    @api.model
    def contract_auto_half_year_invoice(self):
        """
        Scheduler: Auto-generate half-yearly invoices for running tenancy contracts.
        """
        today = fields.Date.today()
        reminder_days = int(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("rental_management.reminder_days", default=0)
        )
        invoice_post_type = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("rental_management.invoice_post_type", default="draft")
        )

        contracts = (
            self.env["tenancy.details"]
            .sudo()
            .search(
                [
                    ("contract_type", "=", "running_contract"),
                    ("payment_term", "=", "half_year"),
                    ("type", "=", "automatic"),
                    ("final_rent_unit", "=", "Month"),
                ]
            )
        )

        for contract in contracts:
            if today >= contract.end_date:
                continue

            last_invoice_date = contract.last_invoice_payment_date
            invoice_date = last_invoice_date + relativedelta(months=6)
            next_next_invoice_date = invoice_date + relativedelta(months=6)
            reminder_date = invoice_date - relativedelta(days=reminder_days)

            if today != reminder_date:
                continue

            # Calculate number of months if contract ends before next-next invoice
            overrun = max(
                0, relativedelta(next_next_invoice_date, contract.end_date).months
            )
            effective_months = 6 - overrun

            invoice_lines = [
                (
                    0,
                    0,
                    {
                        "product_id": contract.installment_item_id.id,
                        "name": f"Semi-Annual Installment of {contract.property_id.name}",
                        "quantity": 1,
                        "price_unit": contract.total_rent * effective_months,
                        "tax_ids": contract.tax_ids.ids
                        if contract.instalment_tax
                        else False,
                    },
                )
            ]

            if contract.is_extra_service and contract.extra_service_invoice == "merge":
                for line in contract.extra_services_ids.filtered(
                    lambda l: l.service_type == "monthly"
                ):
                    invoice_lines.append(
                        (
                            0,
                            0,
                            {
                                "product_id": line.service_id.id,
                                "name": f"Service Type: Quarterly\nService: {line.service_id.name}",
                                "quantity": 1,
                                "price_unit": line.price,
                                "tax_ids": contract.tax_ids.ids
                                if contract.service_tax
                                else False,
                            },
                        )
                    )

            if (
                contract.is_maintenance_service
                and contract.maintenance_rent_type == "recurring"
                and contract.maintenance_service_invoice == "merge"
            ):
                invoice_lines.append(
                    (
                        0,
                        0,
                        {
                            "product_id": contract.maintenance_item_id.id,
                            "name": f"Recurring Quarterly Maintenance of {contract.property_id.name}",
                            "quantity": 1,
                            "price_unit": contract.total_maintenance,
                        },
                    )
                )

            invoice = (
                self.env["account.move"]
                .sudo()
                .create(
                    {
                        "partner_id": contract.tenancy_id.id,
                        "move_type": "out_invoice",
                        "invoice_date": invoice_date,
                        "invoice_line_ids": invoice_lines,
                    }
                )
            )
            invoice.tenancy_id = contract.id

            if invoice_post_type == "automatically":
                invoice.action_post()

            # Update contract info and create rent invoice record
            contract.last_invoice_payment_date = invoice.invoice_date
            # Automatically link PDC cheques to newly created invoice
            if contract.pdc_enabled and contract.pdc_generated:
                contract.action_update_pdc_invoice_links()
            self.env["rent.invoice"].create(
                {
                    "tenancy_id": contract.id,
                    "type": "rent",
                    "invoice_date": invoice_date,
                    "description": f"Semi-Annual Installment of {contract.property_id.name}",
                    "rent_invoice_id": invoice.id,
                    "amount": invoice.amount_total,
                    "rent_amount": contract.total_rent * effective_months,
                }
            )

            # Separate Invoices (if needed)
            if (
                contract.is_maintenance_service
                and contract.maintenance_service_invoice == "separate"
            ):
                contract._process_separate_invoices(maintenance=True)

            if (
                contract.is_extra_service
                and contract.extra_service_invoice == "separate"
            ):
                contract._process_separate_invoices(utility=True)

            # Send reminder
            contract.action_send_tenancy_reminder()

    @api.model
    def create_penalty_invoice(self):
        """
        Scheduler : Create Penalty Invoice For Rent Contract
        """
        rent_contracts = self.env["tenancy.details"].search(
            [
                ("contract_type", "=", "running_contract"),
                ("is_penalty_applied", "!=", False),
            ]
        )
        today = datetime.datetime.today().date()

        for contract in rent_contracts:
            rent_invoices = contract.rent_invoice_ids
            penalty_percentage = contract.penalty_percentage
            penalty_days_after_due = contract.penalty_days_after_due
            for invoice in rent_invoices:
                previous_penalty = self.env["penalty.invoice"].search(
                    [("rent_contract_invoice_id", "=", invoice.id)], limit=1
                )
                if (
                    not previous_penalty
                    and invoice.type in ["rent", "full_rent"]
                    and invoice.rent_invoice_id
                    and invoice.rent_invoice_id.state == "posted"
                    and invoice.rent_invoice_id.amount_residual > 0
                ):
                    invoice_due_date = (
                        invoice.rent_invoice_id.invoice_date_due
                        if invoice.rent_invoice_id.invoice_date_due
                        else invoice.rent_invoice_id.invoice_date
                    )
                    penalty_date = invoice_due_date + timedelta(
                        days=penalty_days_after_due
                    )
                    if penalty_date <= today:
                        penalty_amount = (
                            invoice.rent_invoice_id.amount_residual * penalty_percentage
                        ) / 100
                        penalty_data = {
                            "rent_contract_id": contract.id,
                            "customer_id": contract.tenancy_id.id,
                            "invoice_date": datetime.datetime.today(),
                            "rent_contract_invoice_id": invoice.id,
                            "amount": penalty_amount,
                            "description": f"Penalty invoice for overdue rent invoice {invoice.rent_invoice_id.name} under Rent Contract {contract.tenancy_seq}.",
                            "landlord_id": contract.property_landlord_id.id,
                        }
                        penalty_invoice = self.env["penalty.invoice"].create(
                            penalty_data
                        )
                        if penalty_invoice:
                            penalty_invoice.action_create_invoice()


# Contract Duration
class ContractDuration(models.Model):
    """Contract Duration"""

    _name = "contract.duration"
    _description = "Contract Duration and Month"
    _rec_name = "duration"

    duration = fields.Char(string="Duration", required=True, translate=True)
    month = fields.Integer(string="Unit")
    rent_unit = fields.Selection(
        [("Day", "Day"), ("Month", "Month"), ("Year", "Year")],
        default="Month",
        string="Rent Unit",
    )


# Tenancy Utility Service Line
class TenancyExtraServiceLine(models.Model):
    """Tenancy extra service lines"""

    _name = "tenancy.service.line"
    _description = "Tenancy Service Line"
    _rec_name = "service_id"

    service_id = fields.Many2one(
        "product.product",
        string="Service",
        domain=[("is_extra_service_product", "=", True)],
    )
    company_id = fields.Many2one(
        "res.company", string="Company", default=lambda self: self.env.company
    )
    currency_id = fields.Many2one(
        "res.currency", related="company_id.currency_id", string="Currency"
    )
    price = fields.Float(string="Cost")
    service_type = fields.Selection(
        [("once", "Once"), ("monthly", "Recurring")], string="Type", default="once"
    )
    tenancy_id = fields.Many2one("tenancy.details", string="Tenancies")
    from_contract = fields.Boolean()

    @api.onchange("service_id")
    def _onchange_service_id_price(self):
        """Get price bases on service_id"""
        for rec in self:
            if rec.service_id:
                rec.price = rec.service_id.lst_price

    def action_create_service_invoice(self):
        """Create service invoice for Type : 'Once'"""
        invoice_post_type = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("rental_management.invoice_post_type")
        )
        self.from_contract = True
        record = {
            "product_id": self.service_id.id,
            "name": "Extra Added Service",
            "quantity": 1,
            "price_unit": self.price,
            "tax_ids": self.tenancy_id.tax_ids.ids
            if self.tenancy_id.service_tax
            else False,
        }
        invoice_lines = [(0, 0, record)]
        data = {
            "partner_id": self.tenancy_id.tenancy_id.id,
            "move_type": "out_invoice",
            "invoice_date": fields.Date.today(),
            "invoice_line_ids": invoice_lines,
        }
        invoice_id = self.env["account.move"].sudo().create(data)
        invoice_id.tenancy_id = self.tenancy_id.id
        if invoice_post_type == "automatically":
            invoice_id.action_post()
        rent_invoice = {
            "tenancy_id": self.tenancy_id.id,
            "type": "maintenance",
            "amount": self.price,
            "invoice_date": fields.Date.today(),
            "description": "New Service",
            "rent_invoice_id": invoice_id.id,
        }
        self.env["rent.invoice"].create(rent_invoice)

class TenancyFinalMaintenanceLine(models.Model):
    _name = "tenancy.final.maintenance.line"
    _description = "Final Statement — Maintenance/Repair Charge"

    tenancy_id = fields.Many2one("tenancy.details", ondelete="cascade")
    product_id = fields.Many2one("product.product", string="Item", required=True)
    description = fields.Char(string="Description")
    amount = fields.Monetary(string="Amount", required=True)
    currency_id = fields.Many2one(related="tenancy_id.currency_id")


class TenancyFinalUtilityLine(models.Model):
    _name = "tenancy.final.utility.line"
    _description = "Final Statement — Utility Charge"

    tenancy_id = fields.Many2one("tenancy.details", ondelete="cascade")
    utility_type = fields.Selection(
        [("electricity", "Electricity"), ("water", "Water")], required=True
    )
    meter_no = fields.Char(string="Meter No.")
    closing_reading = fields.Float(string="Closing Reading")
    closing_date = fields.Date(string="Closing Date")
    amount = fields.Monetary(string="Amount", required=True)
    currency_id = fields.Many2one(related="tenancy_id.currency_id")


# Agreement Template
class AgreementTemplate(models.Model):
    """Agreement Template"""

    _name = "agreement.template"
    _description = "Agreement Template"

    name = fields.Char(string="Title", translate=True)
    company_id = fields.Many2one(
        "res.company", string="Company", default=lambda self: self.env.company
    )
    template_type = fields.Selection(
        [("text", "Text Only"), ("printable", "Printable Format")],
        string="Template Type",
        default="text",
        required=True,
        help="Text Only uses the plain HTML agreement field. Printable Format "
             "renders a designed PDF via the linked Report.",
    )
    report_id = fields.Many2one(
        "ir.actions.report",
        string="Printable Report",
        domain="[('model', '=', model)]",
        help="Report used to generate the printable version of this template.",
    )
    agreement = fields.Html(string="Agreement")
    template_variable_ids = fields.One2many(
        "agreement.template.variables",
        "template_id",
        compute="_compute_agreement_variable_ids",
        store=True,
        precompute=True,
        readonly=False,
        copy=False,
    )
    model = fields.Char(string="Model", default="tenancy.details")

    @api.depends("agreement")
    def _compute_agreement_variable_ids(self):
        """Get Variable Bases on agreement variable"""
        for rec in self:
            delete_var = self.env["agreement.template.variables"]
            keep_var = self.env["agreement.template.variables"]
            created_var = []
            body_var = set(re.findall(r"{{[1-9][0-9]*}}", rec.agreement or ""))
            existing_var = rec.template_variable_ids
            new_var = [
                var_name
                for var_name in body_var
                if var_name not in existing_var.mapped("name")
            ]
            deleted_var = existing_var.filtered(lambda var: var.name not in body_var)
            created_var += [{"name": var_name} for var_name in set(new_var)]
            delete_var += deleted_var
            keep_var += existing_var - deleted_var
            rec.template_variable_ids = [
                (3, to_remove.id) for to_remove in delete_var
            ] + [(0, 0, vals) for vals in created_var]


# Agreement Variable
class AgreementTemplateVariable(models.Model):
    """Agreement template variables"""

    _name = "agreement.template.variables"
    _description = "Agreement Variable Templates"
    _order = "name"

    template_id = fields.Many2one("agreement.template", string="Agreement Template")
    name = fields.Char(string="Body")
    model = fields.Char(related="template_id.model")
    field_type = fields.Selection(
        [("free_text", "Free Text"), ("field", "Field of Model")],
        string="Type",
        default="free_text",
    )
    field_name = fields.Char(string="Field")
    demo = fields.Char(string="Demo", default="Demo Value")
    free_text = fields.Char(string="Free Text")


# Extra Services Lines
class ContractExtraServiceLine(models.Model):
    """Tenancy Extra Service Line"""

    _name = "contract.extra.service.line"
    _description = "Contract Extra Service Line"

    contract_id = fields.Many2one(comodel_name="tenancy.details")
    service_id = fields.Many2one(
        comodel_name="product.product", domain="[('is_extra_service_product','=',True)]"
    )
    currency_id = fields.Many2one(
        "res.currency", string="Currency", related="company_id.currency_id"
    )
    company_id = fields.Many2one(
        "res.company", string="Company", default=lambda self: self.env.company
    )
    price = fields.Monetary(string="Price")
    invoice_created = fields.Boolean()
    invoice_id = fields.Many2one(comodel_name="account.move", string="Invoice")

    @api.onchange("service_id")
    def _onchange_service_price(self):
        """Onchange service price"""
        for rec in self:
            rec.price = rec.service_id.lst_price
