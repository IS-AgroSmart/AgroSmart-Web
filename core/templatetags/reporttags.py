# https://stackoverflow.com/a/1427964
from django import template

from core.models import Camera, FlightState

register = template.Library()


@register.filter
def cameraname(cam):
    if cam == Camera.REDEDGE.name:
        return "Micasense RedEdge"
    elif cam == Camera.RGB.name:
        return "Cámara RGB"
    else:
        return "Cámara no reconocida: <" + cam + ">"


@register.filter
def statename(state):
    if state == FlightState.COMPLETE.name:
        return "Completado con éxito"
    elif state == FlightState.ERROR.name:
        return "Completado con errores"
    elif state == FlightState.CANCELED.name:
        return "Cancelado por el usuario"
    else:
        return "Estado no reconocido: <" + state + ">"


@register.filter
def millistostring(millis):
    secs = millis // 1000
    s = secs % 60
    m = (secs - s) // 60
    h = (secs - s - m * 60) // 3600
    return "{} h, {} min, {} s".format(h, m, s)
