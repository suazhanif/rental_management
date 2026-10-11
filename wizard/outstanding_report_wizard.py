import io
import xlsxwriter
import base64
from odoo import _, api, fields, models


class OutstandingReportWizard(models.TransientModel):
    _name = "outstanding.report.wizard"
    _description = "Outstanding Report Wizard"

    property_project_id = fields.Many2one("property.project", string="Compound")
    subproject_id = fields.Many2one(
        "property.sub.project", string="Building",
        domain="[('property_project_id', '=', property_project_id)]",
    )
    floor = fields.Integer(string="Floor", help="Leave 0 to include all floors.")
    property_type = fields.Selection(
        [("land", "Land"), ("residential", "Residential"),
         ("commercial", "Commercial"), ("industrial", "Industrial")],
        string="Property Type",
    )
    only_overdue = fields.Boolean(
        string="Only Overdue", default=False,
        help="Only invoices whose due date has already passed.",
    )
    file_name = fields.Char(string="File Name", readonly=True)
    report_file = fields.Binary(string="Report", readonly=True)

    def _get_domain(self):
        domain = [
            ("tenancy_id", "!=", False),
            ("type", "in", ("rent", "full_rent")),
            ("rent_invoice_id", "!=", False),
            ("rent_invoice_id.state", "=", "posted"),
            ("rent_invoice_id.payment_state", "not in", ("paid", "reversed")),
        ]
        if self.property_project_id:
            domain.append(
                ("tenancy_id.property_project_id", "=", self.property_project_id.id)
            )
        if self.subproject_id:
            domain.append(("tenancy_id.subproject_id", "=", self.subproject_id.id))
        if self.floor:
            domain.append(("tenancy_id.property_id.floor", "=", self.floor))
        if self.property_type:
            domain.append(("tenancy_id.property_type", "=", self.property_type))
        if self.only_overdue:
            domain.append(
                ("rent_invoice_id.invoice_date_due", "<", fields.Date.today())
            )
        return domain

    def action_generate_report(self):
        self.ensure_one()
        rent_invoices = self.env["rent.invoice"].sudo().search(
            self._get_domain(), order="tenancy_id, rent_invoice_id"
        )

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        sheet = workbook.add_worksheet("Outstanding Report")

        header_format = workbook.add_format({
            "bold": True, "bg_color": "#714B67", "font_color": "#FFFFFF",
            "border": 1, "align": "center", "valign": "vcenter",
        })
        cell_format = workbook.add_format({"border": 1, "valign": "vcenter"})
        money_format = workbook.add_format({"border": 1, "valign": "vcenter", "num_format": "#,##0.000"})
        date_format = workbook.add_format({"border": 1, "valign": "vcenter", "num_format": "dd-mm-yyyy"})

        headers = [
            "Unit No.", "Tenant Name", "Rent / Month", "Area (SQM)", "Unit Type",
            "OS Period From", "OS Period To", "Description", "Amount",
        ]
        widths = [14, 22, 12, 12, 16, 14, 14, 28, 14]
        for col, h in enumerate(headers):
            sheet.write(0, col, h, header_format)
            sheet.set_column(col, col, widths[col])

        row = 1
        for line in rent_invoices:
            move = line.rent_invoice_id
            tenancy = line.tenancy_id
            prop = tenancy.property_id
            period_from = move.invoice_date
            period_to = move.invoice_date_due or move.invoice_date

            sheet.write(row, 0, prop.building_no or prop.name, cell_format)
            sheet.write(row, 1, tenancy.tenancy_id.name or "", cell_format)
            sheet.write(row, 2, tenancy.total_rent or 0.0, money_format)
            sheet.write(row, 3, prop.total_area or 0.0, money_format)
            sheet.write(row, 4, prop.property_subtype_id.name or "", cell_format)
            if period_from:
                sheet.write_datetime(row, 5, period_from, date_format)
            else:
                sheet.write(row, 5, "", cell_format)
            if period_to:
                sheet.write_datetime(row, 6, period_to, date_format)
            else:
                sheet.write(row, 6, "", cell_format)
            sheet.write(row, 7, line.description or "", cell_format)
            sheet.write(row, 8, move.amount_residual or 0.0, money_format)
            row += 1

        workbook.close()
        output.seek(0)
        self.write({
            "report_file": base64.b64encode(output.read()),
            "file_name": "Outstanding_Report.xlsx",
        })
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/?model=outstanding.report.wizard&id={self.id}&field=report_file&filename_field=file_name&download=true",
            "target": "self",
        }