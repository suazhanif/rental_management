import io
import xlsxwriter
import base64
from odoo import _, api, fields, models


class OccupancyReportWizard(models.TransientModel):
    _name = "occupancy.report.wizard"
    _description = "Occupancy Report Wizard"

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
    stage = fields.Selection(
        [("draft", "Draft"), ("available", "Available"), ("booked", "In Booking"),
         ("on_lease", "On Rent"), ("sale", "In Sale"), ("sold", "Sold")],
        string="Status",
    )
    only_occupied = fields.Boolean(string="Only Occupied Units", default=False)
    file_name = fields.Char(string="File Name", readonly=True)
    report_file = fields.Binary(string="Report", readonly=True)

    def _get_domain(self):
        domain = [("sale_lease", "=", "for_tenancy")]
        if self.property_project_id:
            domain.append(("property_project_id", "=", self.property_project_id.id))
        if self.subproject_id:
            domain.append(("subproject_id", "=", self.subproject_id.id))
        if self.floor:
            domain.append(("floor", "=", self.floor))
        if self.property_type:
            domain.append(("type", "=", self.property_type))
        if self.stage:
            domain.append(("stage", "=", self.stage))
        if self.only_occupied:
            domain.append(("stage", "=", "on_lease"))
        return domain

    def action_generate_report(self):
        self.ensure_one()
        properties = self.env["property.details"].sudo().search(self._get_domain())

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        sheet = workbook.add_worksheet("Occupancy Report")

        header_format = workbook.add_format({
            "bold": True, "bg_color": "#714B67", "font_color": "#FFFFFF",
            "border": 1, "align": "center", "valign": "vcenter",
        })
        cell_format = workbook.add_format({"border": 1, "valign": "vcenter"})
        money_format = workbook.add_format({"border": 1, "valign": "vcenter", "num_format": "#,##0.000"})
        date_format = workbook.add_format({"border": 1, "valign": "vcenter", "num_format": "dd-mm-yyyy"})

        headers = [
            "Unit No.", "Building", "Floor", "Tenant Name", "Area (SQM)", "Unit Type",
            "Move in Date", "Lease From", "Lease To", "Payment Term", "Rent / Month",
        ]
        for col, h in enumerate(headers):
            sheet.write(0, col, h, header_format)
            sheet.set_column(col, col, 18)

        payment_term_labels = dict(
            self.env["tenancy.details"]._fields["payment_term"].selection
        )

        row = 1
        for prop in properties:
            contract = self.env["tenancy.details"].sudo().search(
                [("property_id", "=", prop.id), ("contract_type", "=", "running_contract")],
                limit=1, order="start_date desc",
            )
            sheet.write(row, 0, prop.building_no or prop.name, cell_format)
            sheet.write(row, 1, prop.subproject_id.name or "", cell_format)
            sheet.write(row, 2, prop.floor or 0, cell_format)
            sheet.write(row, 3, contract.tenancy_id.name if contract else "", cell_format)
            sheet.write(row, 4, prop.total_area or 0.0, money_format)
            sheet.write(row, 5, prop.property_subtype_id.name or "", cell_format)
            if contract:
                sheet.write_datetime(row, 6, contract.start_date, date_format) if contract.start_date else sheet.write(row, 6, "", cell_format)
                sheet.write_datetime(row, 7, contract.start_date, date_format) if contract.start_date else sheet.write(row, 7, "", cell_format)
                sheet.write_datetime(row, 8, contract.end_date, date_format) if contract.end_date else sheet.write(row, 8, "", cell_format)
                sheet.write(row, 9, payment_term_labels.get(contract.payment_term, ""), cell_format)
                sheet.write(row, 10, contract.total_rent or 0.0, money_format)
            else:
                for col in range(6, 10):
                    sheet.write(row, col, "-", cell_format)
                sheet.write(row, 10, "-", cell_format)
            row += 1

        workbook.close()
        output.seek(0)
        self.write({
            "report_file": base64.b64encode(output.read()),
            "file_name": "Occupancy_Report.xlsx",
        })
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/?model=occupancy.report.wizard&id={self.id}&field=report_file&filename_field=file_name&download=true",
            "target": "self",
        }