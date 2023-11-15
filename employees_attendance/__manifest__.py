# -*- coding: utf-8 -*-
{
    'name': 'Asistencias de empleados',
    'version': '1.0.0',
    'category': 'Custom',
    'summary': '',
    'description': """
        Custom attendance for employees
    """,
    'author': 'Arnau Fornaguera Orpinell',
    'depends': ['base', 'hr_attendance', 'web_tree_dynamic_colored_field', 'hr_attendance_autoclose', 'hr_attendance_calendar_view', 'hr_attendance_geolocation', 'hr_attendance_reason', 'hr_attendance_report_theoretical_time', 'hr_holidays_public'],
    'data': [
        'security/ir.model.access.csv',
        'views/hr_attendance_views.xml',
        'report/hr_attendance_report.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
}