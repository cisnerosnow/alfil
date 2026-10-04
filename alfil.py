"""alfil - recortador de video simple.

Abre un video, previsualizalo, marca inicio/fin y exporta el pedazo.
"""

import os
import shutil
import subprocess
import sys

from PySide6.QtCore import Qt, QThread, QUrl, Signal
from PySide6.QtGui import QIcon
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

LOGO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo-alfil.png")

VIDEO_FILTER = "Videos (*.mp4 *.mkv *.mov *.avi *.webm *.m4v *.flv *.wmv);;Todos (*.*)"


def find_ffmpeg():
    return shutil.which("ffmpeg") or r"C:\ffmpeg\bin\ffmpeg.exe"


def fmt(ms):
    """Milisegundos -> h:mm:ss.mmm"""
    if ms is None or ms < 0:
        ms = 0
    s, ms = divmod(int(ms), 1000)
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}.{ms:03d}"


class ExportJob(QThread):
    done = Signal(bool, str)

    def __init__(self, src, dst, start_ms, end_ms, fast):
        super().__init__()
        self.src, self.dst = src, dst
        self.start_ms, self.end_ms = start_ms, end_ms
        self.fast = fast

    def run(self):
        start = self.start_ms / 1000.0
        end = self.end_ms / 1000.0
        dur = end - start
        ffmpeg = find_ffmpeg()
        if self.fast:
            # -ss/-to despues del -i: seek mas lento pero la duracion sale exacta
            # y sin timestamps negativos. El primer frame igual cae en keyframe.
            cmd = [ffmpeg, "-y", "-i", self.src, "-ss", f"{start:.3f}", "-to", f"{end:.3f}",
                   "-c", "copy", "-avoid_negative_ts", "make_zero"]
        else:
            cmd = [ffmpeg, "-y", "-ss", f"{start:.3f}", "-i", self.src, "-t", f"{dur:.3f}",
                   "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                   "-c:a", "aac", "-b:a", "192k"]
        cmd += ["-movflags", "+faststart", self.dst]

        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, creationflags=flags)
        except FileNotFoundError:
            self.done.emit(False, "No encontre ffmpeg. Instalalo y agregalo al PATH.")
            return
        if p.returncode == 0:
            self.done.emit(True, self.dst)
        else:
            self.done.emit(False, (p.stderr or "").strip()[-1500:])


