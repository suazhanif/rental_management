# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class OccupyDetails(models.Model):
    """Occupant Accommodation Contract"""

    _name = "occupy.details"
    _description = "Occupant Accommodation Contract"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = "occupy_seq"

    # Sequence
    occupy_seq = fields.Char(
        string="Sequence",
        required=True,
        readonly=True,
        copy=False,
        default=lambda self: _("New"),
    )

    # State
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("running", "Running"),
            ("cancel", "Cancel"),
            ("close", "Close"),
            ("expire", "Expire"),
        ],
        string="Status",
        default="draft",
        tracking=True,
        required=True,
    )

    # Partner Type
    partner_type = fields.Selection(
        [
            ("company", "Company Employee"),
            ("non_company", "Non-Company"),
        ],
        string="Type",
        default="company",
        required=True,
    )

    # Occupant (res.partner for both cases)
    occupant_id = fields.Many2one(
        "res.partner",
        string="Occupant",
        required=True,
        tracking=True,
    )

    # Related fields from occupant
    occupant_name = fields.Char(
        related="occupant_id.name", string="Name", readonly=True
    )
    occupant_phone = fields.Char(
        related="occupant_id.phone", string="Phone", readonly=True
    )
    occupant_email = fields.Char(
        related="occupant_id.email", string="Email", readonly=True
    )

    # Employee-specific fields (only populated if occupant is linked to employee)
    employee_id = fields.Many2one(
        "hr.employee",
        string="Employee Record",
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

    # Property
    property_id = fields.Many2one(
        "property.details",
        string="Property",
        domain="[('stage', '=', 'available'), ('sale_lease', 'in', ['employee_family', 'bachelor'])]",
        required=True,
        tracking=True,
    )
    property_type = fields.Selection(
        related="property_id.type",
        string="Property Type",
        readonly=True,
    )
    sale_lease = fields.Selection(
        related="property_id.sale_lease",
        string="Accommodation Type",
        readonly=True,
    )
    bed_id = fields.Many2one("property.bed")
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

    # Dates
    start_date = fields.Date(
        string="Start Date",
        required=True,
        default=fields.Date.today,
        tracking=True,
    )
    expected_end_date = fields.Date(
        string="Expected End Date",
        tracking=True,
    )
    days_left = fields.Integer(
        string="Days Left",
        compute="_compute_days_left",
    )

    note = fields.Text(string="Note")

    # Company & Currency
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="company_id.currency_id",
        string="Currency",
    )

    # Responsible
    responsible_id = fields.Many2one(
        "res.users",
        default=lambda self: self.env.user,
        string="Responsible",
        tracking=True,
    )

    # Extend Contract Ref.
    extended = fields.Boolean(string="Is Extended", default=False)
    is_extended = fields.Boolean(string="Is Extended Contract", default=False)
    extend_from = fields.Char(string="Extend From")
    new_occupy_id = fields.Many2one("occupy.details", string="New Contract Ref")

    # Active State
    active_contract_state = fields.Boolean(string="Active State", default=False)

    # Terminate
    terminate_date = fields.Date(string="Terminate Date")

    # Material Hand Over
    is_material_handover_applicable = fields.Boolean(
        string="Material Handover Applicable",
        compute="_compute_is_material_handover_applicable",
        store=True,
    )
    material_line_ids = fields.One2many(
        "occupy.material.line", "occupy_id", string="Material Hand Over"
    )

    @api.depends("partner_type", "sale_lease")
    def _compute_is_material_handover_applicable(self):
        for rec in self:
            rec.is_material_handover_applicable = (
                rec.partner_type == "company"
                and rec.sale_lease in ("employee_family", "bachelor")
            )

    # Create
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("occupy_seq", "New") == "New":
                vals["occupy_seq"] = (
                    self.env["ir.sequence"].next_by_code("occupy.details") or "New"
                )
        return super(OccupyDetails, self).create(vals_list)

    # Compute
    @api.depends("expected_end_date", "state")
    def _compute_days_left(self):
        today = fields.Date.today()
        for rec in self:
            if rec.state == "running" and rec.expected_end_date:
                days = (rec.expected_end_date - today).days
                rec.days_left = days if days > 0 else 0
            else:
                rec.days_left = 0

    # Onchange
    @api.onchange("partner_type")
    def _onchange_partner_type(self):
        for rec in self:
            rec.occupant_id = False

    @api.onchange("occupant_id")
    def _onchange_occupant_id(self):
        for rec in self:
            if rec.occupant_id and not rec.expected_end_date:
                rec.expected_end_date = rec.start_date + relativedelta(years=1)

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

    # Buttons
    def action_set_running(self):
        """Change status from Draft to Running - Only officer/manager"""
        if not self.env.user.has_group(
                "rental_management.property_rental_manager"
        ) and not self.env.user.has_group("rental_management.property_rental_officer"):
            raise UserError(_("Only officers or managers can activate contracts."))

        for rec in self:
            if rec.state != "draft":
                raise UserError(_("Only draft contracts can be activated."))

            if rec.bed_id:
                rec.bed_id.write({"state": "occupied"})

            rec.property_id._set_property_not_available()

            # Material Hand Over: set dates based on activation date
            activation_date = fields.Date.today()
            for line in rec.material_line_ids:
                line.write(
                    {
                        "start_date": activation_date,
                        "end_date": activation_date
                                    + relativedelta(
                            years=line.material_id.replacement_years
                        ),
                    }
                )

            rec.write(
                {
                    "state": "running",
                    "active_contract_state": True,
                }
            )

    def action_close_contract(self):
        for rec in self:
            if rec.state != "running":
                raise UserError(_("Only running contracts can be closed."))
            return {
                "type": "ir.actions.act_window",
                "name": "Vacate Wizard",
                "res_model": "vacate.wizard",
                "view_mode": "form",
                "view_id": self.env.ref("rental_management.vacate_wizard_form_view").id,
                "target": "new",
                "context": {
                    "active_id": self.id,
                    "active_model": "occupy.details",
                },
            }

    def action_cancel_contract(self):
        for rec in self:
            if rec.state not in ["draft", "running"]:
                raise UserError(_("Only draft or running contracts can be cancelled."))
            rec.property_id.write({"stage": "available"})
            if rec.bed_id:
                rec.bed_id.write({"state": "available"})
            rec.write(
                {
                    "state": "cancel",
                    "terminate_date": fields.Date.today(),
                }
            )

    # Scheduler
    @api.model
    def occupy_expire(self):
        today = fields.Date.today()
        contracts = self.sudo().search(
            [
                ("state", "=", "running"),
                ("expected_end_date", "!=", False),
            ]
        )
        for rec in contracts:
            if rec.expected_end_date and today > rec.expected_end_date:
                rec.write({"state": "expire"})

    # Unlink
    def unlink(self):
        for rec in self:
            if rec.state not in ["draft", "cancel"]:
                raise UserError(_("Only draft or cancelled contracts can be deleted."))
            if rec.property_id:
                rec.property_id.write({"stage": "available"})
                if rec.bed_id:
                    rec.bed_id.write({"state": "available"})
        return super(OccupyDetails, self).unlink()

class OccupyMaterialLine(models.Model):
    """Material handover line stored against the occupy contract"""

    _name = "occupy.material.line"
    _description = "Occupy Material Handover Line"

    occupy_id = fields.Many2one(
        "occupy.details", string="Occupy Contract", ondelete="cascade"
    )
    material_id = fields.Many2one(
        "property.handover.material", string="Material", required=True
    )
    start_date = fields.Date(string="Handover Date")
    end_date = fields.Date(string="Replacement Due Date")
    note = fields.Char(string="Note")
