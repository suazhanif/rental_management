# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class VacateWizard(models.TransientModel):
    """Vacate Accommodation Wizard"""

    _name = "vacate.wizard"
    _description = "Vacate Wizard"

    # Contract
    occupy_id = fields.Many2one(
        "occupy.details",
        string="Occupy Contract",
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
        "property.bed", domain="[('property_id', '=', property_id)]"
    )

    # Utility Readings (WIZARD ONLY - linked to property on book)
    water_reading = fields.Float("Water Reading (m³)")
    water_reading_date = fields.Datetime("Water Reading Date/Time")
    electricity_reading = fields.Float("Electricity Reading (kWh)")
    electricity_reading_date = fields.Datetime("Electricity Reading Date/Time")

    # Dates
    end_date = fields.Date(
        string="End Date",
        required=True,
        default=fields.Date.today,
    )

    # Is Readings Required
    is_readings_required = fields.Boolean(
        compute="_compute_is_readings_required",
    )

    @api.model
    def default_get(self, fields_list):
        """Default get with property and readings auto-populated from context"""
        res = super(VacateWizard, self).default_get(fields_list)

        active_id = self.env.context.get("active_id")
        active_model = self.env.context.get("active_model")

        # Called from property.details form
        if active_model == "occupy.details" and active_id:
            occupy_id = self.env["occupy.details"].browse(active_id)
            property_id = occupy_id.property_id
            res["occupy_id"] = active_id
            res["property_id"] = property_id
            res["bed_id"] = occupy_id.bed_id

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

    @api.depends("property_id", "property_id.sale_lease")
    def _compute_is_readings_required(self):
        for rec in self:
            rec.is_readings_required = rec.property_id.sale_lease == "employee_family"

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

    # Action
    def action_vacate(self):
        self.ensure_one()

        if not self.end_date:
            raise ValidationError(_("End date is required"))

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

        # Create utility readings linked to property (not to occupy record)
        if self.is_readings_required:
            self._create_property_readings(self.occupy_id)

        self.property_id.write({"stage": "available"})
        if self.bed_id:
            self.bed_id.write({"state": "available"})
        self.occupy_id.write({"terminate_date": self.end_date, "state": "close"})

        return {
            "type": "ir.actions.act_window",
            "name": "Occupy Contract",
            "res_model": "occupy.details",
            "res_id": self.occupy_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def _create_property_readings(self, occupy):
        """Create water/electricity reading records linked to property only"""
        self.ensure_one()
        if not self.property_id:
            return

        # Water reading
        if self.water_reading_date:
            self.env["property.water.readings"].sudo().create(
                {
                    "name": self.water_reading,
                    "reference": occupy.occupy_seq,
                    "property_details_id": self.property_id.id,
                    "reading_date": self.water_reading_date,
                }
            )

        # Electricity reading
        if self.electricity_reading_date:
            self.env["property.electricity.readings"].sudo().create(
                {
                    "name": self.electricity_reading,
                    "reference": occupy.occupy_seq,
                    "property_details_id": self.property_id.id,
                    "reading_date": self.electricity_reading_date,
                }
            )
