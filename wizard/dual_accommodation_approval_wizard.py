# -*- coding: utf-8 -*-
# Copyright 2026-Baramej®.
# Part of Baramej®. See LICENSE file for full copyright and licensing details.
from dateutil.relativedelta import relativedelta
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class DualAccommodationApprovalWizard(models.TransientModel):
    """Dual Accommodation Chairman Approval Wizard
    Opened when an employee already has a running occupy contract and
    a second bed assignment is attempted.  The user must supply a
    chairman approval number and may attach supporting documents before
    the booking is confirmed.
    """

    _name = "dual.accommodation.approval.wizard"
    _description = "Dual Accommodation Chairman Approval Wizard"

    # ------------------------------------------------------------------ #
    #  Fields carried over from the original OccupyWizard                #
    # ------------------------------------------------------------------ #
    partner_type = fields.Selection(
        [
            ("company", "Company Employee"),
            ("non_company", "Non-Company"),
        ],
        string="Type",
        default="company",
        required=True,
        readonly=True,
    )
    property_id = fields.Many2one(
        "property.details",
        string="Property",
        required=True,
        readonly=True,
    )
    sale_lease = fields.Selection(
        related="property_id.sale_lease",
        string="Accommodation Type",
        readonly=True,
    )
    bed_id = fields.Many2one(
        "property.bed",
        string="Bed",
        readonly=True,
    )
    occupant_id = fields.Many2one(
        "res.partner",
        string="Occupant",
        required=True,
        readonly=True,
    )
    employee_id = fields.Many2one(
        "hr.employee",
        string="Employee",
        readonly=True,
    )
    start_date = fields.Date(
        string="Start Date",
        required=True,
        readonly=True,
    )
    expected_end_date = fields.Date(
        string="Expected End Date",
        readonly=True,
    )
    water_reading = fields.Float("Water Reading (m³)", readonly=True)
    water_reading_date = fields.Datetime("Water Reading Date/Time", readonly=True)
    electricity_reading = fields.Float("Electricity Reading (kWh)", readonly=True)
    electricity_reading_date = fields.Datetime(
        "Electricity Reading Date/Time", readonly=True
    )
    is_readings_required = fields.Boolean(readonly=True)
    note = fields.Text(string="Note", readonly=True)

    # ------------------------------------------------------------------ #
    #  Read-only info shown to the user                                   #
    # ------------------------------------------------------------------ #
    existing_occupy_id = fields.Many2one(
        "occupy.details",
        string="Existing Contract",
        readonly=True,
    )
    existing_property_id = fields.Many2one(
        related="existing_occupy_id.property_id",
        string="Current Property",
        readonly=True,
    )
    existing_bed_id = fields.Many2one(
        related="existing_occupy_id.bed_id",
        string="Current Bed",
        readonly=True,
    )
    existing_start_date = fields.Date(
        related="existing_occupy_id.start_date",
        string="Contract Start",
        readonly=True,
    )

    # ------------------------------------------------------------------ #
    #  Approval fields                                                    #
    # ------------------------------------------------------------------ #
    approval_number = fields.Char(
        string="Chairman Approval Number",
        help="Enter the approval reference number issued by the Chairman.",
    )
    approval_document_ids = fields.Many2many(
        "ir.attachment",
        "dual_accom_approval_attachment_rel",
        "wizard_id",
        "attachment_id",
        string="Supporting Documents",
        help="Attach the signed approval letter or any other supporting documents.",
    )
    approval_notes = fields.Text(
        string="Notes",
        help="Any additional remarks regarding the dual accommodation approval.",
    )

    # ------------------------------------------------------------------ #
    #  Confirm action                                                     #
    # ------------------------------------------------------------------ #
    def action_confirm_dual_accommodation(self):
        """Proceed with booking despite an existing contract, using approval."""
        self.ensure_one()

        if not self.approval_number or not self.approval_number.strip():
            raise ValidationError(
                _(
                    "Please enter the Chairman Approval Number before confirming "
                    "dual accommodation."
                )
            )

        vals = {
            "partner_type": self.partner_type,
            "occupant_id": self.occupant_id.id,
            "property_id": self.property_id.id,
            "start_date": self.start_date,
            "expected_end_date": self.expected_end_date,
            "note": self.note,
            "state": "draft",
            # Store approval reference so it is visible on the contract
            "dual_accommodation_approval_number": self.approval_number,
            "dual_accommodation_notes": self.approval_notes or "",
        }

        if self.sale_lease == "bachelor":
            if not self.bed_id:
                raise ValidationError(
                    _("Bed must be selected for bachelor accommodation.")
                )
            vals["bed_id"] = self.bed_id.id

        # Link documents via Many2many field on the occupy record
        if self.approval_document_ids:
            vals["dual_accommodation_document_ids"] = [
                (6, 0, self.approval_document_ids.ids)
            ]

        occupy = self.env["occupy.details"].create(vals)

        # Post a note on the contract chatter for audit trail
        occupy.message_post(
            body=_(
                "<b>Dual Accommodation Approved</b><br/>"
                "Chairman Approval No.: <b>%(number)s</b><br/>"
                "%(notes)s",
                number=self.approval_number,
                notes=self.approval_notes or "",
            ),
            subject=_("Dual Accommodation — Chairman Approval"),
            message_type="comment",
            subtype_xmlid="mail.mt_note",
        )

        # Create utility readings for family accommodation
        if self.is_readings_required:
            self._create_property_readings(occupy)

        return {
            "type": "ir.actions.act_window",
            "name": _("Occupy Contract"),
            "res_model": "occupy.details",
            "res_id": occupy.id,
            "view_mode": "form",
            "target": "current",
        }

    # ------------------------------------------------------------------ #
    #  Helper                                                             #
    # ------------------------------------------------------------------ #
    def _create_property_readings(self, occupy):
        """Mirror of OccupyWizard._create_property_readings."""
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
