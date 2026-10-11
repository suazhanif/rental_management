import io
import xlsxwriter
import base64
from odoo import _, api, fields, models


class TenancyListReportWizard(models.TransientModel):
    _name = "tenancy.list.report.wizard"
    _description = "Tenancy List Report Wizard"

    property_project_id = fields.Many2one("property.project", string="Compound")
    subproject_id = fields.Many2one(
        "property.sub.project", string="Building",
        domain="[('property_project_id', '=', property_project_id)]",
    )
    floor = fields.Integer(string="Floor", help="Leave 0 to include all floors.")
    include_rent = fields.Boolean(string="Rent Contracts", default=True)
    include_occupy = fields.Boolean(string="Employee/Bachelor Occupancy", default=True)
    file_name = fields.Char(string="File Name", readonly=True)
    report_file = fields.Binary(string="Report", readonly=True)

    def _property_domain(self):
        domain = []
        if self.property_project_id:
            domain.append(("property_project_id", "=", self.property_project_id.id))
        if self.subproject_id:
            domain.append(("subproject_id", "=", self.subproject_id.id))
        if self.floor:
            domain.append(("floor", "=", self.floor))
        return domain

    def _get_rows(self):
        """Return list of dicts: unit_no, partner (res.partner), employee (hr.employee or False)"""
        rows = []
        prop_domain = self._property_domain()

        if self.include_rent:
            tenancy_domain = [("contract_type", "=", "running_contract")]
            if prop_domain:
                tenancy_domain += [
                    ("property_id.property_project_id", "=", self.property_project_id.id)
                ] if self.property_project_id else []
                if self.subproject_id:
                    tenancy_domain.append(
                        ("property_id.subproject_id", "=", self.subproject_id.id)
                    )
                if self.floor:
                    tenancy_domain.append(("property_id.floor", "=", self.floor))
            contracts = self.env["tenancy.details"].sudo().search(tenancy_domain)
            for c in contracts:
                rows.append({
                    "unit_no": c.property_id.building_no or c.property_id.name,
                    "partner": c.tenancy_id,
                    "employee": False,
                })

        if self.include_occupy:
            occupy_domain = [("state", "=", "running")]
            if self.property_project_id:
                occupy_domain.append(
                    ("property_id.property_project_id", "=", self.property_project_id.id)
                )
            if self.subproject_id:
                occupy_domain.append(("property_id.subproject_id", "=", self.subproject_id.id))
            if self.floor:
                occupy_domain.append(("property_id.floor", "=", self.floor))
            occupations = self.env["occupy.details"].sudo().search(occupy_domain)
            for o in occupations:
                rows.append({
                    "unit_no": o.property_id.building_no or o.property_id.name,
                    "partner": o.occupant_id,
                    "employee": o.employee_id,
                })

        rows.sort(key=lambda r: r["unit_no"] or "")
        return rows

    def action_generate_report(self):
        self.ensure_one()
        rows = self._get_rows()

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        sheet = workbook.add_worksheet("Tenancy List")

        header_format = workbook.add_format({
            "bold": True, "bg_color": "#714B67", "font_color": "#FFFFFF",
            "border": 1, "align": "center", "valign": "vcenter",
        })
        cell_format = workbook.add_format({"border": 1, "valign": "vcenter"})
        date_format = workbook.add_format({"border": 1, "valign": "vcenter", "num_format": "dd-mm-yyyy"})

        headers = [
            "Unit No.", "Name", "Phone", "Email", "ID Card No.", "ID Issue Date",
            "ID Expiry Date", "Passport Expiry Date", "Passport Issue Date",
            "Passport No.", "Company Name", "Landline", "PO Box.", "Street",
            "City", "Job Position",
        ]
        for col, h in enumerate(headers):
            sheet.write(0, col, h, header_format)
            sheet.set_column(col, col, 16)

        row_idx = 1
        for data in rows:
            partner = data["partner"]
            employee = data["employee"]

            company_name = ""
            if partner:
                if partner.is_company:
                    company_name = partner.name
                elif partner.parent_id:
                    company_name = partner.parent_id.name
                elif partner.commercial_company_name:
                    company_name = partner.commercial_company_name

            job_position = ""
            if employee:
                job_position = employee.job_title or employee.job_id.name or ""

            sheet.write(row_idx, 0, data["unit_no"] or "", cell_format)
            sheet.write(row_idx, 1, partner.name if partner else "", cell_format)
            sheet.write(row_idx, 2, partner.phone if partner else "", cell_format)
            sheet.write(row_idx, 3, partner.email if partner else "", cell_format)
            sheet.write(row_idx, 4, partner.id_no if partner else "", cell_format)
            if partner and partner.id_issue_date:
                sheet.write_datetime(row_idx, 5, partner.id_issue_date, date_format)
            else:
                sheet.write(row_idx, 5, "", cell_format)
            if partner and partner.id_expiry_date:
                sheet.write_datetime(row_idx, 6, partner.id_expiry_date, date_format)
            else:
                sheet.write(row_idx, 6, "", cell_format)
            if partner and partner.passport_expiry_date:
                sheet.write_datetime(row_idx, 7, partner.passport_expiry_date, date_format)
            else:
                sheet.write(row_idx, 7, "", cell_format)
            if partner and partner.passport_issue_date:
                sheet.write_datetime(row_idx, 8, partner.passport_issue_date, date_format)
            else:
                sheet.write(row_idx, 8, "", cell_format)
            sheet.write(row_idx, 9, partner.passport_no if partner else "", cell_format)
            sheet.write(row_idx, 10, company_name, cell_format)
            sheet.write(row_idx, 11, partner.phone_landline if partner else "", cell_format)
            sheet.write(row_idx, 12, partner.po_box if partner else "", cell_format)
            sheet.write(row_idx, 13, partner.street if partner else "", cell_format)
            sheet.write(row_idx, 14, partner.city if partner else "", cell_format)
            sheet.write(row_idx, 15, job_position, cell_format)
            row_idx += 1

        workbook.close()
        output.seek(0)
        self.write({
            "report_file": base64.b64encode(output.read()),
            "file_name": "Tenancy_List.xlsx",
        })
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/?model=tenancy.list.report.wizard&id={self.id}&field=report_file&filename_field=file_name&download=true",
            "target": "self",
        }