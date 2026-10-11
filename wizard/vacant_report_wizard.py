import io
import xlsxwriter
import base64
from odoo import _, api, fields, models


class VacantReportWizard(models.TransientModel):
    _name = "vacant.report.wizard"
    _description = "Vacant Report Wizard"

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
    file_name = fields.Char(string="File Name", readonly=True)
    report_file = fields.Binary(string="Report", readonly=True)

    def _get_domain(self):
        domain = [
            ("sale_lease", "=", "for_tenancy"),
            ("stage", "=", "available"),
        ]
        if self.property_project_id:
            domain.append(("property_project_id", "=", self.property_project_id.id))
        if self.subproject_id:
            domain.append(("subproject_id", "=", self.subproject_id.id))
        if self.floor:
            domain.append(("floor", "=", self.floor))
        if self.property_type:
            domain.append(("type", "=", self.property_type))
        return domain

    def action_generate_report(self):
        self.ensure_one()
        properties = self.env["property.details"].sudo().search(self._get_domain())

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        sheet = workbook.add_worksheet("Vacant Report")

        header_format = workbook.add_format({
            "bold": True, "bg_color": "#714B67", "font_color": "#FFFFFF",
            "border": 1, "align": "center", "valign": "vcenter",
        })
        cell_format = workbook.add_format({"border": 1, "valign": "vcenter"})
        date_format = workbook.add_format({"border": 1, "valign": "vcenter", "num_format": "dd-mm-yyyy"})

        headers = [
            "Unit No.", "Tenant Name", "Area (SQM)", "Unit Type",
            "Vacant From", "Description",
        ]
        widths = [14, 14, 12, 16, 14, 28]
        for col, h in enumerate(headers):
            sheet.write(0, col, h, header_format)
            sheet.set_column(col, col, widths[col])

        row = 1
        for prop in properties:
            last_contract = self.env["tenancy.details"].sudo().search(
                [
                    ("property_id", "=", prop.id),
                    ("contract_type", "in", ("close_contract", "cancel_contract", "expire_contract")),
                    ("terminate_date", "!=", False),
                ],
                limit=1, order="terminate_date desc",
            )

            sheet.write(row, 0, prop.building_no or prop.name, cell_format)
            sheet.write(row, 1, "Vacant", cell_format)
            sheet.write(row, 2, prop.total_area or 0.0, cell_format)
            sheet.write(row, 3, prop.property_subtype_id.name or "", cell_format)
            if last_contract and last_contract.terminate_date:
                sheet.write_datetime(row, 4, last_contract.terminate_date, date_format)
            else:
                sheet.write(row, 4, "", cell_format)
            sheet.write(row, 5, "", cell_format)
            row += 1

        workbook.close()
        output.seek(0)
        self.write({
            "report_file": base64.b64encode(output.read()),
            "file_name": "Vacant_Report.xlsx",
        })
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/?model=vacant.report.wizard&id={self.id}&field=report_file&filename_field=file_name&download=true",
            "target": "self",
        }