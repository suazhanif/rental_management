# -*- coding: utf-8 -*-
# Copyright 2026-Baramej®.
# Part of Baramej®. See LICENSE file for full copyright and licensing details.
from dateutil.relativedelta import relativedelta
from odoo import _, api, fields, models


class OccupyDetailsDualApproval(models.Model):
    """Adds dual-accommodation chairman-approval fields to occupy.details,
    and expiry reminders for both dual-accommodation and non-company contracts."""

    _inherit = "occupy.details"

    # Dual Accommodation (Bachelor) Fields
    dual_accommodation_approval_number = fields.Char(
        string="Chairman Approval No.",
        readonly=True,
        copy=False,
        help="Populated automatically when a bed is assigned under dual-accommodation approval.",
    )
    dual_accommodation_notes = fields.Text(
        string="Dual Accommodation Notes",
        readonly=True,
        copy=False,
    )
    dual_accommodation_document_ids = fields.Many2many(
        "ir.attachment",
        "occupy_dual_accom_attachment_rel",
        "occupy_id",
        "attachment_id",
        string="Approval Documents",
        readonly=True,
        copy=False,
        help="Supporting documents submitted with the chairman dual-accommodation approval.",
    )
    is_dual_accommodation = fields.Boolean(
        string="Dual Accommodation",
        compute="_compute_is_dual_accommodation",
        store=True,
        help="True when this contract was created under a chairman dual-accommodation approval.",
    )
    dual_accommodation_reminder_sent = fields.Boolean(
        string="Dual Accommodation Expiry Reminder Sent",
        default=False,
        copy=False,
        help="Prevents sending the one-month-before-expiry reminder more than once.",
    )

    # Non-Company Reminder
    non_company_reminder_sent = fields.Boolean(
        string="Non-Company Expiry Reminder Sent",
        default=False,
        copy=False,
        help="Prevents sending the one-month-before-expiry reminder more than once.",
    )

    @api.depends("dual_accommodation_approval_number")
    def _compute_is_dual_accommodation(self):
        for rec in self:
            rec.is_dual_accommodation = bool(rec.dual_accommodation_approval_number)

    # Mail Reminders
    def action_send_dual_accommodation_expiry_reminder(self):
        """Send dual-accommodation expiry reminder to the responsible user"""
        mail_template = self.env.ref(
            "rental_management.dual_accommodation_expiry_reminder_template",
            raise_if_not_found=False,
        )
        if mail_template:
            mail_template.send_mail(
                self.id,
                email_values={"author_id": self.company_id.partner_id.id},
                force_send=True,
            )

    def action_send_non_company_expiry_reminder(self):
        """Send non-company occupant expiry reminder to the responsible user"""
        mail_template = self.env.ref(
            "rental_management.non_company_expiry_reminder_template",
            raise_if_not_found=False,
        )
        if mail_template:
            mail_template.send_mail(
                self.id,
                email_values={"author_id": self.company_id.partner_id.id},
                force_send=True,
            )

    # Scheduler
    @api.model
    def cron_send_occupy_expiry_reminder(self):
        """Scheduled Action: notify responsible users 1 month before
        (a) a dual-accommodation bachelor bed contract expires, and
        (b) a non-company occupation contract expires."""
        target_date = fields.Date.today() + relativedelta(months=1)

        # Dual Accommodation (Bachelor)
        dual_records = self.sudo().search(
            [
                ("is_dual_accommodation", "=", True),
                ("state", "=", "running"),
                ("expected_end_date", "=", target_date),
                ("dual_accommodation_reminder_sent", "=", False),
            ]
        )
        for rec in dual_records:
            rec.action_send_dual_accommodation_expiry_reminder()
            rec.dual_accommodation_reminder_sent = True

        # Non-Company Occupants
        non_company_records = self.sudo().search(
            [
                ("partner_type", "=", "non_company"),
                ("state", "=", "running"),
                ("expected_end_date", "=", target_date),
                ("non_company_reminder_sent", "=", False),
            ]
        )
        for rec in non_company_records:
            rec.action_send_non_company_expiry_reminder()
            rec.non_company_reminder_sent = True
