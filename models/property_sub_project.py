# -*- coding: utf-8 -*-
# Copyright 2026-Baramej®.
# Part of Baramej®. See LICENSE file for full copyright and licensing details.
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class PropertySubProject(models.Model):
    """Property sub projects"""

    _name = "property.sub.project"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Property Sub Project Details"

    # Sub Project Details
    name = fields.Char(string="Name", required=True, translate=True)
    project_sequence = fields.Char(string="Code", required=True)
    image_1920 = fields.Image(string="Image")
    property_project_id = fields.Many2one("property.project", string="Project")
    landlord_id = fields.Many2one(
        "res.partner",
        store=True,
        related="property_project_id.landlord_id",
        string="Landlord",
    )
    project_for = fields.Selection(
        related="property_project_id.project_for", store=True
    )
    status = fields.Selection(
        [
            ("draft", "Draft"),
            ("available", "Available"),
            ("cancel", "Cancel"),
            ("closed", "Closed"),
        ],
        default="draft",
    )
    property_type = fields.Selection(
        [
            ("land", "Land"),
            ("residential", "Residential"),
            ("commercial", "Commercial"),
            ("industrial", "Industrial"),
        ],
        string="Property Type",
    )
    property_subtype_id = fields.Many2one(
        "property.sub.type",
        string="Property Subtype",
        domain="[('type','=',property_type)]",
    )

    # Company & Currency
    company_id = fields.Many2one(
        "res.company",
        related="property_project_id.company_id",
        string="Company",
        required=True,
    )
    currency_id = fields.Many2one(
        "res.currency", related="property_project_id.currency_id", string="Currency"
    )

    # Address
    region_id = fields.Many2one(
        "property.region",
        string="Region",
        store=True,
        related="property_project_id.region_id",
    )
    street = fields.Char(string="Street", translate=True)
    street2 = fields.Char(string="Street2")
    city_id = fields.Many2one("property.res.city", string="City")
    state_id = fields.Many2one(
        "res.country.state", string="State", domain="[('country_id', '=?', country_id)]"
    )
    zip = fields.Char(string="Zip", translate=True)
    country_id = fields.Many2one("res.country", string="Country")

    # Lat Long
    longitude = fields.Char(string="Longitude", related="property_project_id.longitude")
    latitude = fields.Char(string="Latitude", related="property_project_id.latitude")

    # Additional Details
    date_of_project = fields.Date(
        related="property_project_id.date_of_project",
        store=True,
        string="Date of Project",
    )
    property_brochure = fields.Binary(string="Brochure")
    brochure_name = fields.Char(string="Brochure Name")
    construction_year = fields.Char(
        string="Construction Year", related="property_project_id.construction_year"
    )
    website = fields.Char(string="Website", related="property_project_id.website")

    # Documents
    document_ids = fields.One2many("subproject.document", "subproject_id")

    # Availability
    avail_description = fields.Boolean(string="Descriptions")
    avail_amenity = fields.Boolean(string="Amenities")
    avail_specification = fields.Boolean(string="Specifications")
    avail_image = fields.Boolean(string="Images")
    avail_nearby_connectivity = fields.Boolean(string="Nearby Connectivity")

    # Property Units
    property_unit_ids = fields.One2many("property.details", "subproject_id")
    floor_created = fields.Integer()

    # Basic Details
    sale_lease = fields.Selection(
        [
            ("rent", "Rent"),
            ("sale", "Sale"),
            ("employee_family", "Employee Family Accommodation"),
            ("bachelor", "Bachelor Accommodation"),
        ],
        string="Sale Lease",
        default="rent",
    )
    total_floors = fields.Integer(string="Total Floors")
    units_per_floor = fields.Integer(string="Units per Floor")
    total_area = fields.Float(
        string="Total Property Area", compute="compute_properties_statics"
    )
    available_area = fields.Float(
        string="Available Area", compute="compute_properties_statics"
    )
    total_values = fields.Monetary(
        string="Total Value of Project", compute="compute_properties_statics"
    )
    total_maintenance = fields.Monetary(
        string="Total Maintenance", compute="compute_properties_statics"
    )
    total_collection = fields.Monetary(
        string="Total Collection", compute="compute_properties_statics"
    )
    scope_of_collection = fields.Monetary(
        string="Scope of Collection", compute="compute_properties_statics"
    )

    # Description
    description = fields.Html(string="Description")

    # Amenities
    subproject_amenity_ids = fields.Many2many("property.amenities")

    # Specifications
    subproject_specification_ids = fields.Many2many("property.specification")

    # Images
    subproject_image_ids = fields.One2many(
        "subproject.images.line", "subproject_id", string="images"
    )

    # Nearby Connectivity
    subproject_connectivity_ids = fields.One2many(
        "subproject.connectivity.line", "subproject_id"
    )

    # Count
    document_count = fields.Integer(compute="compute_count")
    unit_count = fields.Integer(compute="compute_count")
    available_unit_count = fields.Integer(compute="compute_count")
    sold_count = fields.Integer(compute="compute_count")
    rent_count = fields.Integer(compute="compute_count")

    # On delete
    @api.ondelete(at_uninstall=False)
    def _unlink_property_sub_project(self):
        """Prevent inlink property sub project"""
        for rec in self:
            if rec.property_unit_ids:
                raise ValidationError(
                    _(
                        "Cannot delete subproject, please delete "
                        "corresponding units before deletion"
                    )
                )

    # Compute
    # Count
    def compute_count(self):
        """Compute count"""
        for rec in self:
            rec.document_count = self.env["subproject.document"].search_count(
                [("subproject_id", "in", [rec.id])]
            )
            rec.unit_count = self.env["property.details"].search_count(
                [("subproject_id", "in", [rec.id])]
            )
            rec.available_unit_count = self.env["property.details"].search_count(
                [("subproject_id", "in", [rec.id]), ("stage", "=", "available")]
            )
            rec.sold_count = self.env["property.details"].search_count(
                [("subproject_id", "in", [rec.id]), ("stage", "in", ["sale", "sold"])]
            )
            rec.rent_count = self.env["property.details"].search_count(
                [("subproject_id", "in", [rec.id]), ("stage", "=", "on_lease")]
            )

    # Valuation Calculation
    @api.depends("sale_lease")
    def compute_properties_statics(self):
        """Compute properties statics"""
        for rec in self:
            total_area = 0.0
            available_area = 0.0
            total_values = 0.0
            total_maintenance = 0.0
            total_collection = 0.0
            scope_of_collection = 0.0
            properties = self.env["property.details"].sudo()
            project_domain = [("subproject_id", "in", [rec.id])]
            properties_ids = (
                self.env["property.details"].sudo().search(project_domain).mapped("id")
            )
            properties_sale = (
                self.env["property.vendor"]
                .sudo()
                .search([("property_id", "in", properties_ids)])
            )
            properties_tenancy = (
                self.env["tenancy.details"]
                .sudo()
                .search([("property_id", "in", properties_ids)])
            )
            if rec.sale_lease == "sale":
                sale_domain = project_domain + [("sale_lease", "=", "for_sale")]
                total_area = sum(properties.search(sale_domain).mapped("total_area"))
                available_area = sum(
                    properties.search(
                        sale_domain + [("stage", "=", "available")]
                    ).mapped("total_area")
                )
                total_values = sum(properties.search(sale_domain).mapped("price"))
                total_maintenance = sum(
                    properties.search(
                        sale_domain + [("is_maintenance_service", "=", True)]
                    ).mapped("total_maintenance")
                )
                total_collection = sum(properties_sale.mapped("paid_amount"))
                scope_of_collection = sum(properties_sale.mapped("remaining_amount"))
            if rec.sale_lease == "rent":
                tenancy_domain = [("sale_lease", "=", "for_tenancy")] + project_domain
                total_area = sum(properties.search(tenancy_domain).mapped("total_area"))
                available_area = sum(
                    properties.search(
                        tenancy_domain + [("stage", "=", "available")]
                    ).mapped("total_area")
                )
                total_values = sum(properties.search(tenancy_domain).mapped("price"))
                total_maintenance = sum(
                    properties.search(
                        tenancy_domain + [("is_maintenance_service", "=", True)]
                    ).mapped("total_maintenance")
                )
                total_collection = sum(properties_tenancy.mapped("paid_tenancy"))
                scope_of_collection = sum(properties_tenancy.mapped("remain_tenancy"))
            rec.total_area = total_area
            rec.available_area = available_area
            rec.total_values = total_values
            rec.total_maintenance = total_maintenance
            rec.total_collection = total_collection
            rec.scope_of_collection = scope_of_collection

    # Onchange
    # Property Project info
    @api.onchange("property_project_id")
    def _onchange_property_project_id(self):
        """Onchange property project data"""
        self.street = self.property_project_id.street
        self.street2 = self.property_project_id.street2
        self.city_id = self.property_project_id.city_id.id
        self.state_id = self.property_project_id.state_id
        self.zip = self.property_project_id.zip
        self.country_id = self.property_project_id.country_id
        self.total_floors = self.property_project_id.total_floors
        self.total_area = self.property_project_id.total_area
        self.available_area = self.property_project_id.available_area
        self.property_brochure = self.property_project_id.property_brochure
        self.brochure_name = self.property_project_id.brochure_name
        self.property_type = self.property_project_id.property_type
        self.property_subtype_id = self.property_project_id.property_subtype_id

    @api.onchange("country_id")
    def _onchange_country_id(self):
        """Empty state on change country"""
        if self.country_id and self.country_id != self.state_id.country_id:
            self.state_id = False

    @api.onchange("state_id")
    def _onchange_state(self):
        """Get country bases on state"""
        if self.state_id.country_id:
            self.country_id = self.state_id.country_id

    # Property Sub Type Domain
    @api.onchange("property_type")
    def onchange_property_sub_type(self):
        """Onchange property sub type"""
        for rec in self:
            rec.property_subtype_id = False

    # Action Button
    # Smart Button
    def action_document_count(self):
        """View associated documents"""
        return {
            "name": "Documents",
            "type": "ir.actions.act_window",
            "view_mode": "kanban,list,form",
            "context": {"default_subproject_id": self.id},
            "domain": [("subproject_id", "=", self.id)],
            "res_model": "subproject.document",
            "target": "current",
        }

    def action_view_unit(self):
        """View associated units"""
        return {
            "name": "Units",
            "type": "ir.actions.act_window",
            "domain": [("subproject_id", "=", self.id)],
            "view_mode": "list,form",
            "context": {"create": False},
            "res_model": "property.details",
            "target": "current",
        }

    def action_view_available_unit(self):
        """View available units"""
        return {
            "name": "Available Units",
            "type": "ir.actions.act_window",
            "domain": [("subproject_id", "=", self.id), ("stage", "=", "available")],
            "view_mode": "list,form",
            "context": {"create": False},
            "res_model": "property.details",
            "target": "current",
        }

    def action_view_sold_unit(self):
        """View sold units"""
        return {
            "name": "Sold / Sale Units",
            "type": "ir.actions.act_window",
            "domain": [
                ("subproject_id", "=", self.id),
                ("stage", "in", ["sold", "sale"]),
            ],
            "view_mode": "list,form",
            "context": {"create": False},
            "res_model": "property.details",
            "target": "current",
        }

    def action_view_rent_unit(self):
        """View rent units"""
        return {
            "name": "Rent Units",
            "type": "ir.actions.act_window",
            "domain": [("subproject_id", "=", self.id), ("stage", "=", "on_lease")],
            "view_mode": "list,form",
            "context": {"create": False},
            "res_model": "property.details",
            "target": "current",
        }

    # G-map Location
    def action_gmap_location(self):
        """Google map location bases on longitude and latitude"""
        if self.longitude and self.latitude:
            longitude = self.longitude
            latitude = self.latitude
            http_url = (
                "https://maps.google.com/maps?q=loc:" + latitude + "," + longitude
            )
            return {
                "type": "ir.actions.act_url",
                "target": "new",
                "url": http_url,
            }
        else:
            raise ValidationError("! Enter Proper Longitude and Latitude Values")

    # Status
    def action_status_draft(self):
        """Status : Draft"""
        self.status = "draft"

    def action_status_available(self):
        """Status : Available"""
        if not self.property_unit_ids:
            raise ValidationError(_("Please Create Units !"))
        self.status = "available"


