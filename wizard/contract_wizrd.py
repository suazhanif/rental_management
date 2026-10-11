# -*- coding: utf-8 -*-
# Copyright 2026-Baramej®.
# Part of Baramej®. See LICENSE file for full copyright and licensing details.
from dateutil.relativedelta import relativedelta
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ContractWizard(models.TransientModel):
    """Property Rent Contract Creation"""

    _name = "contract.wizard"
    _description = "Create Contract of rent in property"

    # Company & Currency
    currency_id = fields.Many2one(
        "res.currency", string="Currency", related="company_id.currency_id"
    )
    company_id = fields.Many2one(
        "res.company", string="Company", default=lambda self: self.env.company
    )

    # Customer Details
    customer_id = fields.Many2one(
        "res.partner", string="Customer", domain=[("user_type", "=", "customer")]
    )
    customer_phone = fields.Char(
        related="customer_id.phone", store=True, readonly=False
    )
    customer_email = fields.Char(
        related="customer_id.email", store=True, readonly=False
    )

    # Property Details
    property_id = fields.Many2one("property.details", string="Property")
    rent_unit = fields.Selection(
        [("Day", "Day"), ("Month", "Month"), ("Year", "Year")],
        default="Month",
        string="Rent Unit",
    )
    total_rent = fields.Monetary(string="Related")

    # Deposit
    is_any_deposit = fields.Boolean(string="Deposit")
    deposit_amount = fields.Monetary(string="Security Deposit")

    # Utility Services
    is_extra_service = fields.Boolean(
        related="property_id.is_extra_service", string="Any Extra Services"
    )
    extra_service_ids = fields.One2many(related="property_id.extra_service_ids")
    services = fields.Text(
        string="Utility Services", compute="_compute_services", translate=True
    )
    extra_service_invoice = fields.Selection(
        [("merge", "Merge With Installment"), ("separate", "Separate")], default="merge"
    )

    # Added Services
    is_added_services = fields.Boolean(string="Is Extra Services")
    added_service_ids = fields.One2many(
        comodel_name="contract.service.line", inverse_name="rent_contract_id"
    )
    added_service_invoice = fields.Selection(
        [("merge", "Merge With Installment"), ("separate", "Separate")], default="merge"
    )

    # Maintenance
    is_any_maintenance = fields.Boolean(
        string="Any Maintenance", related="property_id.is_maintenance_service"
    )
    maintenance_rent_type = fields.Selection(
        related="property_id.maintenance_rent_type"
    )
    total_maintenance = fields.Monetary(related="property_id.total_maintenance")
    maintenance_service_invoice = fields.Selection(
        [("merge", "Merge With Installment"), ("separate", "Separate")], default="merge"
    )

    # Contract Detail
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
        "contract.duration", string="Durations", compute="compute_durations"
    )
    duration_id = fields.Many2one(
        "contract.duration", string="Duration", domain="[('id','in',duration_ids)]"
    )
    start_date = fields.Date(string="Start Date")
    end_date = fields.Date(string="End Date", compute="_compute_end_date", store=True)
    total_days = fields.Integer(compute="_compute_total_days")
    duration_type = fields.Selection(
        [("by_duration", "By Duration"), ("by_date", "By Date")], default="by_duration"
    )
    duration_end_date = fields.Date()

    # Broker Details
    is_any_broker = fields.Boolean(string="Any Broker?")
    broker_id = fields.Many2one(
        "res.partner", string="Broker", domain=[("user_type", "=", "broker")]
    )
    rent_type = fields.Selection(
        [("once", "First Month"), ("e_rent", "All Month")], string="Brokerage Type"
    )
    commission_type = fields.Selection(
        [("f", "Fix"), ("p", "Percentage")], string="Commission Type"
    )
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
    broker_commission = fields.Monetary(string="Commission")
    broker_commission_percentage = fields.Float(string="Percentage")

    # Leads
    from_inquiry = fields.Boolean("From Enquiry")
    lead_id = fields.Many2one(
        "crm.lead", string="Enquiry", domain="[('property_id','=',property_id)]"
    )
    inquiry_id = fields.Many2one("tenancy.inquiry", string="Inquiry")
    note = fields.Text(string="Note", translate=True)

    # Agreement
    agreement = fields.Html(string="Agreement")
    agreement_template_id = fields.Many2one(
        "agreement.template",
        string="Agreement Template",
        domain="[('company_id','=',company_id)]",
    )

    # Instalment Item
    installment_item_id = fields.Many2one("product.product", string="Installment Item")
    deposit_item_id = fields.Many2one("product.product", string="Deposit Item")
    broker_item_id = fields.Many2one("product.product", string="Broker Item")
    maintenance_item_id = fields.Many2one("product.product", string="Maintenance Item")

    # Taxes
    instalment_tax = fields.Boolean(string="Taxes on Installment ?")
    deposit_tax = fields.Boolean(string="Taxes on Deposit ?")
    service_tax = fields.Boolean(string="Taxes on Services ?")
    tax_ids = fields.Many2many("account.tax", string="Taxes")

    # Terms & Conditions
    term_condition = fields.Html(string="Term and Condition")

    # Extend Contract
    is_contract_extend = fields.Boolean(string="Extend Contract")

    # Rent Increment
    is_rent_increment = fields.Boolean(string="Is Rent Increment ?")
    previous_rent = fields.Monetary(string="Previous Rent")
    current_rent_type = fields.Selection(related="property_id.pricing_type")
    price_per_area = fields.Monetary(related="property_id.price_per_area")
    current_area = fields.Float(related="property_id.total_area")
    measure_unit = fields.Selection(related="property_id.measure_unit")
    rent_increment_type = fields.Selection(
        [("fix", "Fix Amount"), ("percentage", "Percentage")],
        string="Increment Type",
        default="fix",
    )
    increment_percentage = fields.Float(string="Increment(%)", default=1)
    increment_amount = fields.Monetary(string="Increment Amount")
    incremented_rent = fields.Monetary(
        string="Final Rent", compute="compute_increment_rent"
    )
    incremented_rent_area = fields.Monetary(
        string="Increment Rent(Area)", compute="compute_increment_rent"
    )

    # Multi contract period
    is_contract_available = fields.Boolean(compute="_compute_is_contract_available")
    contract_desc = fields.Text(
        compute="_compute_is_contract_available", string="Draft Contract"
    )

    # Available Payment Term
    available_payment_term = fields.Char(compute="_compute_available_payment_term")

    # Penalty Details
    is_penalty_visible = fields.Boolean()
    is_penalty_applied = fields.Boolean(string="Is Any Penalty?")
    penalty_days_after_due = fields.Integer(
        string="Apply Penalty After (Days)",
        default=lambda self: (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("rental_management.penalty_days_after_due_for_rent_contract")
            or 5
        ),
    )
    penalty_percentage = fields.Integer(
        string="Percentage ",
        default=lambda self: (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("rental_management.penalty_percentage_for_rent_contract")
            or 0
        ),
    )

    # Utility Readings
    water_reading = fields.Float("Water Reading (m³)", required=True)
    water_reading_date = fields.Datetime("Water Reading Date/Time", required=True)
    electricity_reading = fields.Float("Electricity Reading (kWh)", required=True)
    electricity_reading_date = fields.Datetime(
        "Electricity Reading Date/Time", required=True
    )
    utility_water_account_no = fields.Char(
        related="property_id.utility_water_account_no", string="Water Account No."
    )
    utility_electricity_account_no = fields.Char(
        related="property_id.utility_electricity_account_no",
        string="Electricity Account No.",
    )

    # Default Get
    @api.model
    def default_get(self, fields_list):
        """Default get"""
        res = super(ContractWizard, self).default_get(fields_list)
        active_id = self.env.context.get("active_id")
        active_model = self.env.context.get("active_model")
        default_installment_item = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("rental_management.account_installment_item_id")
        )
        default_broker_item = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("rental_management.account_broker_item_id")
        )
        default_deposit_item = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("rental_management.account_deposit_item_id")
        )
        default_maintenance_item = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("rental_management.account_maintenance_item_id")
        )
        if active_model == "property.details":
            property_id = self.env["property.details"].browse(active_id)
            res["installment_item_id"] = (
                int(default_installment_item)
                if default_installment_item
                else self.env.ref("rental_management.property_product_1").id
            )
            res["deposit_item_id"] = (
                int(default_deposit_item)
                if default_deposit_item
                else self.env.ref("rental_management.property_product_2").id
            )
            res["broker_item_id"] = (
                int(default_broker_item)
                if default_broker_item
                else self.env.ref("rental_management.property_product_3").id
            )
            res["maintenance_item_id"] = (
                int(default_maintenance_item)
                if default_maintenance_item
                else self.env.ref("rental_management.property_product_4").id
            )
            res["property_id"] = active_id
            res["rent_unit"] = property_id.rent_unit
            res["total_rent"] = property_id.price
            if property_id.rent_unit == "Day":
                res["payment_term"] = "full_payment"
            if property_id.rent_unit == "Year":
                res["payment_term"] = "year"
            # Electricity/Water Readings
            if property_id:
                if "water_reading" in fields_list:
                    res["water_reading"] = (
                        property_id.water_readings_id.name
                        if property_id.water_readings_id
                        else 0
                    )
                if "electricity_reading" in fields_list:
                    res["electricity_reading"] = (
                        property_id.electricity_readings_id.name
                        if property_id.electricity_readings_id
                        else 0
                    )
                # Also set the dates if you want them defaulted to now
                if "water_reading_date" in fields_list:
                    res["water_reading_date"] = fields.Datetime.now()
                if "electricity_reading_date" in fields_list:
                    res["electricity_reading_date"] = fields.Datetime.now()
        if active_model == "tenancy.details":
            tenancy_id = self.env["tenancy.details"].browse(active_id)
            res["property_id"] = tenancy_id.property_id.id
            res["customer_id"] = tenancy_id.tenancy_id.id
            res["start_date"] = tenancy_id.end_date + relativedelta(days=1)
            res["is_contract_extend"] = True
            res["installment_item_id"] = tenancy_id.installment_item_id.id
            res["deposit_item_id"] = tenancy_id.deposit_item_id.id
            res["broker_item_id"] = tenancy_id.broker_item_id.id
            res["maintenance_item_id"] = tenancy_id.maintenance_item_id.id
            res["is_any_deposit"] = tenancy_id.is_any_deposit
            res["deposit_amount"] = tenancy_id.deposit_amount
            res["rent_unit"] = tenancy_id.rent_unit
            res["total_rent"] = tenancy_id.total_rent
            # Broker Detail
            res["is_any_broker"] = tenancy_id.is_any_broker
            res["broker_id"] = tenancy_id.broker_id.id
            res["commission_from"] = tenancy_id.commission_from
            res["rent_type"] = tenancy_id.rent_type
            res["commission_type"] = tenancy_id.commission_type
            res["broker_commission_percentage"] = (
                tenancy_id.broker_commission_percentage
            )
            res["broker_commission"] = tenancy_id.broker_commission
            res["term_condition"] = tenancy_id.term_condition
            res["previous_rent"] = tenancy_id.total_rent

            # Electricity/Water Readings
            property_id = tenancy_id.property_id
            if property_id:
                if "water_reading" in fields_list:
                    res["water_reading"] = (
                        property_id.water_readings_id.name
                        if property_id.water_readings_id
                        else 0
                    )
                if "electricity_reading" in fields_list:
                    res["electricity_reading"] = (
                        property_id.electricity_readings_id.name
                        if property_id.electricity_readings_id
                        else 0
                    )
                # Also set the dates if you want them defaulted to now
                if "water_reading_date" in fields_list:
                    res["water_reading_date"] = fields.Datetime.now()
                if "electricity_reading_date" in fields_list:
                    res["electricity_reading_date"] = fields.Datetime.now()
        is_penalty_visible = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("rental_management.is_penalty_applied")
        )
        res["is_penalty_visible"] = is_penalty_visible
        return res

    @api.constrains("start_date", "duration_type")
    def _check_end_date(self):
        """Check that end date should be greate than start date"""
        for rec in self:
            if (
                rec.duration_type == "by_date"
                and rec.start_date
                and rec.end_date
                and rec.end_date < rec.start_date
            ):
                raise ValidationError(_("End date should be greater than start date"))

    @api.constrains(
        "total_rent",
        "deposit_amount",
        "broker_commission",
        "broker_commission_percentage",
    )
    def _check_values_is_not_negative(self):
        """Raise Validation if value is negative"""
        for rec in self:
            if rec.total_rent and rec.total_rent < 0:
                raise ValidationError(_("Rent must be zero or greater"))
            if rec.deposit_amount and rec.deposit_amount < 0:
                raise ValidationError(_("Security deposit must be zero or greater"))
            if rec.broker_commission and rec.broker_commission < 0:
                raise ValidationError(_("Commission must be zero or greater"))
            if (
                rec.broker_commission_percentage
                and rec.broker_commission_percentage < 0
            ):
                raise ValidationError(_("Percentage must be zero or greater"))

    # Compute
    # End Date
    @api.depends(
        "start_date",
        "duration_id",
        "duration_id.month",
        "payment_term",
        "rent_unit",
        "duration_type",
        "duration_end_date",
    )
    def _compute_end_date(self):
        """Compute end date"""
        for rec in self:
            end_date = None
            if (
                rec.duration_type == "by_duration"
                and rec.duration_id
                and rec.payment_term
                and rec.rent_unit
                and rec.start_date
            ):
                if rec.rent_unit == "Day":
                    end_date = (
                        rec.start_date
                        + relativedelta(days=rec.duration_id.month)
                        - relativedelta(days=1)
                    )
                elif rec.rent_unit == "Year":
                    end_date = (
                        rec.start_date
                        + relativedelta(years=rec.duration_id.month)
                        - relativedelta(days=1)
                    )
                else:
                    if rec.payment_term == "year":
                        end_date = (
                            rec.start_date
                            + relativedelta(years=rec.duration_id.month)
                            - relativedelta(days=1)
                        )
                    else:
                        end_date = (
                            rec.start_date
                            + relativedelta(months=rec.duration_id.month)
                            - relativedelta(days=1)
                        )
            if rec.duration_type == "by_date":
                end_date = rec.duration_end_date
            rec.end_date = end_date

    # Domain
    @api.depends("payment_term", "rent_unit")
    def compute_durations(self):
        """Compute duration bases on rent unit"""
        for rec in self:
            duration_record = self.env["contract.duration"].sudo()
            ids = []
            if rec.rent_unit == "Day":
                domain = [("rent_unit", "=", "Day")]
                ids = duration_record.search(domain).mapped("id")
            if rec.rent_unit == "Year":
                domain = [("rent_unit", "=", "Year")]
                ids = duration_record.search(domain).mapped("id")
            if rec.rent_unit == "Month":
                if rec.payment_term == "bi_monthly":
                    domain = [("month", ">=", 2), ("rent_unit", "=", "Month")]
                    ids = duration_record.search(domain).mapped("id")
                elif rec.payment_term == "quarterly":
                    domain = [("month", ">=", 3), ("rent_unit", "=", "Month")]
                    ids = duration_record.search(domain).mapped("id")
                elif rec.payment_term == "half_year":
                    domain = [("month", ">=", 6), ("rent_unit", "=", "Month")]
                    ids = duration_record.search(domain).mapped("id")
                elif rec.payment_term == "year":
                    domain = [("rent_unit", "=", "Year")]
                    ids = duration_record.search(domain).mapped("id")
                else:
                    domain = [("month", ">", 0), ("rent_unit", "=", "Month")]
                    ids = duration_record.search(domain).mapped("id")
            rec.duration_ids = ids

    # Check Contract Period Available
    @api.depends("start_date", "end_date", "property_id")
    def _compute_is_contract_available(self):
        """Check Contract Period Available between start date and end date."""
        for rec in self:
            availability = False
            desc = ""
            if rec.start_date and rec.end_date:
                date_domain = [
                    ("start_date", "<=", rec.end_date),
                    ("end_date", ">", rec.start_date),
                ]
                domain = [
                    (
                        "contract_type",
                        "not in",
                        ["expire_contract", "cancel_contract", "close_contract"],
                    ),
                    ("property_id", "=", rec.property_id.id),
                ]
                rent_record = (
                    self.env["tenancy.details"].sudo().search(date_domain + domain)
                )
                draft_contract_record = rent_record.filtered(
                    lambda line: line.contract_type == "new_contract"
                )
                if draft_contract_record:
                    for data in draft_contract_record:
                        desc = (
                            desc
                            + f"{data.tenancy_seq} : {data.start_date} to {data.end_date}"
                            + "\n"
                        )
                if not rent_record.filtered(
                    lambda line: line.id not in draft_contract_record.ids
                ):
                    availability = True

            rec.is_contract_available = availability
            rec.contract_desc = desc

    @api.depends("rent_unit")
    def _compute_available_payment_term(self):
        """Get available payment term"""
        for rec in self:
            available_payment_term = None
            if rec.rent_unit == "Month":
                available_payment_term = (
                    "Available Payment Term  : Monthly, Bi-Monthly, "
                    + "Quarterly, Half year, Full Payment"
                )
            elif rec.rent_unit == "Year":
                available_payment_term = (
                    "Available Payment Term  : Yearly, Full Payment"
                )
            elif rec.rent_unit == "Day":
                available_payment_term = (
                    "Available Payment Term  : Monthly, Bi-Monthly, "
                    + "Quarterly, Half Year, Yearly, Daily, Full Payment"
                )
            rec.available_payment_term = available_payment_term

    @api.depends("start_date", "end_date")
    def _compute_total_days(self):
        """Compute total days"""
        for rec in self:
            total_days = 0
            if rec.start_date and rec.end_date:
                total_days = (rec.end_date - rec.start_date).days + 1
            rec.total_days = total_days if total_days >= 0 else 0

    # Onchange
    # Payment Term
    @api.onchange("payment_term")
    def onchange_payment_term(self):
        """Empty duration_id on payment term"""
        for rec in self:
            rec.duration_id = False

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

    # Agreement
    @api.onchange("agreement_template_id")
    def _onchange_agreement_template_id(self):
        """Get agreement bases on agreement template"""
        for rec in self:
            rec.agreement = rec.agreement_template_id.agreement

    # Leads Info
    @api.onchange("lead_id")
    def _onchange_tenancy_inquiry(self):
        """Property tenancy inquiry"""
        for rec in self:
            if rec.from_inquiry and rec.lead_id:
                rec.note = rec.lead_id.description
                rec.customer_id = rec.lead_id.partner_id.id

    @api.onchange("duration_type")
    def _onchange_duration_type(self):
        """For duration 'By Day' rent unit should be Day"""
        for rec in self:
            if rec.duration_type == "by_date":
                rec.rent_unit = "Day"

    # Compute
    # Services

    @api.depends("property_id")
    def _compute_services(self):
        """Compute services"""
        for rec in self:
            services = ""
            if rec.property_id and rec.is_extra_service:
                for data in rec.property_id.extra_service_ids:
                    services += (
                        f"{data.service_id.name}[{'Once' if data.service_type == 'once' else 'Recurring'}] "
                        f"- {rec.currency_id.symbol} {data.price}\n"
                    )
            rec.services = services

    # Extend Increment Time
    @api.depends(
        "total_rent",
        "increment_percentage",
        "increment_amount",
        "rent_increment_type",
        "price_per_area",
        "current_rent_type",
        "current_area",
    )
    def compute_increment_rent(self):
        """Compute incremented rent"""
        for rec in self:
            amount = 0.0
            incremented_rent_area = 0.0
            calculate_amount = 0.0
            if rec.current_rent_type == "fixed":
                calculate_amount = self.total_rent
            if rec.current_rent_type == "area_wise":
                calculate_amount = self.price_per_area
            if rec.rent_increment_type == "fix":
                amount = rec.increment_amount + calculate_amount
            elif rec.rent_increment_type == "percentage":
                amount = (
                    calculate_amount * rec.increment_percentage / 100 + calculate_amount
                )
            if rec.current_rent_type == "area_wise":
                incremented_rent_area = amount
                area_wise_total_rent = amount * rec.current_area
                amount = area_wise_total_rent
            rec.incremented_rent = amount
            rec.incremented_rent_area = incremented_rent_area

    def _create_property_readings(self, contract_id):
        """Create water, electricity reading records linked to property and contract."""
        self.ensure_one()
        if not self.property_id:
            return

        # Create water reading
        if self.water_reading_date:
            self.env["property.water.readings"].sudo().create(
                {
                    "name": self.water_reading,
                    "property_details_id": self.property_id.id,
                    "reference": contract_id.tenancy_seq,
                    "reading_date": self.water_reading_date,
                }
            )

        # Create electricity reading
        if self.electricity_reading_date:
            self.env["property.electricity.readings"].sudo().create(
                {
                    "name": self.electricity_reading,
                    "property_details_id": self.property_id.id,
                    "reference": contract_id.tenancy_seq,
                    "reading_date": self.electricity_reading_date,
                }
            )

    # Contract Creation
    def contract_action(self):
        """Process rent contract"""
        if self.water_reading <= 0 or self.electricity_reading <= 0:
            message = {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "type": "info",
                    "title": ("You must record water and electricity readings."),
                    "sticky": False,
                },
            }
            return message

        active_model = self.env.context.get("active_model")
        active_id = self.env.context.get("active_id")
        self.customer_id.user_type = "customer"
        if active_model == "tenancy.details":
            tenancy_id = self.env["tenancy.details"].browse(active_id)
            tenancy_id.contract_type = "close_contract"
            tenancy_id.close_contract_state = True
        if self.is_contract_extend and self.is_rent_increment:
            self.action_process_rent_increment()
        record = self.get_contract_info()
        # Utilities
        service_line = []
        if self.property_id.is_extra_service:
            for data in self.property_id.extra_service_ids:
                service_line.append(
                    (
                        0,
                        0,
                        {
                            "service_id": data.service_id.id,
                            "service_type": data.service_type,
                            "from_contract": True,
                            "price": data.price,
                        },
                    )
                )
        if service_line:
            record["extra_services_ids"] = service_line
            record["extra_service_invoice"] = self.extra_service_invoice
        # Extra Services
        if self.is_added_services and self.added_service_ids:
            record["is_added_services"] = self.is_added_services
            record["added_service_ids"] = [
                (0, 0, {"service_id": data.service_id.id, "price": data.price})
                for data in self.added_service_ids
            ]
            record["added_service_invoice"] = self.added_service_invoice
        # Payment Term : Full Payment
        if self.payment_term == "full_payment":
            record["last_invoice_payment_date"] = fields.Date.today()
            record["active_contract_state"] = True
            record["contract_type"] = "running_contract"
            contract_id = self.env["tenancy.details"].create(record)
            contract_id._onchange_agreement_template_id()
            self._create_property_readings(contract_id)
            if contract_id.is_any_broker:
                contract_id.action_broker_invoice()
            # Full Payment Invoice
            if self.duration_type == "by_duration":
                self.action_create_full_payment_invoice(contract_id=contract_id)
            if self.duration_type == "by_date":
                self._process_by_dated_full_payment(contract_id=contract_id)
            self.customer_id.is_tenancy = True
            self.property_id.write({"stage": "on_lease"})
            if active_model == "tenancy.details":
                old_tenancy_id = self.env["tenancy.details"].browse(active_id)
                old_tenancy_id.extended = True
                old_tenancy_id.extend_ref = contract_id.tenancy_seq
                old_tenancy_id.new_contract_id = contract_id.id
                contract_id.is_extended = True
                contract_id.extend_from = old_tenancy_id.tenancy_seq
            return {
                "type": "ir.actions.act_window",
                "name": "Contract",
                "res_model": "tenancy.details",
                "res_id": contract_id.id,
                "view_mode": "form,list",
                "target": "current",
            }
        if self.rent_unit == "Year" and self.payment_term not in [
            "year",
            "full_payment",
        ]:
            message = {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "type": "info",
                    "title": (
                        "For Rent unit Year, please select a payment term: either 'Yearly' or 'Full Payment'."
                    ),
                    "sticky": False,
                },
            }
            return message
        if self.rent_unit == "Month" and self.payment_term in ["daily", "year"]:
            message = {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "type": "info",
                    "title": (
                        _(
                            "For Rent unit Month, please select a payment"
                            " term: either 'Monthly', 'Bi-Monthly', 'Quarterly', "
                            "or 'Full Payment'."
                        )
                    ),
                    "sticky": False,
                },
            }
            return message
        # Payment Term : Monthly Quarterly, Year, Daily
        if self.payment_term != "full_payment":
            record["contract_type"] = "new_contract"
            contract_id = self.env["tenancy.details"].create(record)
            contract_id._onchange_agreement_template_id()
            self._create_property_readings(contract_id)
            self.customer_id.is_tenancy = True
            self.property_id.write({"stage": "on_lease"})
            if active_model == "tenancy.details":
                old_tenancy_id = self.env["tenancy.details"].browse(active_id)
                old_tenancy_id.extended = True
                old_tenancy_id.extend_ref = contract_id.tenancy_seq
                old_tenancy_id.new_contract_id = contract_id.id
                contract_id.is_extended = True
                contract_id.extend_from = old_tenancy_id.tenancy_seq
            return {
                "type": "ir.actions.act_window",
                "name": "Contract",
                "res_model": "tenancy.details",
                "res_id": contract_id.id,
                "view_mode": "form,list",
                "target": "current",
            }

    @api.constrains("is_contract_extend")
    def check_contract_start_date(self):
        """Start date must be greater than previous contract end date in extende contract"""
        for rec in self:
            if rec.is_contract_extend:
                active_model = self.env.context.get("active_model")
                active_id = self.env.context.get("active_id")
                if active_model == "tenancy.details":
                    tenancy_id = self.env["tenancy.details"].sudo().browse(active_id)
                    if rec.start_date < tenancy_id.end_date:
                        raise ValidationError(
                            _(
                                "Contract start date must be greater than previous contract end date"
                            )
                        )

    def get_contract_info(self):
        """Prepare contract data"""
        data = {
            # Customer
            "tenancy_id": self.customer_id.id,
            # Property
            "property_id": self.property_id.id,
            "total_rent": self.get_total_rent(),
            "final_rent_unit": self.rent_unit,
            # Broker
            "is_any_broker": self.is_any_broker,
            "broker_id": self.broker_id.id,
            "rent_type": self.rent_type,
            "commission_type": self.commission_type,
            "broker_commission": self.broker_commission,
            "broker_commission_percentage": self.broker_commission_percentage,
            "commission_from": self.commission_from,
            # Contract Details
            "duration_type": self.duration_type,
            "duration_end_date": self.duration_end_date,
            "duration_id": self.duration_id.id,
            "start_date": self.start_date,
            "invoice_start_date": self.start_date,
            "payment_term": self.payment_term,
            # Deposit
            "is_any_deposit": self.is_any_deposit,
            "deposit_amount": self.deposit_amount,
            # agreement
            "agreement": self.agreement,
            "agreement_template_id": self.agreement_template_id.id,
            # Installment Item
            "installment_item_id": self.installment_item_id.id,
            "broker_item_id": self.broker_item_id.id,
            "deposit_item_id": self.deposit_item_id.id,
            "maintenance_item_id": self.maintenance_item_id.id,
            # Taxes
            "tax_ids": self.tax_ids.ids,
            "instalment_tax": self.instalment_tax,
            "service_tax": self.service_tax,
            "deposit_tax": self.deposit_tax,
            # Terms Conditions
            "term_condition": self.term_condition,
            # Maintenance
            "maintenance_service_invoice": self.maintenance_service_invoice,
            # Penalty
            "is_penalty_applied": self.is_penalty_applied,
            "penalty_days_after_due": self.penalty_days_after_due,
            "penalty_percentage": self.penalty_percentage,
        }
        return data

    def action_create_full_payment_invoice(self, contract_id):
        """Process full payment contract & invoice"""
        invoice_post_type = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("rental_management.invoice_post_type")
        )
        service_invoice_line = []
        desc = ""
        full_payment_record = {
            "product_id": self.installment_item_id.id,
            "name": "Full Payment of " + self.property_id.name,
            "quantity": 1,
            "price_unit": self.get_total_rent() * self.duration_id.month,
            "tax_ids": self.tax_ids.ids if self.instalment_tax else False,
        }
        service_invoice_line.append((0, 0, full_payment_record))
        if self.is_any_maintenance and self.maintenance_service_invoice == "merge":
            service_invoice_line.append(
                (
                    0,
                    0,
                    {
                        "product_id": self.maintenance_item_id.id,
                        "name": "Maintenance of " + self.property_id.name,
                        "quantity": 1,
                        "price_unit": (
                            self.total_maintenance
                            if self.maintenance_rent_type == "once"
                            else self.total_maintenance * self.duration_id.month
                        ),
                    },
                )
            )
        if self.property_id.is_extra_service and self.extra_service_invoice == "merge":
            for line in self.property_id.extra_service_ids:
                if line.service_type == "once":
                    desc = (
                        "Service Type : Once" + "\n"
                        "Service : " + str(line.service_id.name)
                    )
                if line.service_type == "monthly":
                    desc = (
                        "Service Type : Recurring" + "\n"
                        "Service : " + str(line.service_id.name)
                    )
                service_invoice_line.append(
                    (
                        0,
                        0,
                        {
                            "product_id": line.service_id.id,
                            "name": desc,
                            "quantity": (
                                1
                                if line.service_type == "once"
                                else self.duration_id.month
                            ),
                            "price_unit": line.price,
                            "tax_ids": self.tax_ids.ids if self.service_tax else False,
                        },
                    )
                )
        if (
            self.is_added_services
            and self.added_service_ids
            and self.added_service_invoice == "merge"
        ):
            for line in self.added_service_ids:
                service_invoice_line.append(
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
            self._process_separate_added_services(contract_id=contract_id)
        invoice_id = (
            self.env["account.move"]
            .sudo()
            .create(
                {
                    "partner_id": self.customer_id.id,
                    "move_type": "out_invoice",
                    "invoice_date": contract_id.invoice_start_date,
                    "invoice_line_ids": service_invoice_line,
                    "tenancy_id": contract_id.id,
                }
            )
        )
        if invoice_post_type == "automatically":
            invoice_id.action_post()
        #  Rent Invoice Entry
        self.env["rent.invoice"].create(
            {
                "tenancy_id": contract_id.id,
                "type": "full_rent",
                "invoice_date": contract_id.invoice_start_date,
                "amount": invoice_id.amount_total,
                "description": "Full Payment Of Rent",
                "rent_invoice_id": invoice_id.id,
                "rent_amount": invoice_id.amount_total,
            }
        )
        # Separate Deposit Invoice
        contract_id._create_deposit_invoice()
        if self.is_any_maintenance and self.maintenance_service_invoice == "separate":
            self._process_separate_invoices(contract_id=contract_id, maintenance=True)
        if self.is_extra_service and self.extra_service_invoice == "separate":
            self._process_separate_invoices(contract_id=contract_id, utility=True)
        contract_id.action_send_active_contract()

    def action_process_rent_increment(self):
        """Process rent increment"""
        active_id = self.env.context.get("active_id")
        tenancy_id = self.env["tenancy.details"].browse(active_id)
        if self.property_id.pricing_type == "fixed":
            self.property_id.write({"price": self.incremented_rent})
        if self.property_id.pricing_type == "area_wise":
            self.property_id.write({"price_per_area": self.incremented_rent_area})
            self.property_id.onchange_fix_area_price()
        self.env["increment.history"].sudo().create(
            {
                "contract_ref": tenancy_id.tenancy_seq,
                "property_id": self.property_id.id,
                "rent_type": self.property_id.pricing_type,
                "rent_increment_type": self.rent_increment_type,
                "increment_percentage": self.increment_percentage,
                "increment_amount": self.increment_amount,
                "incremented_rent": self.incremented_rent,
                "previous_rent": self.previous_rent,
            }
        )

    def get_total_rent(self):
        """Get total rent"""
        total_rent = self.total_rent
        if self.is_contract_extend and self.is_rent_increment:
            total_rent = self.incremented_rent
        return total_rent

    def _process_by_dated_full_payment(self, contract_id):
        """Process full payment for 'By Date'"""
        """By Dated : Full Payment Rent Invoice"""
        invoice_post_type = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("rental_management.invoice_post_type")
        )
        delta = self.duration_end_date - self.start_date
        invoice_lines = [
            (
                0,
                0,
                {
                    "product_id": self.installment_item_id.id,
                    "name": f"Full Payment : {self.start_date} to {self.duration_end_date}",
                    "quantity": 1,
                    "price_unit": self.get_total_rent() * (delta.days + 1),
                    "tax_ids": self.tax_ids.ids if self.instalment_tax else False,
                },
            )
        ]
        if self.is_any_maintenance and self.maintenance_service_invoice == "merge":
            invoice_lines.append(
                (
                    0,
                    0,
                    {
                        "product_id": self.maintenance_item_id.id,
                        "name": "Maintenance of " + self.property_id.name,
                        "quantity": 1
                        if self.property_id.maintenance_rent_type == "once"
                        else (delta.days + 1),
                        "price_unit": self.total_maintenance,
                    },
                )
            )
        if self.is_extra_service and self.extra_service_invoice == "merge":
            for line in self.property_id.extra_service_ids:
                service_type = "Once" if line.service_type == "once" else "Recurring"
                invoice_lines.append(
                    (
                        0,
                        0,
                        {
                            "product_id": line.service_id.id,
                            "name": f"Service Type : {service_type} - {line.service_id.name}",
                            "quantity": 1
                            if line.service_type == "once"
                            else (delta.days + 1),
                            "price_unit": line.price,
                            "tax_ids": self.tax_ids.ids if self.service_tax else False,
                        },
                    )
                )
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
                            "tax_ids": False,
                        },
                    )
                )
        if (
            self.is_added_services
            and self.added_service_ids
            and self.added_service_invoice == "separate"
        ):
            self._process_separate_added_services(contract_id=contract_id)
        invoice_id = (
            self.env["account.move"]
            .sudo()
            .create(
                {
                    "partner_id": self.customer_id.id,
                    "move_type": "out_invoice",
                    "invoice_date": contract_id.invoice_start_date,
                    "invoice_line_ids": invoice_lines,
                    "tenancy_id": contract_id.id,
                }
            )
        )
        if invoice_post_type == "automatically":
            invoice_id.action_post()
        self.env["rent.invoice"].sudo().create(
            {
                "tenancy_id": contract_id.id,
                "type": "full_rent",
                "invoice_date": contract_id.invoice_start_date,
                "amount": invoice_id.amount_total,
                "description": "Full Payment Of Rent",
                "rent_invoice_id": invoice_id.id,
                "rent_amount": invoice_id.amount_total,
            }
        )
        # Separate Deposit Invoice
        contract_id._create_deposit_invoice()
        if self.is_any_maintenance and self.maintenance_service_invoice == "separate":
            self._process_separate_invoices(contract_id=contract_id, maintenance=True)
        if self.is_extra_service and self.extra_service_invoice == "separate":
            self._process_separate_invoices(contract_id=contract_id, utility=True)
        contract_id.action_send_active_contract()

    def _process_separate_added_services(self, contract_id):
        invoice_lines = []
        for data in contract_id.added_service_ids:
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
                        "partner_id": self.customer_id.id,
                        "move_type": "out_invoice",
                        "invoice_date": contract_id.invoice_start_date,
                        "invoice_line_ids": invoice_lines,
                        "tenancy_id": contract_id.id,
                    }
                )
            )
            contract_id.added_service_ids.write({"invoice_id": invoice_id.id})

    def _process_separate_invoices(self, contract_id, maintenance=None, utility=None):
        """Process Utility and Maintenance Separate Invoices"""
        if self.rent_unit == "Day":
            qty = (self.end_date - self.start_date).days + 1
        else:
            qty = self.duration_id.month
        if maintenance:
            maintenance_invoice_id = self.env["account.move"].create(
                {
                    "partner_id": self.customer_id.id,
                    "move_type": "out_invoice",
                    "invoice_date": contract_id.invoice_start_date,
                    "tenancy_id": contract_id.id,
                    "invoice_line_ids": [
                        (
                            0,
                            0,
                            {
                                "product_id": self.maintenance_item_id.id,
                                "name": "Maintenance of " + self.property_id.name,
                                "quantity": 1
                                if self.property_id.maintenance_rent_type == "once"
                                else qty,
                                "price_unit": self.total_maintenance,
                            },
                        )
                    ],
                }
            )
            self.env["rent.invoice"].create(
                {
                    "tenancy_id": contract_id.id,
                    "type": "maintenance",
                    "invoice_date": contract_id.invoice_start_date,
                    "amount": maintenance_invoice_id.amount_total,
                    "description": "Maintenance of " + self.property_id.name,
                    "rent_invoice_id": maintenance_invoice_id.id,
                }
            )
        if utility:
            service_invoice_lines = []
            for line in self.property_id.extra_service_ids:
                service_type = "Once" if line.service_type == "once" else "Recurring"
                service_invoice_lines.append(
                    (
                        0,
                        0,
                        {
                            "product_id": line.service_id.id,
                            "name": f"Service Type : {service_type} - {line.service_id.name}",
                            "quantity": 1 if line.service_type == "once" else qty,
                            "price_unit": line.price,
                            "tax_ids": self.tax_ids.ids if self.service_tax else False,
                        },
                    )
                )
            service_invoice_id = self.env["account.move"].create(
                {
                    "partner_id": self.customer_id.id,
                    "move_type": "out_invoice",
                    "invoice_date": contract_id.invoice_start_date,
                    "tenancy_id": contract_id.id,
                    "invoice_line_ids": service_invoice_lines,
                }
            )
            self.env["rent.invoice"].create(
                {
                    "tenancy_id": contract_id.id,
                    "type": "other",
                    "invoice_date": contract_id.invoice_start_date,
                    "amount": service_invoice_id.amount_total,
                    "description": "Utility Services",
                    "rent_invoice_id": service_invoice_id.id,
                }
            )


class ContractServiceLine(models.TransientModel):
    """Contract Service Lines"""

    _name = "contract.service.line"
    _description = "Contract Service Line"

    rent_contract_id = fields.Many2one(comodel_name="contract.wizard")
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

    @api.constrains("price")
    def _check_price_is_not_negative(self):
        """Raise Validation if price is negative"""
        for rec in self:
            if rec.price and rec.price < 0:
                raise ValidationError(_("Price must be zero or greater"))

    @api.onchange("service_id")
    def _onchange_service_price(self):
        for rec in self:
            rec.price = rec.service_id.lst_price
