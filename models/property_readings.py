from odoo import models, fields


class PropertyWaterReadings(models.Model):
    _name = "property.water.readings"
    _description = "Property Water Readings"

    name = fields.Float("Reading (m³)", required=True)
    property_details_id = fields.Many2one(
        "property.details", required=True, string="Property"
    )
    reference = fields.Char("Ref.")
    reading_date = fields.Datetime("Reading Date/Time", required=True)


class PropertyElectricityReadings(models.Model):
    _name = "property.electricity.readings"
    _description = "Property Electricity Readings"

    name = fields.Float("Reading (kWh)", required=True)
    property_details_id = fields.Many2one(
        "property.details", required=True, string="Property"
    )
    reference = fields.Char("Ref.")
    reading_date = fields.Datetime("Reading Date/Time", required=True)
