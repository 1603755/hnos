from odoo import models, fields

class FleetVehicleLogServices(models.Model):
    _inherit = 'fleet.vehicle.log.services'
    
    running_time = fields.Float(compute='_get_running_time', inverse='_set_running_time', string='Last Running Time',
        help='Running time measure of the vehicle at the moment of this log')
    running_time_unit = fields.Selection([
        ('hours', 'h'),
        ('days', 'd')
        ], 'Runing Time Unit', default='hours', help='Unit of the running time counter')
    maintenance_type = fields.Selection(related='vehicle_id.model_id.maintenance_type')
    maintenance_plan = fields.Many2one(related = 'vehicle_id.model_id.maintenance_plan')
    model_id = fields.Many2one(comodel_name='fleet.vehicle.model',related='vehicle_id.model_id')
    
    def _get_running_time(self):
        FleetVehicleRunningTime = self.env['fleet.vehicle.running.time']
        for record in self:
            vehicle_running_time = FleetVehicleRunningTime.search([('vehicle_id', '=', record.id)], limit=1, order='value desc')
            if vehicle_running_time:
                record.running_time = vehicle_running_time.value
            else:
                record.running_time = 0

    def _set_running_time(self):
        for record in self:
            if record.running_time:
                date = fields.Date.context_today(record)
                data = {'value': record.running_time, 'date': date, 'vehicle_id': record.vehicle_id.id}
                self.env['fleet.vehicle.running.time'].create(data)