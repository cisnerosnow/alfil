<p align="center">
  <img src="logo-alfil.png" alt="Alfil" width="180">
</p>

<h1 align="center">Alfil</h1>

<p align="center">Editor de video open source, simple y directo.</p>

---

**Alfil** es un editor de video de escritorio escrito en Python con PySide6 (Qt 6) que
usa **ffmpeg** por debajo. Abris un video, lo previsualizas, marcas inicio y fin, y
exportas el recorte. Sin nube, sin cuentas, sin marcas de agua: todo corre en tu maquina.

## Caracteristicas

- Reproductor integrado con barra de busqueda (scrub) y tiempo en `h:mm:ss.mmm`.
- Marcado de punto de inicio y de fin, con botones para saltar a cada uno.
- **Corte rapido**: copia los streams sin recodificar (instantaneo, corta en el keyframe
  mas cercano).
- **Corte preciso**: recodifica con `libx264` + `aac` para que el recorte arranque
  exactamente donde lo marcaste.
- Exportacion en un hilo aparte: la interfaz no se congela.
- `+faststart` activado, listo para subir a la web.
- Formatos: mp4, mkv, mov, avi, webm, m4v, flv, wmv.

## Requisitos

- Python 3.9 o superior.
- [ffmpeg](https://ffmpeg.org/download.html) en el `PATH`. En Windows tambien se busca
  en `C:\ffmpeg\bin\ffmpeg.exe` como alternativa.

## Instalacion

```bash
git clone <url-del-repo> alfil
cd alfil

python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
```

## Uso

```bash
python alfil.py
```

1. **Abrir video** y elegi el archivo.
2. Movete por la barra hasta donde quieras que empiece el recorte y marca el inicio.
3. Hace lo mismo para el fin.
4. Opcional: tilda *Corte rapido* si no te importa que el corte caiga en un keyframe.
5. **Exportar recorte** y elegi donde guardarlo.

### Atajos de teclado

| Tecla      | Accion                  |
| ---------- | ----------------------- |
| `Espacio`  | Play / Pausa            |
| `I`        | Marcar inicio           |
| `O`        | Marcar fin              |
| `<-` `->`  | Retroceder / avanzar 2s |

## Rapido vs preciso

| | Corte rapido | Corte preciso |
| --- | --- | --- |
| Velocidad | Casi instantaneo | Depende de la duracion |
| Calidad | Identica al original | Recodificada (CRF 20) |
| Exactitud del inicio | Keyframe mas cercano | Al milisegundo |

## Licencia

[MIT](LICENSE) - haz lo que quieras con el, solo mantene el aviso de copyright.