# SubProject Document
class SubProjectDocument(models.Model):
    """Sub project documents"""

    _name = "subproject.document"
    _description = "Documents for Sub Project"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(string="Name", required=True)
    document_name = fields.Char(string="Document Name")
    document_file = fields.Binary(string="Document", required=True)
    user_id = fields.Many2one(
        "res.users",
        string="Added by",
        required=True,
        domain=lambda self: [
            ("all_group_ids", "in", self.env.ref("base.group_user").id)
        ],
    )
    subproject_id = fields.Many2one("property.sub.project")


# Project Connectivity Line
class SubprojectConnectivityLine(models.Model):
    """Sub project connectivity line"""

    _name = "subproject.connectivity.line"
    _description = "Sub Project Connectivity Line"

    subproject_id = fields.Many2one("property.sub.project")
    connectivity_id = fields.Many2one(
        "property.connectivity", string="Nearby Connectivity"
    )
    name = fields.Char(string="Name", translate=True)
    image = fields.Image(related="connectivity_id.image", string="Images")
    distance = fields.Char(string="Distance", translate=True)


# Property Images
class ProjectImagesLine(models.Model):
    """Subproject image line"""

    _name = "subproject.images.line"
    _description = "Subproject Image Line"
    _inherit = ["image.mixin"]
    _order = "sequence, id"

    title = fields.Char(string="Title", translate=True)
    sequence = fields.Integer(default=10)
    subproject_id = fields.Many2one("property.sub.project")
    image = fields.Image(string="Images")
