from odoo import models, fields, api
from datetime import timedelta

class FleetMaintenancePlan(models.Model):
    _name = 'fleet.maintenance.plan'
    
    name = fields.Char(required=True)
    maintenance_type = fields.Selection([
        ('odometer', 'Odometer'),
        ('running_time', 'Running time')
        ], 'Maintenance type', default='odometer', help='Type of maintenance for the vehicle', required=True)
    models = fields.One2many(comodel_name='fleet.vehicle.model', inverse_name = 'maintenance_plan', domain="[('maintenance_type','=',maintenance_type)]",string='Models')
    maintenance_lines = fields.One2many(comodel_name='fleet.maintenance.plan.line', inverse_name='plan', string='Plan lines')
    
    @api.onchange('maintenance_type')
    def _onchange_mant_type(self):
        if self.maintenance_type != self._origin.maintenance_type:
            for line in self.maintenance_lines:
                line.periodicity_unit = False
                
#FIXME: No debe poder repetirse líneas con el mismo tipo de servicio
        
class FleetMaintenancePlanLine(models.Model):
    _name = 'fleet.maintenance.plan.line'
    
    display_name = fields.Char(related='service_type.name')
    service_type = fields.Many2one(comodel_name='fleet.service.type', string='Service type', required=True)
    periodicity = fields.Integer(required=True)
    periodicity_unit = fields.Many2one(comodel_name='uom.uom', string='Periodicity Unit',help='Months and years relate to elapsed time.', required=True)
    plan = fields.Many2one(comodel_name='fleet.maintenance.plan', string='Maintenance plan')
    maintenance_type = fields.Selection(related='plan.maintenance_type')
    periodicity_unit_domain = fields.Char(compute='_compute_unit_domain')
    
    @api.depends('maintenance_type')
    def _compute_unit_domain(self):
        for record in self:
            if record.maintenance_type == 'odometer' or False:
                record.periodicity_unit_domain = '[ ["name","in", ["km", "mi", "Meses", "Años"]] ]'
                pass
            else:
                record.periodicity_unit_domain = '[ ["name","in", ["Horas", "Días", "Meses", "Años"] ] ]'
    
    def get_next_service(self,vehicle):
        last_service = self.env['fleet.vehicle.log.services'].search([('service_type_id','=',self.service_type.id),
                                                                      ('vehicle_id','=',vehicle.id),
                                                                      ('state','in',['done','running'])],
                                                                            limit=1,order ='date desc')
        reference_uom = self.env['uom.uom'].search([('category_id','=',self.periodicity_unit.category_id.id),
                                                    ('uom_type','=','reference')])
        if self.periodicity_unit in [self.env.ref('fleet_maintenance.product_uom_month'),self.env.ref('fleet_maintenance.product_uom_year')]:
            if last_service:
                previous_date = last_service.date
            elif vehicle.next_assignation_date:
                previous_date = vehicle.next_assignation_date
            else:
                previous_date = vehicle.first_contract_date
            next_service = previous_date + timedelta(days=self.periodicity_unit._compute_quantity(self.periodicity, reference_uom))
            service_type = 'date'
        else:
            service_type = 'usage'
            if self.maintenance_type == 'odometer':
                if last_service:
                    previous_value = self._get_oum_unit(last_service.odometer_unit)._compute_quantity(last_service.odometer, reference_uom)
                else:
                    previous_value = 0
                next_service = previous_value + self.periodicity_unit._compute_quantity(self.periodicity, reference_uom)
            else:
                if last_service:
                    previous_value = self._get_oum_unit(last_service.running_time_unit)._compute_quantity(last_service.running_time, reference_uom)
                else:
                    previous_value = 0
                next_service = previous_value + self.periodicity_unit._compute_quantity(self.periodicity, reference_uom)
        return next_service,service_type
    
    def _get_oum_unit(self,unit_str):
        unit_map = {'kilometers': 'km', 'miles': 'mi','hours': 'Horas', 'days': 'Días'}
        unit = self.env['uom.uom'].search([('name','=',unit_map[unit_str])])
        return unit
