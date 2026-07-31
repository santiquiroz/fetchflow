from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

# Traduccion de "quiero este video" a las opciones de yt-dlp.
#
# Vive aparte y sin importar nada de Upflow a proposito: aca esta TODA la logica de
# decision (formato, techo de altura, contenedor, playlist, subtitulos) y se prueba
# entera sin tocar la red ni yt-dlp. Es tambien lo que hace que este paquete se pueda
# extraer a su propio repo cuando este probado.
#
# Lo que se midio y por que esta cada cosa:
#
#   - ffmpeg NO alcanza con `ffmpeg_location`. Un intento real fallo con "ffmpeg is not
#     installed" mientras el postprocesador reportaba available=True: el camino de
#     descarga parcial usa OTRO chequeo, que mira el PATH. Por eso `env_path_entries`
#     existe y el llamador TIENE que usarlo.
#   - Los hooks de progreso dan bytes y total, y son densos: 180 eventos para 124 MB.
#   - Lanzar desde el hook cancela limpio y deja un .part identificable.

# Alturas que la UI ofrece. Tope en 1080 por defecto y no en 4K: el pedido caro tiene
# que ser una eleccion, no un descuido. Es la misma leccion del multiplicador ciego.
DEFAULT_MAX_HEIGHT = 1080
ALLOWED_MAX_HEIGHTS: tuple[int, ...] = (360, 480, 720, 1080, 1440, 2160)

# Techo duro de items por pedido. Existe para que nadie dispare una playlist de 500
# videos sin querer -- la queja mas repetida en los foros de descargadores.
MAX_PLAYLIST_ITEMS = 50

# Techo del probe al enumerar una playlist. Los Mixes de YouTube (list=RD...) generan
# entradas SIN FIN incluso en modo plano: sin este tope el probe no retorna nunca.
PROBE_PLAYLIST_LIMIT = 100

# Formatos de audio ofrecidos. Los lossless no tienen bitrate elegible: el plan
# descarta el bitrate para ellos en vez de pasarle a ffmpeg una invocacion invalida.
AUDIO_FORMATS: tuple[str, ...] = ("mp3", "m4a", "opus", "flac", "wav")
LOSSLESS_AUDIO_FORMATS: tuple[str, ...] = ("flac", "wav")
DEFAULT_AUDIO_FORMAT = "mp3"
# None = mejor calidad variable ("0" para ffmpeg). Bitrates fijos solo para lossy.
ALLOWED_AUDIO_BITRATES_KBPS: tuple[int, ...] = (128, 192, 256, 320)

# Contenedores de merge para video. webm queda afuera a proposito: con streams h264
# (lo que dan casi todos los sitios) el remux de ffmpeg falla; mkv acepta cualquier
# stream y mp4 es el default compatible.
VIDEO_CONTAINERS: tuple[str, ...] = ("mp4", "mkv")
DEFAULT_VIDEO_CONTAINER = "mp4"

# Pausa entre pedidos. NO es prudencia teorica: sin esto YouTube corta la sesion con
# "the current session has been rate-limited by YouTube for up to an hour" -- se
# reprodujo probando la app, y una hora de espera por unos pocos pedidos seguidos es
# mucho peor que un segundo de pausa entre ellos.
SLEEP_BETWEEN_REQUESTS_SECONDS = 1

# Reintentos ante errores conocidos del extractor. yt-dlp ya trae 3 por defecto; se
# declara explicito para que se vea que es una decision y no un descuido.
EXTRACTOR_RETRIES = 3


@dataclass(frozen=True, slots=True)
class FetchRequest:
    url: str
    output_dir: Path
    max_height: int = DEFAULT_MAX_HEIGHT
    audio_only: bool = False
    audio_format: str = DEFAULT_AUDIO_FORMAT
    # None = mejor calidad variable; un numero = bitrate fijo (solo formatos lossy).
    audio_bitrate_kbps: int | None = None
    video_container: str = DEFAULT_VIDEO_CONTAINER
    # Una playlist se trata como UN item salvo que se pida lo contrario, explicito.
    include_playlist: bool = False
    playlist_limit: int = 10
    subtitle_languages: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class FetchPlan:
    """Lo que se le va a pedir a yt-dlp, mas lo que el entorno necesita."""

    options: dict = field(default_factory=dict)
    # Directorios que TIENEN que estar en PATH del proceso. Ver la nota de arriba:
    # pasar ffmpeg_location y nada mas rompe la descarga parcial.
    env_path_entries: tuple[Path, ...] = ()


def validate_max_height(max_height: int) -> None:
    if max_height not in ALLOWED_MAX_HEIGHTS:
        raise ValueError(
            f"max_height debe ser uno de {list(ALLOWED_MAX_HEIGHTS)}, no {max_height}"
        )


