from odoo import models, fields, api

class FleetServiceType(models.Model):
    _inherit = 'fleet.service.type'
    
    models = fields.Many2many(comodel_name="fleet.vehicle.model",compute='_compute_models',search='_search_models')
    
    def _compute_models(self):
        maintenance_plans = self.env['fleet.maintenance.plan.line'].search([('service_type','=',self.id)]).mapped('plan')
        self.models = maintenance_plans.mapped('models')
        
    def _search_models(self, operator, value):
        if operator == "=":
            maintenance_plans = self.env['fleet.maintenance.plan'].search([('models','=',value)])
            service_types = maintenance_plans.maintenance_lines.mapped('service_type')
            domain = [('id','in',service_types.ids)]
            return domain
