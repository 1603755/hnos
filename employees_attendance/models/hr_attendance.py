from odoo import models, fields, api
from datetime import datetime
from jinja2 import Markup
from geopy.geocoders import Nominatim
from geopy.point import Point
from bs4 import BeautifulSoup
import pytz
#need to install jinja2 and geopy if not installed
class HrAttendance(models.Model):
    _name = 'hr.attendance'
    _description = 'Advanced Employees Attendance'
    _inherit = 'hr.attendance'

    difference = fields.Char(string='Diferencia', compute='_compute_difference')
    diff_value = fields.Integer(string='Difference Value', compute='_compute_difference')
    summary = fields.Html(string='Resumen')
    day = fields.Date(string='Dia')


    @api.depends('check_in', 'check_out')
    def _compute_difference(self):
        day_hours = self.env['resource.calendar'].search([('id', '=', self.employee_id.resource_calendar_id.id)], limit=1).hours_per_day
        for attendance in self:
            # Obtener la diferencia de horas

            difference = attendance.worked_hours * 60 - day_hours * 60
            attendance.diff_value = difference
            negative = 1
            if difference < 0:
                negative = -1
            difference = abs(difference*60)


            hours = 0
            minutes = 0
            seconds = 0

            hours = int(difference/3600)
            if hours != 0:
                minutes = int(int(difference)%3600/60)
            else:
                minutes = int(difference)/60
                if minutes != 0:
                    seconds = int(difference)%60
                else:
                    seconds = int(difference)

            if hours and minutes:
                attendance.difference = f"{negative*hours}h {minutes}m"
            elif minutes and seconds:
                attendance.difference = f"{negative*minutes}m {seconds}s"
            else:
                attendance.difference = f"{negative*seconds}s"


    def update_attributes(self, vals):
        user_tz = pytz.timezone(self.env.user.tz)
        icon_in_html = Markup('<img src="/employees_attendance/static/src/icons/in.png" alt="My Icon" style="vertical-align: middle; margin-right: 5px; max-height: 1em;"/>')
        icon_out_html = Markup('<img src="/employees_attendance/static/src/icons/out.png" alt="My Icon" style="vertical-align: middle; margin-right: 5px; max-height: 1em;"/>')

        if vals.get('check_out'):
            if isinstance(vals.get('check_out'), str):
                vals['check_out'] = datetime.strptime(str(vals.get('check_out')), "%Y-%m-%d %H:%M:%S")
        if vals.get('check_in'):
            if isinstance(vals.get('check_in'), str):
                vals['check_in'] = datetime.strptime(str(vals.get('check_in')), "%Y-%m-%d %H:%M:%S")
        existing_attendance = self.env['hr.attendance'].search([('employee_id', '=', self.employee_id.id)])
        if existing_attendance:
            #Obtenemos el check_in minimo
            today = datetime.today()
            min = today
            anterior = False
            for attendance in existing_attendance:
                if attendance.check_in.date() == min.date():
                    if attendance.check_in < min:
                        min = attendance.check_in
                        anterior = True
                        break


            vals['summary'] = f""
            #Seteamos el summary y nos deshacemos de las tuplas innecesarias
            for attendance in existing_attendance:
                if attendance.check_in.date() == min.date():
                    if 'summary' in vals and attendance.summary:
                        vals['summary'] = attendance.summary + vals['summary']
                    else:
                        vals['summary'] = attendance.summary
                    if attendance.id != self.id:
                        attendance.unlink()


            if vals.get('check_in') and not anterior:
                vals['summary'] += Markup(f"{icon_in_html} {pytz.utc.localize(vals['check_in']).astimezone(user_tz).strftime('%H:%M')}")

            vals['check_in'] = min
        else:
            if not vals.get('summary'):
                vals['summary'] = f""

            if vals.get('check_in'):
                #pass  check_int to user defined utc time
                #get the user timezone
                vals['summary'] += Markup(f"{icon_in_html} {pytz.utc.localize(vals['check_in']).astimezone(user_tz).strftime('%H:%M')}")

        if vals.get('check_out'):
            if self.check_in_latitude_text and self.check_in_longitude_text:
                try:
                    latitude_decimal, longitude_decimal = coordenadas_a_numeros(self.check_in_latitude_text, self.check_in_longitude_text)
                    location_address = get_location_from_coordinates(latitude_decimal, longitude_decimal)
                    work_location = self.env['hr.work.location'].search([('id', '=', self.employee_id.work_location_id.id)], limit=1)
                    if location_address == work_location.name:
                        presencial_icon_html = Markup('<img src="/employees_attendance/static/src/icons/presencial.png" alt="My Icon" style="vertical-align: middle; margin-right: 5px; max-height: 1em;"/>')
                        vals['summary'] += Markup(f" &nbsp; {presencial_icon_html} &nbsp;")
                    else:
                        online_icon_html = Markup('<img src="/employees_attendance/static/src/icons/online.png" alt="My Icon" style="vertical-align: middle; margin-right: 5px; max-height: 1.5em;"/>')
                        vals['summary'] += Markup(f"&nbsp; {online_icon_html} &nbsp;")
                except ValueError:
                    vals['summary'] += Markup(f"&nbsp;<b>Unknown</b>&nbsp;")
            vals['summary'] += Markup(f"{icon_out_html} {pytz.utc.localize(vals['check_out']).astimezone(user_tz).strftime('%H:%M')}  ")
            vals['summary'] += Markup(f" &nbsp; &nbsp; <b> {datetime_to_difference(self.check_in, vals['check_out'])} </b> <br/>")

        if vals.get('check_in'):
            vals['day'] = vals['check_in'].date()






    def write(self, vals):
        vals['employee_id'] = self.employee_id.id
        self.update_attributes(vals)
        return super(HrAttendance, self).write(vals)

    @api.model
    def create(self, vals):
        self.update_attributes(vals)
        return super(HrAttendance, self).create(vals)

    def user_attendances_to_pdf(self):
        return {
            'type': 'ir.actions.report',
            'report_name': 'employees_attendance.attendance_report',
            'report_type': 'qweb-pdf',
            'data': {
                'model': 'hr.employee',
                'ids': self.ids,
                'report_name': 'employees_attendance.attendance_report',
                'summary': Markup(f"{self.summary}"),
            },
            'context': {
                'active_model': 'hr.employee',
                'active_ids': self.ids,
                'active_id': len(self.ids) and self.ids[0] or False,
            },
        }

    #Convert all attendances of the user in the day to pdf
    def print_attendance_report(self):
        attendances = self.env['hr.attendance'].search([('employee_id', '=', self.employee_id.id)])
        form = []
        for attendance_id in attendances.ids:
            #only append if the attendance is from the same day
            if self.env['hr.attendance'].browse(attendance_id).check_in.date() == self.check_in.date():
                form.append(self.env['hr.attendance'].browse(attendance_id).read()[0])
        data = {
            'ids': attendances.ids,
            'model': 'hr.attendance',
            'form': form
        }

        return self.env.ref('employees_attendance.action_report_hr_attendance').report_action(self, data=data)

    # Convert all attendances of the user to pdf
    def print_user_attendance_report(self):
        attendances = self.env['hr.attendance'].search([('employee_id', '=', self.employee_id.id)])
        form = []
        for attendance_id in attendances.ids:
            attendance = self.env['hr.attendance'].browse(attendance_id).read()[0]

            soup = BeautifulSoup(attendance['summary'], 'html.parser')
            rows = []
            for row in soup.find_all('img'):
                image = row

                if image and ('in.png' in image['src'] or 'out.png' in image['src']):
                    continue

                if image and ('presencial' in image['src']):
                    rows.append("presencial")
                elif image and ('online' in image['src']):
                    rows.append("online")
                else:
                    rows.append("unknown")

            attendance['summary'] = remove_html_markup(attendance['summary']).replace('\xa0', ' ').split('  ')
            attendance['summary'] = list(filter(lambda item: item != '', attendance['summary']))
            if len(attendance['summary'])/3 == len(rows):
                for i in range(len(rows)):
                    #add in to second element row without erasing the element
                    attendance['summary'].insert((i*3)+1+i, rows[i])
            form.append(attendance)

        data = {
            'ids': attendances.ids,
            'model': 'hr.attendance',
            'form': form
        }
        return self.env.ref('employees_attendance.action_report_hr_attendance').report_action(self, data=data)

