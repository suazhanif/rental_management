from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class PropertyOccupation(models.Model):
    _name = "property.occupation"
    _description = "Property Occupation"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = "employee_id"
    _order = "date_from desc"

    # =========================
    # Basic Information
    # =========================

    employee_id = fields.Many2one(
        "hr.employee", string="Employee", required=True, tracking=True
    )

    unit_id = fields.Many2one(
        "property.details",
        string="Unit",
        required=True,
        tracking=True,
        domain=[
            ("sale_lease", "in", ("employee_family", "bachelor")),
            ("stage", "=", "available"),
        ],
    )

    bed_id = fields.Many2one(
        "property.bed",
        string="Bed",
        tracking=True,
        domain="[('unit_id', '=', unit_id), ('state', '=', 'available')]",
    )

    accommodation_type = fields.Selection(
        [
            ("employee_family", "Employee Family Accommodation"),
            ("bachelor", "Bachelor Accommodation"),
        ],
        string="Accommodation Type",
        required=True,
        tracking=True,
    )

    # =========================
    # Dates
    # =========================

    date_from = fields.Date(
        string="Occupation Start Date",
        required=True,
        default=fields.Date.today,
        tracking=True,
    )

    date_to = fields.Date(string="Occupation End Date", tracking=True)

    # =========================
    # Status
    # =========================

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("active", "Active"),
            ("vacated", "Vacated"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        tracking=True,
    )

    # =========================
    # Computed Fields
    # =========================

    duration_days = fields.Integer(
        string="Duration (Days)", compute="_compute_duration", store=True
    )

    @api.depends("date_from", "date_to")
    def _compute_duration(self):
        for rec in self:
            if rec.date_from and rec.date_to:
                rec.duration_days = (rec.date_to - rec.date_from).days
            else:
                rec.duration_days = 0

    # =========================
    # Constraints
    # =========================

    @api.constrains("accommodation_type", "bed_id")
    def _check_bed_required_for_bachelor(self):
        for rec in self:
            if rec.accommodation_type == "bachelor" and not rec.bed_id:
                raise ValidationError(_("Bed is required for Bachelor accommodation."))

            if rec.accommodation_type == "employee_family" and rec.bed_id:
                raise ValidationError(
                    _("Bed should not be selected for Family accommodation.")
                )

    @api.constrains("employee_id", "state")
    def _check_employee_not_double_allocated(self):
        for rec in self:
            if rec.state != "active":
                continue

            existing = self.search(
                [
                    ("employee_id", "=", rec.employee_id.id),
                    ("state", "=", "active"),
                    ("id", "!=", rec.id),
                ]
            )

            if existing:
                raise ValidationError(_("Employee already has an active occupation."))

    # =========================
    # Actions
    # =========================

    def action_confirm(self):

        for rec in self:
            if rec.state != "draft":
                continue

            if rec.unit_id.stage != "available":
                raise ValidationError(_("Unit is not available."))

            # Mark unit occupied
            rec.unit_id.stage = "on_lease"

            # Mark bed occupied (Bachelor)
            if rec.accommodation_type == "bachelor":
                if rec.bed_id.state != "available":
                    raise ValidationError(_("Bed is already occupied."))

                rec.bed_id.state = "occupied"
                rec.bed_id.employee_id = rec.employee_id

            rec.state = "active"

    def action_vacate(self):

        for rec in self:
            if rec.state != "active":
                continue

            # Free bed
            if rec.bed_id:
                rec.bed_id.state = "available"
                rec.bed_id.employee_id = False

            # Free unit
            rec.unit_id.stage = "available"

            rec.date_to = fields.Date.today()

            rec.state = "vacated"

    def action_cancel(self):

        for rec in self:
            if rec.state == "active":
                raise ValidationError(
                    _("Cannot cancel active occupation. Vacate first.")
                )

            rec.state = "cancelled"
