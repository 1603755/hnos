from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import datetime
import logging 

class FleetVehicleModel(models.Model):
    _inherit = 'fleet.vehicle.model'

    vehicle_type = fields.Selection([('car', 'Car'), ('bike', 'Bike'), ('other', 'Other')], default='car', required=True)
    maintenance_type = fields.Selection([
        ('odometer', 'Odometer'),
        ('running_time', 'Running time'),
        ('none', 'None')
        ], 'Maintenance type', default='odometer', help='Type of maintenance for the vehicle', required=True)
    maintenance_plan = fields.Many2one(comodel_name='fleet.maintenance.plan')

class FleetVehicle(models.Model):
    _inherit = 'fleet.vehicle'
    
    running_time_count = fields.Integer(compute="_compute_running_time_count", string='Running time')
    running_time = fields.Float(compute='_get_running_time', inverse='_set_running_time', string='Last Running Time',
        help='Running time measure of the vehicle at the moment of this log')
    running_time_unit = fields.Selection([
        ('hours', 'h'),
        ('days', 'd')
        ], 'Runing Time Unit', default='hours', help='Unit of the running time counter')
    maintenance_type = fields.Selection(related='model_id.maintenance_type')
    maintenance_plan = fields.Many2one(related = 'model_id.maintenance_plan')
    next_service_date = fields.Many2one(comodel_name='fleet.maintenance.plan.line', compute='_compute_next_service', string='Next service by date')
    next_service_value_date = fields.Float(compute='_compute_next_service',help='Value in months')
    next_service_usage = fields.Many2one(comodel_name='fleet.maintenance.plan.line', compute='_compute_next_service', string='Next service by usage')
    next_service_value_usage = fields.Integer(compute='_compute_next_service')
    
    def _compute_next_service(self):
        for record in self:
            if record.maintenance_plan:
                min_value_date = None
                min_value_usage = None
                next_date_service = False
                next_usage_service = False
                for plan_line in record.maintenance_plan.maintenance_lines:
                    value,service_type = plan_line.get_next_service(record) #Ya me lo da en la reference uom de la categoría
                    if service_type == 'usage':
                        if min_value_usage is None or value < min_value_usage:
                            min_value_usage = value
                            next_usage_service = plan_line
                    else:
                        if min_value_date is None or value < min_value_date:
                            min_value_date = value
                            next_date_service = plan_line
                # COnvertir a unidad de odómetro o rt y restar el valor actual
                if record.maintenance_type == 'odometer':
                    unit_map = {'kilometers': 'km', 'miles': 'mi'}
                    unit = record.env['uom.uom'].search([('name','=',unit_map[record.odometer_unit])])
                    current_value = record.odometer
                elif record.maintenance_type == 'running_time':
                    unit_map = {'hours': 'Horas', 'days': 'Días'}
                    unit = record.env['uom.uom'].search([('name','=',unit_map[record.running_time_unit])])
                    current_value = record.running_time
                reference_uom = record.env['uom.uom'].search([('category_id','=',unit.category_id.id),
                                                        ('uom_type','=','reference')])
                if min_value_usage:
                    record.next_service_value_usage = reference_uom._compute_quantity(min_value_usage, unit) \
                                                    - current_value
                else:
                    record.next_service_value_usage = False
                if min_value_date:
                    record.next_service_value_date = (min_value_date - datetime.datetime.now().date()).days/30
                else:
                    record.next_service_value_date = False
                record.next_service_usage = next_usage_service
                record.next_service_date = next_date_service
            else:
                record.next_service_value_usage = False
                record.next_service_value_date = False
                record.next_service_usage = False
                record.next_service_date = False
            
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
                data = {'value': record.running_time, 'date': date, 'vehicle_id': record.id}
                self.env['fleet.vehicle.running.time'].create(data)

    def _compute_running_time_count(self):
        FleetVehicleRunningTime = self.env['fleet.vehicle.running.time']
        for record in self:
            record.running_time_count = FleetVehicleRunningTime.search_count([('vehicle_id', '=', record.id)])
            
    def return_action_to_open(self):
        """ This opens the xml view specified in xml_id for the current vehicle """
        self.ensure_one()
        xml_id = self.env.context.get('xml_id')
        if xml_id:
            try:
                res = self.env['ir.actions.act_window']._for_xml_id('fleet_maintenance.%s' % xml_id)
            except ValueError as e:
                if "External ID not found in the system:" in str(e):
                    pass
                else:
                    raise e
            else:
                res.update(
                    context=dict(self.env.context, default_vehicle_id=self.id, group_by=False),
                    domain=[('vehicle_id', '=', self.id)]
                )
                return res
        return super(FleetVehicle, self).return_action_to_open()
    
    def run_scheduler(self):
        min_usage_percent_remaining = 0.05
        min_date_units = 0.25
        users = self.env['ir.model.data'].get_object('fleet','fleet_group_manager').users
        users |= self.driver_id
        maintenance_activity_type = self.env['ir.model.data'].get_object('fleet_maintenance','mail_act_fleet_maintenance')
        records = self.search([])
        vehicle_model_id = self.env['ir.model'].search([('model', '=', 'fleet.vehicle')]).id
        for record in records:
            previous_activities = record.env['mail.activity'].search([('activity_type_id','=',maintenance_activity_type.id),
                                              ('user_id','in',users.ids),
                                              ('res_model_id','=',vehicle_model_id),
                                              ('res_id','=',record.id)])
            previous_activities.unlink()
            if record.maintenance_plan:
                min_usage_remaining = record.next_service_usage.periodicity*min_usage_percent_remaining
                if record.next_service_usage and record.next_service_value_usage <= min_usage_remaining:
                    record._create_activity(usage=record.next_service_value_usage)
                if record.next_service_date and record.next_service_value_date <= min_date_units:
                    record._create_activity(months=record.next_service_value_date)
                
    def _create_activity(self,months=False,usage=False):
        _logger = logging.getLogger(__name__)
        Activity = self.env["mail.activity"]
        activity_type_id = self.env['ir.model.data'].get_object('fleet_maintenance','mail_act_fleet_maintenance')
        res_id = self.id
        res_model_id = self.env['ir.model'].search([('model', '=', 'fleet.vehicle')]).id
        users = self.env['ir.model.data'].get_object('fleet','fleet_group_manager').users
        if (usage and usage < 0) or (months and months < 0):
            if usage:
                date_deadline = datetime.date.today() - datetime.timedelta(days=1)
            else:
                date_deadline = datetime.date.today() - datetime.timedelta(months=months)
            note = _('Maintenance on vehicle is required.')
        else:
            date_deadline = datetime.date.today()
            note = _('Maintenance on vehicle is required soon.')
        for user_id in users:
            vals = {"activity_type_id": activity_type_id.id,
                            "note": note,
                            "res_id": res_id,
                            "user_id": user_id.id,
                            "res_model_id": res_model_id,
                            "date_deadline": date_deadline}
            try:
                Activity.create(vals)
            except:
                _logger.info("Unable to create activity: " + str(vals))
        return True
            
    def _create_service(self,service):
        vals = {}
        vals['vehicle_id'] = self.id
        vals['purchaser_id'] = self.driver_id.id
        vals['service_type_id'] = service.service_type.id
        vals['date'] = datetime.date.today()
        if self.maintenance_type == 'odometer':
            vals['description'] = _('Service "%s" at %s %s' % (service.service_type.name,self.odometer,self.odometer_unit))
            vals['odometer'] = self.odometer
        elif self.maintenance_type == 'running_time':
            vals['description'] = _('Service "%s" at %s %s' % (service.service_type.name,self.running_time,self.running_time_unit))
            vals['running_time'] = self.running_time
        res_id = self.env['fleet.vehicle.log.services'].create(vals)
        return {
            'name': _('Service'),
            'type': 'ir.actions.act_window',
            'res_model': 'fleet.vehicle.log.services',
            'view_mode': 'form',
            'res_id': res_id.id
        }
    
    def action_create_service_usage(self):
        return self._create_service(self.next_service_usage)
    
    def action_create_service_date(self):
        return self._create_service(self.next_service_date)
        
