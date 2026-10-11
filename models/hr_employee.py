from odoo import fields, models, api


class HrEmployee(models.Model):
    _name = "hr.employee"
    _inherit = ["hr.employee"]

    employee_code = fields.Char("Employee's Code")
    occupy_ids = fields.One2many("occupy.details", "employee_id")
    occupy_id = fields.Many2one("occupy.details", compute="_compute_occupy_id")

    @api.depends("occupy_ids")
    def _compute_occupy_id(self):
        for rec in self:
            running_ids = rec.occupy_ids.filtered(lambda o: o.state == "running")
            if len(running_ids) > 1:
                rec.occupy_id = running_ids[0]
            else:
                rec.occupy_id = running_ids

    def name_get(self):
        result = []
        for employee in self:
            name = employee.name
            if employee.employee_code:
                name = f"{name} [{employee.employee_code}]"
            result.append((employee.id, name))
        return result

    @api.model
    def name_search(self, name="", args=None, operator="ilike", limit=100):
        args = args or []
        domain = []
        if name:
            domain = ["|", ("name", operator, name), ("employee_code", operator, name)]
        return self.search(domain + args, limit=limit).name_get()