class Alfil(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("alfil")
        self.setWindowIcon(QIcon(LOGO))
        self.resize(900, 620)

        self.path = None
        self.duration = 0
        self.start_ms = 0
        self.end_ms = 0
        self.job = None
        self.scrubbing = False

        self.player = QMediaPlayer(self)
        self.audio = QAudioOutput(self)
        self.player.setAudioOutput(self.audio)
        self.video = QVideoWidget(self)
        self.video.setMinimumHeight(320)
        self.player.setVideoOutput(self.video)

        self.player.positionChanged.connect(self.on_position)
        self.player.durationChanged.connect(self.on_duration)
        self.player.playbackStateChanged.connect(self.on_state)
        self.player.errorOccurred.connect(self.on_error)

        # --- controles ---
        self.open_btn = QPushButton("Abrir video")
        self.open_btn.clicked.connect(self.open_file)
        self.file_lbl = QLabel("Ningun video cargado")
        self.file_lbl.setStyleSheet("color: #888;")

        self.seek = QSlider(Qt.Horizontal)
        self.seek.setRange(0, 0)
        self.seek.sliderPressed.connect(self.on_seek_press)
        self.seek.sliderReleased.connect(self.on_seek_release)
        self.seek.sliderMoved.connect(self.player.setPosition)

        self.time_lbl = QLabel("0:00:00.000 / 0:00:00.000")
        self.play_btn = QPushButton("Play")
        self.play_btn.clicked.connect(self.toggle_play)

        self.in_btn = QPushButton("Marcar inicio  [I]")
        self.in_btn.clicked.connect(self.mark_in)
        self.out_btn = QPushButton("Marcar fin  [O]")
        self.out_btn.clicked.connect(self.mark_out)
        self.range_lbl = QLabel("inicio 0:00:00.000   fin 0:00:00.000   dura 0:00:00.000")

        self.go_in = QPushButton("Ir a inicio")
        self.go_in.clicked.connect(lambda: self.player.setPosition(self.start_ms))
        self.go_out = QPushButton("Ir a fin")
        self.go_out.clicked.connect(lambda: self.player.setPosition(self.end_ms))

        self.fast_chk = QCheckBox("Corte rapido (sin recodificar, corta en keyframe)")

        self.export_btn = QPushButton("Exportar recorte")
        self.export_btn.clicked.connect(self.export)
        self.export_btn.setMinimumHeight(36)

        self.bar = QProgressBar()
        self.bar.setRange(0, 0)
        self.bar.hide()
        self.status = QLabel("")

        top = QHBoxLayout()
        top.addWidget(self.open_btn)
        top.addWidget(self.file_lbl, 1)

        play_row = QHBoxLayout()
        play_row.addWidget(self.play_btn)
        play_row.addWidget(self.time_lbl)
        play_row.addStretch(1)

        mark_row = QHBoxLayout()
        mark_row.addWidget(self.in_btn)
        mark_row.addWidget(self.out_btn)
        mark_row.addWidget(self.go_in)
        mark_row.addWidget(self.go_out)
        mark_row.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self.video, 1)
        layout.addWidget(self.seek)
        layout.addLayout(play_row)
        layout.addLayout(mark_row)
        layout.addWidget(self.range_lbl)
        layout.addWidget(self.fast_chk)
        layout.addWidget(self.export_btn)
        layout.addWidget(self.bar)
        layout.addWidget(self.status)

        self.set_enabled(False)

    # --- helpers ---
    def set_enabled(self, on):
        for w in (self.seek, self.play_btn, self.in_btn, self.out_btn,
                  self.go_in, self.go_out, self.export_btn):
            w.setEnabled(on)

    def refresh_range(self):
        self.range_lbl.setText(
            f"inicio {fmt(self.start_ms)}   fin {fmt(self.end_ms)}   "
            f"dura {fmt(max(0, self.end_ms - self.start_ms))}"
        )

    # --- acciones ---
    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Elegi un video", "", VIDEO_FILTER)
        if not path:
            return
        self.path = path
        self.player.setSource(QUrl.fromLocalFile(path))
        self.file_lbl.setText(os.path.basename(path))
        self.file_lbl.setStyleSheet("")
        self.status.setText("")
        self.set_enabled(True)
        self.player.play()

    def toggle_play(self):
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def mark_in(self):
        self.start_ms = self.player.position()
        if self.end_ms <= self.start_ms:
            self.end_ms = self.duration
        self.refresh_range()

    def mark_out(self):
        self.end_ms = self.player.position()
        if self.start_ms >= self.end_ms:
            self.start_ms = 0
        self.refresh_range()

    def export(self):
        if not self.path:
            return
        if self.end_ms - self.start_ms < 100:
            QMessageBox.warning(self, "alfil", "El rango es demasiado corto. Marca inicio y fin.")
            return
        base, ext = os.path.splitext(os.path.basename(self.path))
        suggested = os.path.join(os.path.dirname(self.path), f"{base}_recorte{ext}")
        dst, _ = QFileDialog.getSaveFileName(self, "Guardar recorte como", suggested, VIDEO_FILTER)
        if not dst:
            return
        if os.path.abspath(dst) == os.path.abspath(self.path):
            QMessageBox.warning(self, "alfil", "Elegi un archivo distinto al original.")
            return

        self.export_btn.setEnabled(False)
        self.bar.show()
        self.status.setText("Exportando...")
        self.job = ExportJob(self.path, dst, self.start_ms, self.end_ms, self.fast_chk.isChecked())
        self.job.done.connect(self.on_export_done)
        self.job.start()

    # --- senales ---
    def on_export_done(self, ok, msg):
        self.bar.hide()
        self.export_btn.setEnabled(True)
        if ok:
            self.status.setText(f"Listo: {msg}")
        else:
            self.status.setText("Fallo la exportacion.")
            QMessageBox.critical(self, "alfil", msg or "ffmpeg fallo.")

    def on_duration(self, ms):
        self.duration = ms
        self.seek.setRange(0, ms)
        self.start_ms = 0
        self.end_ms = ms
        self.refresh_range()

    def on_position(self, ms):
        if not self.scrubbing:
            self.seek.setValue(ms)
        self.time_lbl.setText(f"{fmt(ms)} / {fmt(self.duration)}")

    def on_seek_press(self):
        self.scrubbing = True

    def on_seek_release(self):
        self.scrubbing = False
        self.player.setPosition(self.seek.value())

    def on_state(self, state):
        self.play_btn.setText("Pausa" if state == QMediaPlayer.PlayingState else "Play")

    def on_error(self, error, msg):
        if error != QMediaPlayer.NoError:
            self.status.setText(f"No pude reproducir el video: {msg}")

    def keyPressEvent(self, e):
        if not self.path:
            return super().keyPressEvent(e)
        k = e.key()
        if k == Qt.Key_Space:
            self.toggle_play()
        elif k == Qt.Key_I:
            self.mark_in()
        elif k == Qt.Key_O:
            self.mark_out()
        elif k == Qt.Key_Left:
            self.player.setPosition(max(0, self.player.position() - 2000))
        elif k == Qt.Key_Right:
            self.player.setPosition(min(self.duration, self.player.position() + 2000))
        else:
            super().keyPressEvent(e)


def main():
    if os.name == "nt":
        # Sin esto Windows agrupa la ventana bajo el icono de python.exe.
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("alfil.editor")
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(LOGO))
    w = Alfil()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