def validate_audio_format(audio_format: str) -> None:
    if audio_format not in AUDIO_FORMATS:
        raise ValueError(
            f"audio_format debe ser uno de {list(AUDIO_FORMATS)}, no {audio_format!r}"
        )


def validate_audio_bitrate(bitrate_kbps: int | None) -> None:
    if bitrate_kbps is None:
        return
    if bitrate_kbps not in ALLOWED_AUDIO_BITRATES_KBPS:
        raise ValueError(
            f"audio_bitrate_kbps debe ser uno de {list(ALLOWED_AUDIO_BITRATES_KBPS)} "
            f"o None, no {bitrate_kbps}"
        )


def validate_video_container(container: str) -> None:
    if container not in VIDEO_CONTAINERS:
        raise ValueError(
            f"video_container debe ser uno de {list(VIDEO_CONTAINERS)}, no {container!r}"
        )


def audio_quality_for(audio_format: str, bitrate_kbps: int | None) -> str:
    if bitrate_kbps is None or audio_format in LOSSLESS_AUDIO_FORMATS:
        return "0"
    return str(bitrate_kbps)


def validate_playlist_limit(limit: int) -> None:
    if limit < 1:
        raise ValueError(f"playlist_limit debe ser positivo, no {limit}")
    if limit > MAX_PLAYLIST_ITEMS:
        raise ValueError(
            f"playlist_limit no puede pasar de {MAX_PLAYLIST_ITEMS}; se pidio {limit}"
        )


def format_selector(max_height: int, audio_only: bool) -> str:
    """El selector de formato de yt-dlp.

    Video y audio por separado y despues merge, porque en la mayoria de los sitios la
    mejor calidad solo existe en pistas separadas. El fallback `/best[...]` cubre a los
    que solo publican un archivo combinado.
    """
    if audio_only:
        return "bestaudio/best"
    return f"bestvideo[height<={max_height}]+bestaudio/best[height<={max_height}]"


def output_template(include_playlist: bool) -> str:
    # El indice adelante solo cuando hay playlist, para que el orden se vea en el
    # directorio. En un item suelto seria ruido.
    if include_playlist:
        return "%(playlist_index)03d-%(title).80s.%(ext)s"
    return "%(title).80s.%(ext)s"


def build_plan(request: FetchRequest, ffmpeg_bin_dir: Path) -> FetchPlan:
    validate_max_height(request.max_height)
    if request.include_playlist:
        validate_playlist_limit(request.playlist_limit)
    # Mismo criterio que playlist_limit: cada knob se valida solo cuando el pedido
    # lo usa, para que uno absurdo no rompa un pedido que ni lo mira.
    if request.audio_only:
        validate_audio_format(request.audio_format)
        validate_audio_bitrate(request.audio_bitrate_kbps)
    else:
        validate_video_container(request.video_container)

    options: dict = {
        "outtmpl": str(request.output_dir / output_template(request.include_playlist)),
        "format": format_selector(request.max_height, request.audio_only),
        "ffmpeg_location": str(ffmpeg_bin_dir),
        "noplaylist": not request.include_playlist,
        "noprogress": True,
        "quiet": True,
        "no_warnings": True,
        # Ver la nota de SLEEP_BETWEEN_REQUESTS_SECONDS: sin la pausa, YouTube corta la
        # sesion por una hora.
        "sleep_interval_requests": SLEEP_BETWEEN_REQUESTS_SECONDS,
        "extractor_retries": EXTRACTOR_RETRIES,
        # Sin colores ANSI: yt-dlp los mete en los mensajes de error y llegaban crudos
        # a la pantalla ("[0;31mERROR: [0m...").
        "color": "no_color",
        # Metadata y subtitulos por defecto: es lo que la gente espera que pase, y
        # pedirlo por separado es la friccion que hace que los descargadores se sientan
        # burocraticos.
        "writethumbnail": False,
        "embedmetadata": True,
        "embedsubtitles": bool(request.subtitle_languages),
        # Sin DRM. yt-dlp ya se niega; esto lo hace explicito y da un motivo legible.
        "allow_unplayable_formats": False,
    }

    if request.audio_only:
        options["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": request.audio_format,
                "preferredquality": audio_quality_for(
                    request.audio_format, request.audio_bitrate_kbps
                ),
            }
        ]
    else:
        options["merge_output_format"] = request.video_container

    if request.subtitle_languages:
        options["writesubtitles"] = True
        options["subtitleslangs"] = list(request.subtitle_languages)

    if request.include_playlist:
        options["playlistend"] = request.playlist_limit

    return FetchPlan(options=options, env_path_entries=(ffmpeg_bin_dir,))
