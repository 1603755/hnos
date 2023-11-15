==================
Monitoring: Status
==================

.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
    :alt: License

Provides a HTTP route that returns health status of the instance.

| The url to call is ``http://server/monitoring/status``
| 
| This module is maintained from: https://github.com/vertelab/odoo-maintenance/
| until https://github.com/camptocamp/odoo-cloud-platform/tree/14.0/monitoring_status has lifted it.
| Inspired by Camptocamp SA.
|        
| Purpose of this module is to answer with a json object the status of the database, on or off. To query the database you need to go to the /monitoring/status url.
| 
| Url Syntax: ``https ://hostname/monitoring/status?db=databasename``
| 
| In order for the database to be able to answer without being logged in on you need to change the odoo.conf and add this module to the server_wide_modules.
  

Installation
============

This module depends on ``base``, ``web`` .

This module is maintained from: https://github.com/vertelab/odoo-maintenance/

Configuration
=============


Usage
=====
| Module.
| 
| Version ledger:
| 14.0 = Odoo version
| 1 = Major, Non regressionable code
| 2 = Minor, New features that are regressionable
| 3 = Bug fixes
| 
| Hover over fields to se a brief description of them. For more information make sure you are in debug mode.
| 
| 14.0.1.0 - Ticket-123 Added the module to the repo.
