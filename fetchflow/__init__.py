"""fetchflow — yt-dlp embebible, con el pegamento ya resuelto.

Lo que aporta sobre llamar a yt-dlp directo: progreso tipado, cancelacion cooperativa,
y las cuatro trampas de integracion que solo aparecen midiendo (ver el README).

NO envuelve la extraccion: eso es yt-dlp y son 210.000 lineas de trabajo que nadie
deberia reescribir.
"""

from fetchflow.engine import (
    FetchCancelled,
    FetchProgress,
    FetchUnavailable,
    MediaInfo,
    download,
    probe,
)
from fetchflow.options import (
    ALLOWED_MAX_HEIGHTS,
    DEFAULT_MAX_HEIGHT,
    MAX_PLAYLIST_ITEMS,
    FetchPlan,
    FetchRequest,
    build_plan,
)

__all__ = [
    "ALLOWED_MAX_HEIGHTS",
    "DEFAULT_MAX_HEIGHT",
    "MAX_PLAYLIST_ITEMS",
    "FetchCancelled",
    "FetchPlan",
    "FetchProgress",
    "FetchRequest",
    "FetchUnavailable",
    "MediaInfo",
    "build_plan",
    "download",
    "probe",
]
