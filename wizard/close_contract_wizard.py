# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class CloseContractWizard(models.TransientModel):
    """Wizard to close rent contract with final readings and inspection"""

    _name = "close.contract.wizard"
    _description = "Close Contract Wizard"

    # Contract Reference
    contract_id = fields.Many2one("tenancy.details", string="Contract", required=True)

    # Property (related)
    property_id = fields.Many2one(
        related="contract_id.property_id", string="Property", readonly=True
    )

    # Tenant (related)
    tenant_id = fields.Many2one(
        related="contract_id.tenancy_id", string="Tenant", readonly=True
    )

    # Outstanding balance.  A pending balance does not block closure, but it
    # is shown on the wizard so the user knows what is left unpaid.
    currency_id = fields.Many2one(
        related="contract_id.currency_id", string="Currency", readonly=True
    )
    outstanding_amount = fields.Monetary(
        related="contract_id.remain_tenancy", string="Outstanding Amount", readonly=True
    )
    has_outstanding_amount = fields.Boolean(compute="_compute_has_outstanding_amount")

    @api.depends("outstanding_amount")
    def _compute_has_outstanding_amount(self):
        """Flag contracts that still have money due"""
        for wizard in self:
            wizard.has_outstanding_amount = wizard.outstanding_amount > 0

    # Closing Settlement.  Multiple settlement lines (maintenance/repair or
    # utility) are invoiced to the tenant and deducted from the security
    # deposit; what is left of the deposit is credited back with a credit note.
    maintenance_line_ids = fields.One2many(
        "close.contract.maintenance.line", "wizard_id", string="Settlement Charges"
    )
    maintenance_amount = fields.Monetary(
        "Total Maintenance Amount", compute="_compute_settlement_totals"
    )
    utility_amount = fields.Monetary(
        "Total Utility Amount", compute="_compute_settlement_totals"
    )
    deposit_amount = fields.Monetary(
        "Security Deposit", compute="_compute_settlement_amounts"
    )
    refundable_amount = fields.Monetary(
        "Refundable to Tenant", compute="_compute_settlement_amounts"
    )
    has_deposit_invoice = fields.Boolean(compute="_compute_settlement_amounts")

    termination_type = fields.Selection(
        [("normal", "Normal Expiry"), ("early", "Early Termination"), ("renewal", "Non-Renewal")],
        string="Termination Type", default="normal",
    )
    move_out_date = fields.Date(string="Move Out Date")
    key_handover_date = fields.Date(string="Date of Key Handover")

    @api.depends("maintenance_line_ids.amount", "maintenance_line_ids.charge_type")
    def _compute_settlement_totals(self):
        for wizard in self:
            wizard.maintenance_amount = sum(
                wizard.maintenance_line_ids.filtered(lambda l: l.charge_type == "maintenance").mapped("amount")
            )
            wizard.utility_amount = sum(
                wizard.maintenance_line_ids.filtered(lambda l: l.charge_type == "utility").mapped("amount")
            )

    @api.depends("contract_id")
    def _compute_settlement_amounts(self):
        """Preview the settlement: deposit refunded in full"""
        for wizard in self:
            deposit_invoice_id = (
                wizard.contract_id._get_deposit_invoice()
                if wizard.contract_id
                else False
            )
            deposit_amount = (
                deposit_invoice_id.amount_total if deposit_invoice_id else 0.0
            )
            wizard.has_deposit_invoice = bool(deposit_invoice_id)
            wizard.deposit_amount = deposit_amount
            wizard.refundable_amount = deposit_amount

    # Water Readings
    water_reading = fields.Float("Final Water Reading (m³)", required=True)
    water_reading_date = fields.Datetime(
        "Water Reading Date/Time", required=True, default=fields.Datetime.now
    )

    # Electricity Readings
    electricity_reading = fields.Float("Final Electricity Reading (kWh)", required=True)
    electricity_reading_date = fields.Datetime(
        "Electricity Reading Date/Time", required=True, default=fields.Datetime.now
    )

    # Inspection Request fields
    inspection_name = fields.Char("Inspection Title")
    inspection_description = fields.Html("Inspection Description")
    inspection_partner_id = fields.Many2one("res.partner", string="Inspection Contact")

    rent_paid_upto = fields.Date(string="Rent Paid Upto")
    rent_paid_upto_note = fields.Char(string="Rent Paid Upto (Note)")
    rent_due_amount = fields.Monetary(string="Rent Due")
    rent_refund_note = fields.Char(string="Rent Refund Period/Note")
    rent_refund_amount = fields.Monetary(string="Rent Refund Amount")
    tenant_paid_repair_note = fields.Char(string="Tenant Paid for Repair (Note)")
    tenant_paid_repair_amount = fields.Monetary(string="Tenant Paid for Repair Amount")
    payment_mode = fields.Selection(
        [("cheque", "Cheque"), ("bank_transfer", "Bank Transfer"), ("cash", "Cash")],
        string="Payment Mode",
    )
    termination_type = fields.Selection(
        [("normal", "Normal Expiry"), ("early", "Early Termination"), ("renewal", "Non-Renewal")],
        string="Termination Type", default="normal",
    )
    move_out_date = fields.Date(string="Move Out Date")
    key_handover_date = fields.Date(string="Date of Key Handover")

    maintenance_amount = fields.Monetary("Total Maintenance Amount", compute="_compute_settlement_totals")
    utility_amount = fields.Monetary("Total Utility Amount", compute="_compute_settlement_totals")
    termination_type = fields.Selection(
        [("normal", "Normal Expiry"), ("early", "Early Termination"), ("renewal", "Non-Renewal")],
        string="Termination Type", default="normal",
    )
    move_out_date = fields.Date(string="Move Out Date")
    key_handover_date = fields.Date(string="Date of Key Handover")

    @api.depends("maintenance_line_ids.amount", "maintenance_line_ids.charge_type")
    def _compute_settlement_totals(self):
        for wizard in self:
            wizard.maintenance_amount = sum(
                wizard.maintenance_line_ids.filtered(lambda l: l.charge_type == "maintenance").mapped("amount")
            )
            wizard.utility_amount = sum(
                wizard.maintenance_line_ids.filtered(lambda l: l.charge_type == "utility").mapped("amount")
            )

    @api.model
    def default_get(self, fields_list):
        """Default get: pre-fill readings from property's latest readings"""
        res = super(CloseContractWizard, self).default_get(fields_list)
        active_id = self.env.context.get("active_id")
        active_model = self.env.context.get("active_model")

        if active_model == "tenancy.details" and active_id:
            contract = self.env["tenancy.details"].browse(active_id)
            res["contract_id"] = contract.id

            water_reading = 0.0
            electricity_reading = 0.0

            if contract.property_id:
                prop = contract.property_id
                if prop.water_readings_id and "water_reading" in fields_list:
                    water_reading = prop.water_readings_id.name
                    res["water_reading"] = water_reading
                if prop.electricity_readings_id and "electricity_reading" in fields_list:
                    electricity_reading = prop.electricity_readings_id.name
                    res["electricity_reading"] = electricity_reading

                res["inspection_name"] = f"[{prop.property_seq}] Inspection Request"
                res["inspection_partner_id"] = contract.tenancy_id.id

                res["move_out_date"] = contract.end_date
                res["key_handover_date"] = contract.end_date

                if "maintenance_line_ids" in fields_list:
                    lines = []
                    if contract.maintenance_item_id:
                        lines.append((0, 0, {
                            "charge_type": "maintenance",
                            "product_id": contract.maintenance_item_id.id,
                            "description": _(
                                "Closing maintenance of %(property)s", property=prop.name
                            ),
                            "amount": 0.0,
                        }))
                    lines.append((0, 0, {
                        "charge_type": "utility",
                        "utility_type": "electricity",
                        "meter_no": prop.utility_electricity_account_no,
                        "closing_reading": electricity_reading,
                        "closing_date": fields.Date.today(),
                        "amount": 0.0,
                    }))
                    lines.append((0, 0, {
                        "charge_type": "utility",
                        "utility_type": "water",
                        "meter_no": prop.utility_water_account_no,
                        "closing_reading": water_reading,
                        "closing_date": fields.Date.today(),
                        "amount": 0.0,
                    }))
                    res["maintenance_line_ids"] = lines

        return res

    def _create_property_readings(self):
        """Create water and electricity reading records"""
        self.ensure_one()
        if not self.property_id:
            return

        # Create water reading
        self.env["property.water.readings"].sudo().create(
            {
                "name": self.water_reading,
                "property_details_id": self.property_id.id,
                "reference": self.contract_id.tenancy_seq,
                "reading_date": self.water_reading_date,
            }
        )

        # Create electricity reading
        self.env["property.electricity.readings"].sudo().create(
            {
                "name": self.electricity_reading,
                "property_details_id": self.property_id.id,
                "reference": self.contract_id.tenancy_seq,
                "reading_date": self.electricity_reading_date,
            }
        )

    def action_create_inspection_request(self):
        """Create helpdesk ticket for inspection request"""
        self.ensure_one()

        if not self.inspection_name:
            raise ValidationError(_("Please provide an inspection title."))

        # Build description if not provided
        description = self.inspection_description or ""
        if not description:
            description = self._build_default_inspection_description()

        self.env["helpdesk.ticket"].sudo().create(
            {
                "name": self.inspection_name,
                "partner_id": self.inspection_partner_id.id or self.tenant_id.id,
                "description": description,
            }
        )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "success",
                "title": _("Inspection Requested"),
                "message": _("Inspection request has been created successfully."),
                "sticky": False,
            },
        }

    @api.onchange("water_reading", "water_reading_date")
    def _onchange_water_reading(self):
        for line in self.maintenance_line_ids.filtered(
            lambda l: l.charge_type == "utility" and l.utility_type == "water"
        ):
            line.closing_reading = self.water_reading
            line.closing_date = self.water_reading_date.date() if self.water_reading_date else False

    @api.onchange("electricity_reading", "electricity_reading_date")
    def _onchange_electricity_reading(self):
        for line in self.maintenance_line_ids.filtered(
            lambda l: l.charge_type == "utility" and l.utility_type == "electricity"
        ):
            line.closing_reading = self.electricity_reading
            line.closing_date = self.electricity_reading_date.date() if self.electricity_reading_date else False

    def _build_default_inspection_description(self):
        """Build default HTML description for inspection"""
        prop = self.property_id
        address_parts = []
        if prop.street:
            address_parts.append(prop.street)
        if prop.street2:
            address_parts.append(prop.street2)
        if prop.city_id:
            address_parts.append(prop.city_id.name)
        if prop.state_id:
            address_parts.append(prop.state_id.name)
        if prop.country_id:
            address_parts.append(prop.country_id.name)

        address = ", ".join(address_parts) if address_parts else "N/A"
        landlord_name = prop.landlord_id.name if prop.landlord_id else "N/A"

        return f"""
        <h3>Contract Close Inspection</h3>
        <p><strong>Contract:</strong> {self.contract_id.tenancy_seq}</p>
        <p><strong>Property:</strong> {prop.name} ({prop.property_seq})</p>
        <p><strong>Tenant:</strong> {self.tenant_id.name}</p>
        <p><strong>Address:</strong> {address}</p>
        <p><strong>Landlord:</strong> {landlord_name}</p>
        <h4>Final Readings</h4>
        <ul>
            <li>Water: {self.water_reading} m³ (Date: {self.water_reading_date})</li>
            <li>Electricity: {self.electricity_reading} kWh (Date: {self.electricity_reading_date})</li>
        </ul>
        <p><em>Inspection requested during contract closure.</em></p>
        """

    def action_close_contract(self):
        self.ensure_one()
        if self.water_reading < 0 or self.electricity_reading < 0:
            raise ValidationError(_("Readings cannot be negative."))

        self._create_property_readings()

        settlement_lines = []
        maintenance_final_lines = []
        utility_final_lines = []

        for line in self.maintenance_line_ids:
            if line.amount <= 0:
                continue
            if line.charge_type == "maintenance":
                if not line.product_id:
                    raise ValidationError(_("Select an item for every maintenance/repair line."))
                settlement_lines.append({
                    "charge_type": "maintenance",
                    "product_id": line.product_id.id,
                    "description": line.description,
                    "amount": line.amount,
                })
                maintenance_final_lines.append((0, 0, {
                    "product_id": line.product_id.id,
                    "description": line.description,
                    "amount": line.amount,
                }))
            else:  # utility
                if not line.utility_type:
                    raise ValidationError(_("Select Electricity or Water for every utility line."))
                settlement_lines.append({
                    "charge_type": "utility",
                    "product_id": line.product_id.id if line.product_id else self.contract_id.maintenance_item_id.id,
                    "description": line.description or dict(line._fields["utility_type"].selection).get(
                        line.utility_type),
                    "amount": line.amount,
                })
                utility_final_lines.append((0, 0, {
                    "utility_type": line.utility_type,
                    "meter_no": line.meter_no,
                    "closing_reading": line.closing_reading,
                    "closing_date": line.closing_date,
                    "amount": line.amount,
                }))

        result = self.contract_id._do_close_contract(maintenance_lines=settlement_lines)

        self.contract_id.write({
            "termination_type": self.termination_type,
            "move_out_date": self.move_out_date,
            "key_handover_date": self.key_handover_date,
            "final_maintenance_line_ids": maintenance_final_lines,
            "final_utility_line_ids": utility_final_lines,
        })
        return result

class CloseContractMaintenanceLine(models.TransientModel):
    _name = "close.contract.maintenance.line"
    _description = "Close Contract Settlement Line"

    wizard_id = fields.Many2one("close.contract.wizard", string="Wizard", ondelete="cascade")
    charge_type = fields.Selection(
        [("maintenance", "Maintenance / Repair"), ("utility", "Utility")],
        string="Type", default="maintenance", required=True,
    )
    product_id = fields.Many2one("product.product", string="Item")
    description = fields.Char(string="Description")
    utility_type = fields.Selection(
        [("electricity", "Electricity"), ("water", "Water")], string="Utility"
    )
    meter_no = fields.Char(string="Meter No.")
    closing_reading = fields.Float(string="Closing Reading")
    closing_date = fields.Date(string="Closing Date")
    amount = fields.Monetary(string="Amount", required=True)
    currency_id = fields.Many2one(related="wizard_id.currency_id")

    @api.constrains("amount")
    def _check_amount_is_not_negative(self):
        for rec in self:
            if rec.amount < 0:
                raise ValidationError(_("Amount must be zero or greater"))