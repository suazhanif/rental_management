# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class OccupyWizard(models.TransientModel):
    """Occupant Accommodation Booking Wizard"""

    _name = "occupy.wizard"
    _description = "Occupy Wizard"

    # Type
    partner_type = fields.Selection(
        [
            ("company", "Company Employee"),
            ("non_company", "Non-Company"),
        ],
        string="Type",
        default="company",
        required=True,
    )

    # Property
    property_id = fields.Many2one(
        "property.details",
        string="Property",
        domain="[('stage', '=', 'available'), ('sale_lease', 'in', ['employee_family', 'bachelor'])]",
        required=True,
    )
    sale_lease = fields.Selection(
        related="property_id.sale_lease",
        string="Accommodation Type",
        readonly=True,
    )
    bed_id = fields.Many2one(
        "property.bed",
        domain="[('property_id', '=', property_id), ('state', '=', 'available')]",
    )

    # Occupant (res.partner for both cases)
    occupant_id = fields.Many2one(
        "res.partner",
        string="Occupant",
        required=True,
    )

    # Related fields
    occupant_name = fields.Char(
        related="occupant_id.name", string="Name", readonly=True
    )
    occupant_phone = fields.Char(
        related="occupant_id.phone", string="Phone", readonly=True
    )
    occupant_email = fields.Char(
        related="occupant_id.email", string="Email", readonly=True
    )

    # Employee-specific (computed from occupant)
    employee_id = fields.Many2one(
        "hr.employee",
        string="Employee",
    )
    employee_code = fields.Char(
        related="employee_id.employee_code",
        string="Employee Code",
        readonly=True,
    )
    department_id = fields.Many2one(
        related="employee_id.department_id",
        string="Department",
        readonly=True,
    )

    utility_water_account_no = fields.Char(
        related="property_id.utility_water_account_no",
        string="Water Account No.",
        readonly=True,
    )
    utility_electricity_account_no = fields.Char(
        related="property_id.utility_electricity_account_no",
        string="Electricity Account No.",
        readonly=True,
    )

    water_reading = fields.Float("Water Reading (m³)")
    water_reading_date = fields.Datetime("Water Reading Date/Time")
    electricity_reading = fields.Float("Electricity Reading (kWh)")
    electricity_reading_date = fields.Datetime("Electricity Reading Date/Time")

    start_date = fields.Date(
        string="Start Date",
        required=True,
        default=fields.Date.today,
    )
    expected_end_date = fields.Date(
        string="Expected End Date",
    )

    note = fields.Text(string="Note")

    # Is Readings Required
    is_readings_required = fields.Boolean(
        compute="_compute_is_readings_required",
    )

    # Material Hand Over
    is_material_handover_applicable = fields.Boolean(
        string="Material Handover Applicable",
        compute="_compute_is_material_handover_applicable",
    )
    material_line_ids = fields.One2many(
        "occupy.wizard.material.line",
        "occupy_wizard_id",
        string="Material Hand Over",
    )

    @api.model
    def default_get(self, fields_list):
        res = super(OccupyWizard, self).default_get(fields_list)

        active_id = self.env.context.get("active_id")
        active_model = self.env.context.get("active_model")

        if active_model == "property.details" and active_id:
            property_id = self.env["property.details"].browse(active_id)
            res["property_id"] = active_id

            # Auto-populate readings from property
            if "water_reading" in fields_list:
                res["water_reading"] = (
                    property_id.water_readings_id.name
                    if property_id.water_readings_id
                    else 0.0
                )
            if "electricity_reading" in fields_list:
                res["electricity_reading"] = (
                    property_id.electricity_readings_id.name
                    if property_id.electricity_readings_id
                    else 0.0
                )
            if "water_reading_date" in fields_list:
                res["water_reading_date"] = fields.Datetime.now()
            if "electricity_reading_date" in fields_list:
                res["electricity_reading_date"] = fields.Datetime.now()

        return res

    @api.onchange("employee_id")
    def _onchange_employee_id(self):
        for rec in self:
            rec.occupant_id = (
                rec.employee_id.work_contact_id if rec.employee_id else False
            )

    @api.depends("property_id", "property_id.sale_lease")
    def _compute_is_readings_required(self):
        for rec in self:
            rec.is_readings_required = rec.property_id.sale_lease == "employee_family"

    @api.depends("partner_type", "sale_lease")
    def _compute_is_material_handover_applicable(self):
        """Only for Company Employee + Family or Bachelor accommodation"""
        for rec in self:
            rec.is_material_handover_applicable = (
                rec.partner_type == "company"
                and rec.sale_lease in ("employee_family", "bachelor")
            )

    def _populate_material_lines(self):
        """Populate default material handover lines from the configured master list"""
        self.ensure_one()
        materials = self.env["property.handover.material"].search([])
        self.material_line_ids = [(5, 0, 0)] + [
            (0, 0, {"material_id": m.id}) for m in materials
        ]

    @api.onchange("property_id", "partner_type")
    def _onchange_material_handover_trigger(self):
        for rec in self:
            if rec.is_material_handover_applicable:
                if not rec.material_line_ids:
                    rec._populate_material_lines()
            else:
                rec.material_line_ids = [(5, 0, 0)]

    # Onchange
    @api.onchange("property_id")
    def _onchange_property_id(self):
        for rec in self:
            if rec.property_id:
                if rec.property_id.water_readings_id:
                    rec.water_reading = rec.property_id.water_readings_id.name
                else:
                    rec.water_reading = 0.0
                if rec.property_id.electricity_readings_id:
                    rec.electricity_reading = (
                        rec.property_id.electricity_readings_id.name
                    )
                else:
                    rec.electricity_reading = 0.0
                now = fields.Datetime.now()
                rec.water_reading_date = now
                rec.electricity_reading_date = now

    @api.onchange("occupant_id")
    def _onchange_occupant_id(self):
        for rec in self:
            if rec.occupant_id and not rec.expected_end_date:
                rec.expected_end_date = rec.start_date + relativedelta(years=1)

    @api.onchange("partner_type")
    def _onchange_partner_type(self):
        for rec in self:
            rec.occupant_id = False

    # Constraints
    @api.constrains("start_date", "expected_end_date")
    def _check_dates(self):
        for rec in self:
            if (
                rec.expected_end_date
                and rec.start_date
                and rec.expected_end_date < rec.start_date
            ):
                raise ValidationError(_("Expected end date must be after start date"))

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

    def _create_material_handover_lines(self, occupy):
        """Carry wizard material lines onto the occupy contract (no dates yet —
        dates get set on activation via action_set_running)."""
        self.ensure_one()
        material_vals = [
            (
                0,
                0,
                {
                    "material_id": line.material_id.id,
                    "note": line.note,
                },
            )
            for line in self.material_line_ids
        ]
        occupy.write({"material_line_ids": material_vals})

    # Action
    def action_book(self):
        self.ensure_one()

        if not self.occupant_id:
            raise ValidationError(_("Occupant is required"))

        if self.employee_id.occupy_id:
            approval_wizard = self.env[
                "dual.accommodation.approval.wizard"
            ].create(
                {
                    "partner_type": self.partner_type,
                    "property_id": self.property_id.id,
                    "bed_id": self.bed_id.id if self.bed_id else False,
                    "occupant_id": self.occupant_id.id,
                    "employee_id": self.employee_id.id,
                    "start_date": self.start_date,
                    "expected_end_date": self.expected_end_date,
                    "water_reading": self.water_reading,
                    "water_reading_date": self.water_reading_date,
                    "electricity_reading": self.electricity_reading,
                    "electricity_reading_date": self.electricity_reading_date,
                    "is_readings_required": self.is_readings_required,
                    "existing_occupy_id": self.employee_id.occupy_id.id,
                    "note": self.note,
                }
            )
            return {
                "type": "ir.actions.act_window",
                "name": _("Chairman Approval — Dual Accommodation"),
                "res_model": "dual.accommodation.approval.wizard",
                "res_id": approval_wizard.id,
                "view_mode": "form",
                "target": "new",
            }

        # Validate readings if required
        if self.is_readings_required:
            if self.water_reading <= 0:
                raise ValidationError(
                    _(
                        "Water reading must be greater than zero for family accommodation"
                    )
                )
            if self.electricity_reading <= 0:
                raise ValidationError(
                    _(
                        "Electricity reading must be greater than zero for family accommodation"
                    )
                )

        vals = {
            "partner_type": self.partner_type,
            "occupant_id": self.occupant_id.id,
            "employee_id": self.employee_id.id,
            "property_id": self.property_id.id,
            "start_date": self.start_date,
            "expected_end_date": self.expected_end_date,
            "note": self.note,
            "state": "draft",
        }

        if self.sale_lease == "bachelor":
            if not self.bed_id:
                raise ValidationError(
                    _("Bed must be selected for bachelor accommodation")
                )

            vals["bed_id"] = self.bed_id.id

        occupy = self.env["occupy.details"].create(vals)

        if self.is_readings_required:
            self._create_property_readings(occupy)

        # Material Hand Over
        if self.is_material_handover_applicable and self.material_line_ids:
            self._create_material_handover_lines(occupy)

        return {
            "type": "ir.actions.act_window",
            "name": "Occupy Contract",
            "res_model": "occupy.details",
            "res_id": occupy.id,
            "view_mode": "form",
            "target": "current",
        }

    def _create_property_readings(self, occupy):
        self.ensure_one()
        if not self.property_id:
            return

        if self.water_reading_date:
            self.env["property.water.readings"].sudo().create(
                {
                    "name": self.water_reading,
                    "reference": occupy.occupy_seq,
                    "property_details_id": self.property_id.id,
                    "reading_date": self.water_reading_date,
                }
            )

        if self.electricity_reading_date:
            self.env["property.electricity.readings"].sudo().create(
                {
                    "name": self.electricity_reading,
                    "reference": occupy.occupy_seq,
                    "property_details_id": self.property_id.id,
                    "reading_date": self.electricity_reading_date,
                }
            )

class OccupyWizardMaterialLine(models.TransientModel):

    _name = "occupy.wizard.material.line"
    _description = "Occupy Wizard Material Handover Line"

    occupy_wizard_id = fields.Many2one(
        "occupy.wizard", string="Occupy Wizard", ondelete="cascade"
    )
    material_id = fields.Many2one(
        "property.handover.material", string="Material", required=True
    )
    replacement_years = fields.Integer(
        string="Replacement (Years)",
        related="material_id.replacement_years",
        readonly=True,
    )
    note = fields.Char(string="Note")
