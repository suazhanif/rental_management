# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ShiftOccupy(models.Model):
    """Shift Occupant from one accommodation to another (Persistent for audit)"""

    _name = "shift.occupy"
    _description = "Shift Occupy"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = "shift_seq"

    # Sequence
    shift_seq = fields.Char(
        string="Shift Reference",
        required=True,
        readonly=True,
        copy=False,
        default=lambda self: _("New"),
    )

    # State
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("done", "Done"),
            ("cancel", "Cancelled"),
        ],
        string="Status",
        default="draft",
        tracking=True,
        required=True,
    )

    # Employee
    employee_search_id = fields.Many2one(
        "hr.employee",
        string="Search by Employee",
        states={"draft": [("readonly", False)]},
    )

    # Current Occupation (source)
    occupy_id = fields.Many2one(
        "occupy.details",
        string="Current Occupation",
        required=True,
        tracking=True,
        domain="[('state', '=', 'running')]",
    )
    occupant_id = fields.Many2one(
        related="occupy_id.occupant_id",
        string="Occupant",
        readonly=True,
        store=True,
    )
    employee_id = fields.Many2one(
        related="occupy_id.employee_id",
        string="Employee",
        readonly=True,
        store=True,
    )

    # Shift From (source property - auto-populated)
    from_property_id = fields.Many2one(
        related="occupy_id.property_id",
        string="Shift From (Property)",
        readonly=True,
        store=True,
    )
    from_sale_lease = fields.Selection(
        related="from_property_id.sale_lease",
        string="From Accommodation Type",
        readonly=True,
        store=True,
    )
    from_bed_id = fields.Many2one(
        related="occupy_id.bed_id",
        string="Shift From (Bed)",
        readonly=True,
        store=True,
    )

    # Shift To (target property)
    to_property_id = fields.Many2one(
        "property.details",
        string="Shift To (Property)",
        required=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
        domain="[('stage', '=', 'available'), ('sale_lease', 'in', ['employee_family', 'bachelor'])]",
        tracking=True,
    )
    to_sale_lease = fields.Selection(
        related="to_property_id.sale_lease",
        string="To Accommodation Type",
        readonly=True,
        store=True,
    )
    to_bed_id = fields.Many2one(
        "property.bed",
        string="Shift To (Bed)",
        readonly=True,
        states={"draft": [("readonly", False)]},
        domain="[('property_id', '=', to_property_id), ('state', '=', 'available')]",
    )

    # Shift Reason
    shift_reason = fields.Text(
        string="Shift Reason",
        required=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
        tracking=True,
    )

    # Dates
    shift_date = fields.Date(
        string="Shift Date",
        default=fields.Date.today,
        readonly=True,
        states={"draft": [("readonly", False)]},
        tracking=True,
    )

    # Resulting new occupy
    new_occupy_id = fields.Many2one(
        "occupy.details",
        string="New Occupy Contract",
        readonly=True,
        tracking=True,
    )

    # Readings tracking
    is_readings_required = fields.Boolean(
        compute="_compute_is_readings_required",
        store=True,
    )

    # Utility Readings (for vacating old property)
    water_reading = fields.Float("Water Reading (m³)")
    water_reading_date = fields.Datetime("Water Reading Date/Time", default=fields.Datetime.now)
    electricity_reading = fields.Float("Electricity Reading (kWh)")
    electricity_reading_date = fields.Datetime("Electricity Reading Date/Time", default=fields.Datetime.now)

    # Company
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
    )

    @api.onchange("employee_search_id")
    def _onchange_employee_search_id(self):
        for rec in self:
            if rec.employee_search_id:
                rec.occupy_id = rec.employee_search_id.occupy_id
            else:
                rec.occupy_id = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Set Current Occupation
            if not vals.get("occupy_id") and vals.get("employee_search_id"):
                employee = self.env["hr.employee"].browse(vals["employee_search_id"])
                if employee.occupy_id:
                    vals["occupy_id"] = employee.occupy_id.id
            # Set Sequence
            if vals.get("shift_seq", "New") == "New":
                vals["shift_seq"] = (
                    self.env["ir.sequence"].next_by_code("shift.occupy") or "New"
                )
        return super(ShiftOccupy, self).create(vals_list)

    @api.depends("from_property_id", "from_property_id.sale_lease")
    def _compute_is_readings_required(self):
        for rec in self:
            rec.is_readings_required = (
                rec.from_property_id.sale_lease == "employee_family"
            )

    @api.onchange("to_property_id")
    def _onchange_to_property_id(self):
        self.to_bed_id = False
    
    @api.onchange("occupy_id")
    def _onchange_occupy_id(self):
        for rec in self:
            if rec.occupy_id and rec.occupy_id.property_id:
                prop = rec.occupy_id.property_id
                rec.water_reading = (
                    prop.water_readings_id.name if prop.water_readings_id else 0.0
                )
                rec.electricity_reading = (
                    prop.electricity_readings_id.name if prop.electricity_readings_id else 0.0
                )
                now = fields.Datetime.now()
                rec.water_reading_date = now
                rec.electricity_reading_date = now
            else:
                rec.water_reading = 0.0
                rec.electricity_reading = 0.0
                rec.water_reading_date = False
                rec.electricity_reading_date = False

    @api.constrains("to_property_id", "to_bed_id")
    def _check_target_property(self):
        for rec in self:
            if rec.to_property_id.sale_lease == "bachelor" and not rec.to_bed_id:
                raise ValidationError(
                    _("Bed must be selected for bachelor accommodation")
                )

    @api.constrains("water_reading", "electricity_reading")
    def _check_readings(self):
        for rec in self:
            if rec.is_readings_required:
                if rec.water_reading <= 0:
                    raise ValidationError(_("Water reading must be greater than zero"))
                if rec.electricity_reading <= 0:
                    raise ValidationError(
                        _("Electricity reading must be greater than zero")
                    )

    def action_shift(self):
        """Execute the shift: vacate old property, occupy new property"""
        self.ensure_one()

        if self.state != "draft":
            raise ValidationError(_("Only draft shift records can be processed"))

        occupy = self.occupy_id
        old_property = self.from_property_id
        new_property = self.to_property_id

        # Validate current state
        if occupy.state != "running":
            raise ValidationError(_("Only running contracts can be shifted"))

        # Validate target availability
        if new_property.stage != "available":
            raise ValidationError(_("Target property is not available"))

        # Validate bed for bachelor
        if new_property.sale_lease == "bachelor":
            if not self.to_bed_id:
                raise ValidationError(
                    _("Bed must be selected for bachelor accommodation")
                )
            if self.to_bed_id.state != "available":
                raise ValidationError(_("Selected bed is not available"))

        # Step 1: Record final readings on old property (if required)
        if self.is_readings_required:
            self._create_vacate_readings(occupy)

        # Step 2: Vacate old property
        if old_property.sale_lease == "bachelor" and occupy.bed_id:
            occupy.bed_id.write({"state": "available"})

        old_property.write({"stage": "available"})

        occupy.write(
            {
                "state": "close",
                "terminate_date": fields.Date.today(),
            }
        )

        # Step 3: Create new occupy record
        new_occupy_vals = {
            "partner_type": occupy.partner_type,
            "occupant_id": occupy.occupant_id.id,
            "property_id": new_property.id,
            "start_date": fields.Date.today(),
            "expected_end_date": occupy.expected_end_date,
            "state": "running",
            "active_contract_state": True,
        }

        if occupy.employee_id:
            new_occupy_vals["employee_id"] = occupy.employee_id.id

        if new_property.sale_lease == "bachelor":
            new_occupy_vals["bed_id"] = self.to_bed_id.id
            self.to_bed_id.write({"state": "occupied"})

        new_property._set_property_not_available()

        new_occupy = self.env["occupy.details"].create(new_occupy_vals)

        # Step 4: Create initial readings for new property if family accommodation
        if new_property.sale_lease == "employee_family":
            self._create_occupy_readings(new_occupy, new_property)

        # Update shift record
        self.write(
            {
                "state": "done",
                "new_occupy_id": new_occupy.id,
            }
        )

        return {
            "type": "ir.actions.act_window",
            "name": "New Occupy Contract",
            "res_model": "occupy.details",
            "res_id": new_occupy.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_cancel(self):
        """Cancel draft shift record"""
        self.write({"state": "cancel"})

    def action_reset_draft(self):
        """Reset to draft (manager only)"""
        if not self.env.user.has_group("rental_management.property_rental_manager"):
            raise ValidationError(_("Only managers can reset to draft"))
        self.write({"state": "draft"})

    def _create_vacate_readings(self, occupy):
        """Create final water/electricity readings for old property"""
        self.ensure_one()
        if not self.from_property_id:
            return

        if self.water_reading_date:
            self.env["property.water.readings"].sudo().create(
                {
                    "name": self.water_reading,
                    "reference": f"{occupy.occupy_seq} (Shift Vacate - {self.shift_seq})",
                    "property_details_id": self.from_property_id.id,
                    "reading_date": self.water_reading_date,
                }
            )

        if self.electricity_reading_date:
            self.env["property.electricity.readings"].sudo().create(
                {
                    "name": self.electricity_reading,
                    "reference": f"{occupy.occupy_seq} (Shift Vacate - {self.shift_seq})",
                    "property_details_id": self.from_property_id.id,
                    "reading_date": self.electricity_reading_date,
                }
            )

    def _create_occupy_readings(self, occupy, property_id):
        """Create initial readings for new property"""
        self.ensure_one()
        if not property_id:
            return

        water_val = (
            property_id.water_readings_id.name if property_id.water_readings_id else 0.0
        )
        elec_val = (
            property_id.electricity_readings_id.name
            if property_id.electricity_readings_id
            else 0.0
        )
        now = fields.Datetime.now()

        self.env["property.water.readings"].sudo().create(
            {
                "name": water_val,
                "reference": f"{occupy.occupy_seq} (Shift Occupy - {self.shift_seq})",
                "property_details_id": property_id.id,
                "reading_date": now,
            }
        )

        self.env["property.electricity.readings"].sudo().create(
            {
                "name": elec_val,
                "reference": f"{occupy.occupy_seq} (Shift Occupy - {self.shift_seq})",
                "property_details_id": property_id.id,
                "reading_date": now,
            }
        )
