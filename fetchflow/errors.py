from __future__ import annotations

import re

# Traducir un fallo de yt-dlp a algo que le sirva a una persona.
#
# Es el punto mas importante de la UX de un descargador: los sitios cambian y la
# extraccion se rompe seguido, asi que la diferencia entre util e inutil es decir QUE
# paso. yt-dlp ya escribe mensajes legibles, pero les pega decoracion de terminal.

# Codigos de color ANSI. yt-dlp los mete en sus mensajes de error, y sin limpiarlos
# llegan crudos a la pantalla: se vio "[0;31mERROR: [0m[youtube] ..." en una UI real.
# Es lo primero que ve alguien cuando algo falla, asi que importa.
#
# Pedirle `color: no_color` al motor cubre el camino normal; esto cubre el resto, porque
# la excepcion puede venir de un lugar que no respeta esa opcion.
_ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")

# Sin exigir el espacio final. Se limpia ANSI primero y eso deja "ERROR: " suelto, cuyo
# .strip() lo vuelve "ERROR:" -- un prefijo con espacio nunca matchearia y el resultado
# era "ERROR:" a secas, o sea decoracion pura mostrada como si fuera un motivo.
_ERROR_PREFIX = re.compile(r"^error:\s*", re.IGNORECASE)

# yt-dlp no tiene una excepcion propia para el rate limit, asi que se reconoce por el
# texto. Fragil por naturaleza -- si cambian la redaccion, el aviso se degrada al
# mensaje original, que ya es legible. Nunca se pierde informacion.
_RATE_LIMIT_MARKERS = ("rate-limited", "rate limited", "too many requests", "http error 429")

RATE_LIMIT_MESSAGE = (
    "El sitio limito los pedidos por hacer demasiados seguidos. "
    "Espera unos minutos y volve a intentar; no hay nada roto."
)


def looks_rate_limited(message: str) -> bool:
    return any(marker in message.lower() for marker in _RATE_LIMIT_MARKERS)


def describe_failure(exc: Exception, *, rate_limit_message: str = RATE_LIMIT_MESSAGE) -> str:
    """Un motivo legible, sin decoracion de terminal ni stacktrace.

    `rate_limit_message` es parametro para que cada app lo diga en su idioma y su tono;
    el default explica lo unico que la persona necesita saber, que es que no hay nada
    roto y que esperar alcanza. El mensaje original de yt-dlp recomienda un flag de
    linea de comandos que en una app embebida no existe.
    """
    message = _ERROR_PREFIX.sub("", _ANSI_ESCAPE.sub("", str(exc)).strip()).strip()
    if not message:
        return exc.__class__.__name__
    if looks_rate_limited(message):
        return rate_limit_message
    return message