def get_location_from_coordinates(latitud, longitud):
    geolocator = Nominatim(user_agent="geocoding_app")
    coordenadas = f"{latitud}, {longitud}"
    try:
        location = geolocator.reverse(coordenadas, exactly_one=True, language="es")
        if location:
            # Location format ej: les Casetes d'en Mussons, Òdena, Anoia, Barcelona, Cataluña, 08700, España
            # Solo se coje la calle
            return location.address.split(",")[0]
        else:
            return "Dirección no encontrada para estas coordenadas."
    except Exception as e:
        return f"Error: {str(e)}"


def coordenadas_a_numeros(latitud_str, longitud_str):
    # Función para convertir una coordenada de grados, minutos y segundos a un número decimal
    def grados_minutos_segundos_a_decimal(grados, minutos, segundos):
        return grados + minutos / 60 + segundos / 3600

    # Dividir las cadenas de coordenadas en grados, minutos y segundos
    latitud_parts = latitud_str.split()
    longitud_parts = longitud_str.split()

    # Obtener los valores de grados, minutos y segundos para latitud y longitud
    latitud_grados = float(latitud_parts[1][:-1])  # Excluir el último carácter (º)
    latitud_minutos = float(latitud_parts[2][:-1])  # Excluir el último carácter (')
    latitud_segundos = float(latitud_parts[3][:-1])  # Excluir el último carácter (')

    longitud_grados = float(longitud_parts[1][:-1])  # Excluir el último carácter (º)
    longitud_minutos = float(longitud_parts[2][:-1])  # Excluir el último carácter (')
    longitud_segundos = float(longitud_parts[3][:-1])  # Excluir el último carácter (')

    # Calcular los valores numéricos para latitud y longitud
    latitud_numerica = grados_minutos_segundos_a_decimal(latitud_grados, latitud_minutos, latitud_segundos)
    longitud_numerica = grados_minutos_segundos_a_decimal(longitud_grados, longitud_minutos, longitud_segundos)

    return latitud_numerica, longitud_numerica

def datetime_to_difference(datetime1, datetime2):
    # make tehr rest of the two datetimes , and look if are seconds, minutes, or hours
    if datetime1 > datetime2:
        datetime1, datetime2 = datetime2, datetime1
    rest = datetime2 - datetime1
    if rest.seconds < 60:
        return f"{rest.seconds} s"
    elif rest.seconds < 3600:
        return f"{rest.seconds // 60} m"
    else:
        return f"{rest.seconds // 3600} h"

def remove_html_markup(text_with_markup):
    soup = BeautifulSoup(text_with_markup, "html.parser")
    text_without_markup = soup.get_text()

    return text_without_markup