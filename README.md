# fetchflow

yt-dlp embebible en una app Python, con el pegamento ya resuelto.

**Lo que NO hace:** extraer. Eso es [yt-dlp](https://github.com/yt-dlp/yt-dlp) — 1751
extractores y ~210.000 líneas de gente averiguando cómo cada sitio sirve su video, y
rehaciéndolo cada vez que el sitio cambia. Nadie debería reescribir eso.

**Lo que sí hace:** todo lo que hay entre "yt-dlp existe" y "mi app puede descargar sin
sorpresas".

## Por qué existe

Los wrappers de yt-dlp que hay en PyPI son de dos tipos: envoltorios de **línea de
comandos**, o **forks de yt-dlp** para agregarle progreso. Forkear es un callejón —
yt-dlp libera casi mensualmente para seguirle el paso a las defensas de los sitios, y un
fork queda atrás justo cuando más importa.

Falta la tercera opción: una librería que lo **envuelva** sin forkearlo, y que traiga
resueltas las trampas que solo aparecen cuando lo pones en producción.

## Las cuatro trampas, medidas

Cada una nos costó una sesión de depuración. Están resueltas acá con un test que las fija.

**1. `ffmpeg_location` no alcanza.** Pasás la opción, el postprocesador reporta
`available=True`, y la descarga muere con `ffmpeg is not installed`. El camino de descarga
parcial usa **otro** chequeo, que mira el `PATH`. `build_plan()` devuelve los directorios
que hay que agregar, y `download()` los aplica.

**2. Los archivos finales no están en los eventos `finished`.** Esos reportan los
componentes de **antes** del merge (el video suelto y el audio suelto), que ffmpeg borra
al unirlos. Una descarga perfecta devolvía **lista vacía**. La verdad está en
`requested_downloads[].filepath` del info que devuelve yt-dlp.

**3. Las calidades incluyen basura.** Un probe de YouTube devuelve alturas `27, 45, 90`
entre las reales: son storyboards, tiras de miniaturas. Se filtran por `vcodec`.

**4. `curl-cffi` no es opcional.** Sin él, Dailymotion falla con *"the extractor is
attempting impersonation, but none of these impersonate targets are available"*. Con él
pasa a funcionar: de **0 a 37** targets de impersonation. Cada vez más sitios exigen
fingerprint de TLS de navegador. Va como dependencia, no como extra.

Y una quinta que no es trampa sino consecuencia: **sin pausa entre pedidos, YouTube corta
la sesión por una hora.** `sleep_interval_requests` va puesto por defecto, en el probe y
en la descarga.

## Uso

```python
from pathlib import Path
from fetchflow import FetchRequest, build_plan, download, probe

info = probe("https://www.youtube.com/watch?v=aqz-KE-bpKQ")
print(info.title, info.duration_seconds, info.available_heights)
# Big Buck Bunny ... 635 (144, 240, 360, 480, 720, 1080, 1440, 2160)

plan = build_plan(
    FetchRequest(url=info_url, output_dir=Path("./descargas"), max_height=1080),
    ffmpeg_bin_dir=Path("/usr/bin"),
)
archivos = download(plan, info_url, on_progress=lambda p: print(p.fraction))
```

### Cancelar

```python
import threading

cancelar = threading.Event()
# desde otro hilo: cancelar.set()
try:
    download(plan, url, cancel_event=cancelar)
except FetchCancelled:
    ...  # lo pidió el usuario, no es un fallo
```

Cortar se hace lanzando desde el hook de progreso. `download()` reconoce la cancelación
recorriendo la cadena de causas, porque yt-dlp la envuelve en `DownloadError` — sin eso,
cancelar se reportaría como error.

## Decisiones que trae puestas

Son opiniones, y están acá porque cada una evita un problema concreto:

| Decisión | Por qué |
|---|---|
| Techo por defecto **1080p**, no 4K | Un default caro es cómo se llega a esperar una hora por algo que nadie pidió |
| Una URL de lista baja **un** item | Es también la URL de un video. La queja más repetida del rubro es pegar un link y que arranquen 200 |
| Tope duro de 50 items | Que un límite mal puesto no se convierta en 500 descargas |
| Video + audio separados y merge | En la mayoría de los sitios la mejor calidad solo existe en pistas separadas |
| Metadata por defecto | Es lo que la gente espera; pedirlo aparte vuelve la herramienta burocrática |
| `allow_unplayable_formats: False` | No sortear DRM. Es la línea que separa un uso defendible de uno que no |

Si no te gustan, `build_plan()` devuelve un dict de opciones normal que podés modificar
antes de pasarlo a `download()`.

## Qué está deliberadamente afuera

- **Cola de trabajos.** Toda app ya tiene la suya y acoplarla acá sería estorbo.
- **Interfaz.** Esto es una librería.
- **Salud por sitio.** Es el hueco más real que queda, pero necesita datos de uso que
  todavía no tenemos. Prefiero no inventar una API para eso.

## Probar

```bash
pip install -e ".[dev]"
pytest
```

Los 43 tests corren **sin red y sin yt-dlp**: el constructor de opciones es puro, y el
puente de progreso, la detección de cancelación y el manejo del `PATH` se prueban con
diccionarios. La integración con yt-dlp real se verifica a mano; lo medido está en las
notas de cada test.

## Licencia

MIT. yt-dlp es [The Unlicense](https://github.com/yt-dlp/yt-dlp/blob/master/LICENSE)
(dominio público), así que no impone nada — pero **cuidado con su ejecutable prebuilt**:
ese incluye código GPLv3+ y el trabajo combinado pasa a ser GPLv3+. Este paquete depende
del wheel de PyPI, que es Unlicense limpio.

## De dónde salió

Extraído de [Upflow](https://github.com/santiquiroz/upflow), una suite de multimedia e IA,
donde es el motor de su apartado de descargas.