class FleetVehicleRunningTime(models.Model):
    _name = 'fleet.vehicle.running.time'
    _description = 'Runing time log for a vehicle'
    _order = 'date desc'

    name = fields.Char(compute='_compute_vehicle_log_name', store=True)
    date = fields.Date(default=fields.Date.context_today, required=True)
    value = fields.Float('Time Value', group_operator="max", required=True)
    vehicle_id = fields.Many2one('fleet.vehicle', 'Vehicle', domain="[('maintenance_type','=','running_time')]", required=True)
    unit = fields.Selection(related='vehicle_id.running_time_unit', string="Unit", readonly=True)
    driver_id = fields.Many2one(related="vehicle_id.driver_id", string="Driver", readonly=False)

    @api.depends('vehicle_id', 'date')
    def _compute_vehicle_log_name(self):
        for record in self:
            name = record.vehicle_id.name
            if not name:
                name = str(record.date)
            elif record.date:
                name += ' / ' + str(record.date)
            record.name = name

    @api.onchange('vehicle_id')
    def _onchange_vehicle(self):
        if self.vehicle_id:
            self.unit = self.vehicle_id.running_time_unit
    
    @api.model        
    def create(self, vals):
        vehicle_running_time = self.search([('vehicle_id', '=', vals['vehicle_id'])], limit=1, order='value desc')
        if vehicle_running_time:
            if vals['value'] < vehicle_running_time.value:
                raise ValidationError(_('New running time value (%d) cannot be less than existing one (%d).' % (vals['value'],vehicle_running_time.value)))
        return super(FleetVehicleRunningTime, self).create(vals)
            
class FleetVehicleOdometer(models.Model):
    _inherit = 'fleet.vehicle.odometer'
    
    vehicle_id = fields.Many2one('fleet.vehicle', 'Vehicle', domain="[('maintenance_type','=','odometer')]", required=True)
    
    @api.model        
    def create(self, vals):
        vehicle_odometer = self.search([('vehicle_id', '=', vals['vehicle_id'])], limit=1, order='value desc')
        if vehicle_odometer:
            if vals['value'] < vehicle_odometer.value:
                raise ValidationError(_('New odometer value (%d) cannot be less than existing one (%d).' % (vals['value'],vehicle_odometer.value)))
        return super(FleetVehicleOdometer, self).create(vals)
