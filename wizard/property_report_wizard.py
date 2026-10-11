import io
import xlsxwriter
import base64
from odoo import _, api, fields, models

AMENITY_FIELD_ORDER = [
    ("gym", "Gym"), ("wifi", "WiFi"), ("pool", "Pool"), ("parking", "Parking"),
    ("security", "Security"), ("laundry_room", "Laundry Room"),
    ("equipped_kitchen", "Equipped Kitchen"), ("air_conditioned", "Air Conditioned"),
    ("semi_furnished", "Semi Furnished"), ("full_furnished", "Full Furnished"),
    ("safety_alarm", "Safety Alarm"), ("window_covering", "Window Covering"),
]
# NOTE: rental_management.property.amenities is a master list (title/image),
# matched to a property via the M2M `amenities_ids`. There's no boolean field
# per amenity name on property.details itself. Below we match by amenity
# TITLE against amenities_ids — adjust the titles list if your master data
# uses different wording.
AMENITY_TITLES = [label for _key, label in AMENITY_FIELD_ORDER]


class PropertyReportWizard(models.TransientModel):
    _name = "property.report.wizard"
    _description = "Property Report Wizard"

    property_project_id = fields.Many2one("property.project", string="Compound")
    subproject_id = fields.Many2one(
        "property.sub.project", string="Building",
        domain="[('property_project_id', '=', property_project_id)]",
    )
    property_type = fields.Selection(
        [("land", "Land"), ("residential", "Residential"),
         ("commercial", "Commercial"), ("industrial", "Industrial")],
        string="Property Type",
    )
    sale_lease = fields.Selection(
        [("for_sale", "Sale"), ("employee_family", "Employee Family Accommodation"),
         ("bachelor", "Bachelor Accommodation"), ("for_tenancy", "Rent")],
        string="Property For",
    )
    stage = fields.Selection(
        [("draft", "Draft"), ("available", "Available"), ("booked", "In Booking"),
         ("on_lease", "On Rent"), ("sale", "In Sale"), ("sold", "Sold")],
        string="Status",
    )
    file_name = fields.Char(string="File Name", readonly=True)
    report_file = fields.Binary(string="Report", readonly=True)

    def _get_domain(self):
        domain = []
        if self.property_project_id:
            domain.append(("property_project_id", "=", self.property_project_id.id))
        if self.subproject_id:
            domain.append(("subproject_id", "=", self.subproject_id.id))
        if self.property_type:
            domain.append(("type", "=", self.property_type))
        if self.sale_lease:
            domain.append(("sale_lease", "=", self.sale_lease))
        if self.stage:
            domain.append(("stage", "=", self.stage))
        return domain

    def action_generate_report(self):
        self.ensure_one()
        properties = self.env["property.details"].sudo().search(self._get_domain())

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        sheet = workbook.add_worksheet("Property Report")

        header_format = workbook.add_format({
            "bold": True, "bg_color": "#714B67", "font_color": "#FFFFFF",
            "border": 1, "align": "center", "valign": "vcenter",
        })
        cell_format = workbook.add_format({"border": 1, "valign": "vcenter"})
        money_format = workbook.add_format({"border": 1, "valign": "vcenter", "num_format": "#,##0.000"})
        date_format = workbook.add_format({"border": 1, "valign": "vcenter", "num_format": "dd-mm-yyyy"})
        bool_format = workbook.add_format({"border": 1, "valign": "vcenter", "align": "center"})

        base_headers = [
            "Unit Name", "Unit Code", "Building", "Building Code", "Property Type",
            "Property Sub Type", "Property For", "LandLord", "Assigned Officers",
            "Street No.", "Region", "City", "Latitude", "Longitude", "No of Floors",
            "Floor", "Beds", "Bathrooms", "Furnishing", "Pricing Type", "Price",
            "Water Account No.", "Latest Water Reading", "Electricity Account No.",
            "Latest Electricity Reading", "Company", "Country", "Status",
            "Employee's Grade", "Bachelor Beds Generated", "Website Description",
            "Short Description",
        ]
        amenity_headers = [label for _key, label in AMENITY_FIELD_ORDER]
        headers = base_headers + amenity_headers + ["Accommodation"]

        stage_labels = dict(self.env["property.details"]._fields["stage"].selection)
        sale_lease_labels = dict(self.env["property.details"]._fields["sale_lease"].selection)
        pricing_type_labels = dict(self.env["property.details"]._fields["pricing_type"].selection)

        for col, h in enumerate(headers):
            sheet.write(0, col, h, header_format)
            sheet.set_column(col, col, 16)

        row = 1
        for prop in properties:
            col = 0

            def w(val, fmt=cell_format):
                nonlocal col
                sheet.write(row, col, val, fmt)
                col += 1

            w(prop.name or "")
            w(prop.property_seq or "")
            w(prop.subproject_id.name or "")
            w(prop.subproject_id.project_sequence or "")
            w(dict(prop._fields["type"].selection).get(prop.type, ""))
            w(prop.property_subtype_id.name or "")
            w(sale_lease_labels.get(prop.sale_lease, ""))
            w(prop.landlord_id.name or "")
            w(", ".join(prop.user_ids.mapped("name")))
            w(prop.street or "")
            w(prop.region_id.name or "")
            w(prop.city_id.name or "")
            w(prop.latitude or "")
            w(prop.longitude or "")
            w(prop.total_floor or 0)
            w(prop.floor or 0)
            w(prop.bed or 0)
            w(prop.bathroom or 0)
            w(prop.furnishing_id.name or "")
            w(pricing_type_labels.get(prop.pricing_type, ""))
            w(prop.price or 0.0, money_format)
            w(prop.utility_water_account_no or "")
            w(prop.water_readings_id.name if prop.water_readings_id else "")
            w(prop.utility_electricity_account_no or "")
            w(prop.electricity_readings_id.name if prop.electricity_readings_id else "")
            w(prop.company_id.name or "")
            w(prop.country_id.name or "")
            w(stage_labels.get(prop.stage, ""))
            w("")  # Employee's Grade — no source field found
            w("TRUE" if prop.bachelor_bed else "FALSE", bool_format)
            w("")  # Website Description — no source field found
            w("")  # Short Description — no source field found

            amenity_titles_on_property = set(prop.amenities_ids.mapped("title"))
            for label in amenity_headers:
                is_present = label in amenity_titles_on_property
                w("TRUE" if is_present else "FALSE", bool_format)

            w("")  # Accommodation — ambiguous source, left blank

            row += 1

        workbook.close()
        output.seek(0)
        self.write({
            "report_file": base64.b64encode(output.read()),
            "file_name": "Property_Report.xlsx",
        })
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/?model=property.report.wizard&id={self.id}&field=report_file&filename_field=file_name&download=true",
            "target": "self",
        }