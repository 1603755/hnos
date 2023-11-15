from odoo import models,fields

class FieldVehicleLogFuel(models.Model):
    _inherit = 'fleet.vehicle.log.fuel'
    
    service_type_id = fields.Many2one(
        "fleet.service.type",
        "Service Type",
        required=True,
        default=lambda self: self.env.ref(
            "fleet_maintenance.type_service_refueling", raise_if_not_found=False
        ),
    )