# -*- coding: utf-8 -*-
from odoo import api, fields, models


class EmployeeAccommodationSearchWizard(models.TransientModel):
    _name = "employee.accommodation.search.wizard"
    _description = "Employee Accommodation Search Wizard"

    employee_id = fields.Many2one(
        "hr.employee",
        string="Employee",
    )
    employee_code = fields.Char(
        related="employee_id.employee_code",
        string="Employee Code",
        readonly=True,
    )
    name = fields.Char(
        related="employee_id.name",
        string="Name",
        readonly=True,
    )
    department_id = fields.Many2one(
        related="employee_id.department_id",
        string="Department",
        readonly=True,
    )

    def action_search_properties(self):
        """Open properties list view filtered by availability for employee accommodation"""
        self.ensure_one()

        if not self.employee_id:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "type": "warning",
                    "title": "No Employee Selected",
                    "message": "Please select an employee first.",
                    "sticky": False,
                },
            }

        return {
            "type": "ir.actions.act_window",
            "name": "Available Properties for %s" % self.employee_id.name,
            "res_model": "property.details",
            "view_mode": "list,form,kanban",
            "domain": [
                ("stage", "=", "available"),  # Only show available properties
                (
                    "sale_lease",
                    "in",
                    ["employee_family", "bachelor"],
                ),  # Employee accommodations
            ],
            "context": {
                "search_default_available": 1,
            },
            "target": "current",
        }
