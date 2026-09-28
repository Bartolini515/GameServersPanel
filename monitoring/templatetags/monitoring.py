from django import template

from monitoring.system import format_bytes, format_uptime

register = template.Library()
register.filter("monitor_bytes", format_bytes)
register.filter("monitor_uptime", format_uptime)
