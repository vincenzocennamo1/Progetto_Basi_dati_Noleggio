from django import template

from rental.utils import money, vehicle_specs


register = template.Library()


@register.filter
def euro(value):
    return money(value)


@register.filter
def specs(vehicle):
    return vehicle_specs(vehicle, show_plate=False)


@register.filter
def plate_specs(vehicle):
    return vehicle_specs(vehicle, show_plate=True)
