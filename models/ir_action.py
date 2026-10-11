from odoo import fields, models


class WindowActionView(models.Model):
    """Window Action"""

    _inherit = "ir.actions.act_window.view"

    view_mode = fields.Selection(
        selection_add=[("tk_map", "Map")], ondelete={"tk_map": "cascade"}
    )
