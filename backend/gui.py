import sys
import time
import math
import threading

from PySide6.QtCore import (
    QObject,
    Signal,
    Slot,
    Qt,
    QTimer,
    QRectF,
    QPointF,
)
from PySide6.QtGui import (
    QFont,
    QColor,
    QPen,
    QBrush,
    QRadialGradient,
    QPainter,
    QTextCursor,
)
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTextEdit,
    QLineEdit,
    QPushButton,
    QFrame,
)

from brain import ask_jarvis_stream, warmup
from voice import wait_for_wake_word, listen_command
from tts import speak


# ============================================================
# PALETA HOLOGRÁFICA
# ============================================================

class Palette:
    BG = "#04070c"
    BG_PANEL = "#0a1018"

    # cian (estado base / JARVIS)
    CYAN = "#39d6ff"
    CYAN_DIM = "#1c6d8a"
    CYAN_GLOW = "#7ceaff"

    # verde (escuchando)
    GREEN = "#4ef2a1"
    GREEN_DIM = "#1f6d4a"

    # ámbar (procesando)
    AMBER = "#ffc857"
    AMBER_DIM = "#8a6a1c"

    # violeta (hablando)
    VIOLET = "#b78cff"
    VIOLET_DIM = "#5a3f8a"

    GRID = "#10242f"
    TEXT = "#d8f4ff"
    TEXT_DIM = "#4e7a8a"
    TEXT_FAINT = "#2c4a57"

    MONO = "Consolas"


# ============================================================
# ESTADO -> COLOR
# ============================================================

STATE_COLORS = {
    "WAITING":   {"main": "#39d6ff", "dim": "#1c6d8a", "glow": "#7ceaff"},
    "LISTENING": {"main": "#4ef2a1", "dim": "#1f6d4a", "glow": "#a3ffd1"},
    "PROCESSING": {"main": "#ffc857", "dim": "#8a6a1c", "glow": "#ffe2a1"},
    "SPEAKING":  {"main": "#b78cff", "dim": "#5a3f8a", "glow": "#e0d0ff"},
}


# ============================================================
# WORKER DE JARVIS
# ============================================================

class JarvisWorker(QObject):
    token = Signal(str)
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, message):
        super().__init__()
        self.message = message

    def run(self):
        try:
            parts = []

            for piece in ask_jarvis_stream(self.message):

                if piece.strip():
                    parts.append(piece)
                    self.token.emit(piece)

            if parts:
                answer = "".join(parts)
            else:
                answer = ""

            if answer is None:
                answer = ""

            self.finished.emit(answer)

        except Exception as e:
            self.error.emit(str(e))


# ============================================================
# WORKER DE TTS
# ============================================================

class TTSWorker(QObject):
    finished = Signal()
    error = Signal(str)

    def __init__(self, text):
        super().__init__()
        self.text = text

    @Slot()
    def run(self):
        try:
            speak(self.text)
            self.finished.emit()

        except Exception as e:
            self.error.emit(str(e))


# ============================================================
# WORKER DE VOZ
# ============================================================

class VoiceWorker(QObject):
    wake_detected = Signal(float)
    command_detected = Signal(str)
    listening_started = Signal()
    processing_started = Signal()
    error = Signal(str)

    def __init__(self):
        super().__init__()
        self.running = True

    @Slot()
    def run(self):

        while self.running:

            try:

                score = wait_for_wake_word(self._stop_event())

                if not self.running:
                    break

                if score is None:
                    continue

                self.wake_detected.emit(score)

                self.listening_started.emit()

                command = listen_command(self._stop_event())

                if not self.running:
                    break

                if command:
                    self.command_detected.emit(command)
                else:
                    self.processing_started.emit()

            except Exception as e:

                self.error.emit(str(e))

                time.sleep(1)

    def _stop_event(self):

        class StopEvent:

            def __init__(self, worker):
                self.worker = worker

            def is_set(self):
                return not self.worker.running

        return StopEvent(self)

    def stop(self):
        self.running = False


# ============================================================
# NÚCLEO HOLOGRÁFICO — ESFERA 3D TIPO JARVIS (IRON MAN)
# ============================================================

class HoloCore(QWidget):
    """Esfera/globo holográfico 3D tipo JARVIS: una nube densa
    de puntos sobre una esfera proyectada en perspectiva (puntos
    cercanos más grandes y brillantes), con núcleo pulsante,
    anillo orbital elíptico inclinado, arcos HUD discontinuos y
    un anillo exterior de marcas de graduación."""

    N_POINTS = 620

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setFixedSize(380, 380)

        self._angle = 0.0
        self._tick = 0
        self.state = "WAITING"
        self.pulse = 1.0

        # inclinación del globo (rotación Y fija para darle 3D)
        self.tilt_x = 0.42   # radianes
        self.tilt_y = 0.30

        # marcas de graduación exteriores
        self.ticks = 72

        self._build_sphere()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._advance)
        self.timer.start(16)

    # --------------------------------------------------------
    # Construcción de la nube de puntos (esfera de Fibonacci)
    # --------------------------------------------------------

    def _build_sphere(self):
        pts = []
        n = HoloCore.N_POINTS
        golden = math.pi * (3.0 - math.sqrt(5.0))
        for i in range(n):
            y = 1.0 - (i / float(n - 1)) * 2.0
            r = math.sqrt(max(0.0, 1.0 - y * y))
            theta = golden * i
            x = math.cos(theta) * r
            z = math.sin(theta) * r
            pts.append((x, y, z))
        self._points = pts

    # --------------------------------------------------------
    # Animación
    # --------------------------------------------------------

    def _advance(self):
        self._angle += 0.5  # grados, ajustado por estado abajo
        self._tick += 1
        self.pulse += 0.025
        if self.pulse > 1.0:
            self.pulse = 1.0
        self.update()

    # --------------------------------------------------------
    # Estado
    # --------------------------------------------------------

    def set_state(self, state):
        self.state = state
        self.pulse = 0.25
        self.update()

    def _colors(self):
        return STATE_COLORS.get(
            self.state,
            STATE_COLORS["WAITING"],
        )

    def _breath_scale(self):
        # el globo "respira" en reposo y pulsa fuerte al hablar
        if self.state == "SPEAKING":
            return 1.0 + 0.045 * math.sin((self._tick / 8.0))
        if self.state in ("LISTENING", "PROCESSING"):
            return 1.0 + 0.02 * math.sin(self._tick / 10.0)
        return 1.0 + 0.012 * math.sin(self._tick / 26.0)

    # --------------------------------------------------------
    # Pintado
    # --------------------------------------------------------

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        cx = w / 2.0
        cy = h / 2.0

        col = self._colors()
        main = QColor(col["main"])
        glow = QColor(col["glow"])
        dim = QColor(col["dim"])

        self._paint_glow(painter, cx, cy, main, glow)
        self._paint_ticks(painter, cx, cy, dim, glow)
        self._paint_hud_arcs(painter, cx, cy, main, dim, glow)
        self._paint_sphere(painter, cx, cy, main, glow)
        self._paint_orbit_ring(painter, cx, cy, main, glow)
        self._paint_core(painter, cx, cy, glow, main)

        painter.end()

    def _paint_glow(self, painter, cx, cy, main, glow):
        r = QRadialGradient(QPointF(cx, cy), 185)
        base = QColor(main)
        base.setAlpha(34)
        r.setColorAt(0.0, base)
        outer = QColor(main)
        outer.setAlpha(4)
        r.setColorAt(1.0, outer)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(r))
        painter.drawEllipse(QRectF(cx - 185, cy - 185, 370, 370))

    def _paint_ticks(self, painter, cx, cy, dim, glow):
        R = 178
        long_t = QColor(glow)
        long_t.setAlpha(150)
        width = 2 if self._tick % 6 == 0 else 1
        for i in range(self.ticks):
            a = math.radians((360.0 / self.ticks) * i)
            x0 = cx + R * math.cos(a)
            y0 = cy + R * math.sin(a)
            ln = 8 if i % 6 == 0 else 4
            x1 = cx + (R - ln) * math.cos(a)
            y1 = cy + (R - ln) * math.sin(a)
            c = QColor(glow) if i % 6 == 0 else QColor(dim)
            pen = QPen(c)
            pen.setWidthF(width)
            painter.setPen(pen)
            painter.drawLine(QPointF(x0, y0), QPointF(x1, y1))

    def _paint_hud_arcs(self, painter, cx, cy, main, dim, glow):
        arcs = [
            {"r": 150, "w": 1.2, "span": 120, "speed": 0.9},
            {"r": 128, "w": 2.4, "span": 80,  "speed": -1.4},
            {"r": 108, "w": 1.0, "span": 220, "speed": 0.6},
            {"r": 72,  "w": 1.8, "span": 100, "speed": -1.0},
        ]
        for i, a in enumerate(arcs[:2]):
            pen = QPen(QColor(dim))
            pen.setWidth(1)
            pen.setStyle(Qt.DashLine)
            painter.setOpacity(0.5)
            painter.setPen(pen)
            painter.drawEllipse(QRectF(cx - a["r"], cy - a["r"],
                                       a["r"] * 2, a["r"] * 2))
            painter.setOpacity(1.0)
        for i, a in enumerate(arcs):
            start = (self._angle * a["speed"] * 6 + i * 90) % 360.0
            pen = QPen(QColor(glow))
            pen.setWidthF(a["w"])
            pen.setCapStyle(Qt.RoundCap)
            painter.setPen(pen)
            painter.setOpacity(0.85)
            painter.drawArc(
                QRectF(cx - a["r"], cy - a["r"], a["r"] * 2, a["r"] * 2),
                int(-start * 16), int(-a["span"] * 16),
            )
            painter.setOpacity(1.0)

    def _paint_sphere(self, painter, cx, cy, main, glow):
        scale = self._breath_scale()
        R = 66 * scale

        tx = self._angle * math.pi / 180.0
        siny, cosy = math.sin(self.tilt_y), math.cos(self.tilt_y)
        sinx, cosx = math.sin(self.tilt_x), math.cos(self.tilt_x)

        for (px, py, pz) in self._points:
            # rotar Y (giro continuo del globo)
            x1 = px * cosy + pz * siny
            z1 = -px * siny + pz * cosy
            # rotar X (inclinación fija)
            y1 = py * cosx - z1 * sinx
            z2 = py * sinx + z1 * cosx

            # el giro continuo: añadir rotación alrededor del eje Y
            ang = tx
            x2 = x1 * math.cos(ang) - z2 * math.sin(ang)
            z3 = x1 * math.sin(ang) + z2 * math.cos(ang)

            depth = z3  # profundidad de perspectiva

            # proyección simple en perspectiva
            persp = 1.0 + depth * 0.35
            sx = cx + x2 * R * persp
            sy = cy + y1 * R * persp

            # brillo/tamaño según profundidad (3D)
            if depth < 0:
                brightness = 0.25 + 0.55 * (1.0 + depth / 1.0)
                size = 1.0 + 2.6 * (1.0 + depth / 1.0)
            else:
                brightness = 0.15 + 0.25 * (1.0 - depth / 1.0)
                size = 0.8 + 0.6 * (1.0 - depth / 1.0)

            c = QColor(glow)
            c.setAlphaF(max(0.05, min(1.0, brightness)))
            pen = QPen(c)
            pen.setWidthF(max(0.6, size * 0.55))
            painter.setPen(pen)
            painter.drawPoint(QPointF(sx, sy))

        # contorno suave del globo
        rim = QPen(QColor(main))
        rim.setWidthF(1.2)
        rim.setColor(QColor(glow))
        painter.setOpacity(0.5)
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(QRectF(cx - R, cy - R, R * 2, R * 2))
        painter.setOpacity(1.0)

    def _paint_orbit_ring(self, painter, cx, cy, main, glow):
        # anillo orbital elíptico inclinado alrededor del globo
        rot = math.radians(self._angle * 2.0 + 45)
        tilt = math.radians(24.0)
        rx = 115
        ry = rx * math.cos(tilt) * 0.85

        painter.save()
        painter.translate(cx, cy)
        painter.rotate(9.0)

        base_col = QColor(main)
        base_col.setAlpha(90)
        pen = QPen(base_col)
        pen.setWidth(1)
        painter.setOpacity(0.55)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(QRectF(-rx, -ry, rx * 2, ry * 2))
        painter.setOpacity(1.0)

        # marcador brillante orbitando la elipse
        ox = rx * math.cos(rot)
        oy = ry * math.sin(rot)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(glow)))
        painter.drawEllipse(QRectF(ox - 4, oy - 4, 8, 8))

        # estela
        pen2 = QPen(QColor(glow))
        pen2.setWidthF(2.2)
        pen2.setCapStyle(Qt.RoundCap)
        painter.setOpacity(0.85)
        painter.setPen(pen2)
        painter.drawArc(QRectF(-rx, -ry, rx * 2, ry * 2),
                        int(math.degrees(rot) * 16), int(-70 * 16))
        painter.setOpacity(1.0)

        painter.restore()

    def _paint_core(self, painter, cx, cy, glow, main):
        # núcleo interior pulsante (el "cerebro")
        pulse = self.pulse
        r = 35 + 8 * pulse

        grad = QRadialGradient(QPointF(cx - 4, cy - 4), r)
        c0 = QColor(glow)
        c0.setAlpha(230)
        grad.setColorAt(0.0, c0)
        c1 = QColor(main)
        c1.setAlpha(180)
        grad.setColorAt(0.7, c1)
        c2 = QColor("#04101c")
        grad.setColorAt(1.0, c2)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(grad))
        painter.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))

        # J.A.R.V.I.S en horizontal, grande, centrado
        name = "J.A.R.V.I.S"
        f = QFont(Palette.MONO, 19, QFont.Bold)
        painter.setFont(f)
        fm = painter.fontMetrics()
        total_w = fm.horizontalAdvance(name)
        total_h = fm.height()

        painter.setPen(QColor(glow))

        # resplandor suave para la legibilidad
        painter.setOpacity(0.35)
        glow_col = QColor(main)
        painter.setPen(glow_col)
        painter.drawText(
            QRectF(cx - total_w / 2.0 - 1, cy - total_h / 2.0 - 1,
                   total_w + 2, total_h + 2),
            Qt.AlignCenter,
            name,
        )
        painter.setOpacity(1.0)

        painter.setPen(QColor(glow))
        painter.drawText(
            QRectF(cx - total_w / 2.0, cy - total_h / 2.0,
                   total_w, total_h),
            Qt.AlignCenter,
            name,
        )

        # indicador de estado bajo las siglas
        marker = {"WAITING": "□", "LISTENING": "◉",
                  "PROCESSING": "•••", "SPEAKING": "◄►"}[self.state]
        mf = QFont(Palette.MONO, 8, QFont.Bold)
        painter.setFont(mf)
        painter.setOpacity(0.9)
        painter.drawText(
            QRectF(cx - 60, cy + total_h / 2.0 + 4, 120, 14),
            Qt.AlignCenter,
            marker,
        )
        painter.setOpacity(1.0)


# ============================================================
# VENTANA PRINCIPAL
# ============================================================

class JarvisWindow(QMainWindow):

    def __init__(self):

        super().__init__()

        self.setWindowTitle("J.A.R.V.I.S — HOLOGRAPHIC INTERFACE")

        self.resize(1180, 800)

        self.setMinimumSize(900, 680)

        self.thread = None
        self.worker = None

        self.active_threads = []
        self.active_tts_threads = []

        self.voice_thread = None
        self.voice_worker = None

        self.processing = False

        self.voice_enabled = True

        self.processing = False
        self._pending_message = None
        self._stream_active = False

        # temporizador: muestra segundos de procesamiento
        self._proc_start = 0.0
        self._proc_timer = QTimer(self)
        self._proc_timer.setInterval(1000)
        self._proc_timer.timeout.connect(self._update_proc_time)

        self.setup_ui()

        self.start_voice()

        # Calentar el modelo en segundo plano para evitar
        # los ~25s de arranque en frío en el primer mensaje.
        threading.Thread(
            target=warmup,
            daemon=True
        ).start()

    # ========================================================
    # UI
    # ========================================================

    def setup_ui(self):

        self.setStyleSheet(self._global_stylesheet())

        central = QWidget()
        central.setObjectName("root")
        central.setStyleSheet("QWidget#root { background-color: #04070c; }")
        self.setCentralWidget(central)

        outer = QHBoxLayout(central)
        outer.setContentsMargins(18, 14, 18, 14)
        outer.setSpacing(14)

        # ================================================
        # PANEL IZQUIERDO — HUD TÉCNICO
        # ================================================
        left_panel = QFrame()
        left_panel.setObjectName("hudPanel")
        left_panel.setFixedWidth(190)
        left_panel.setStyleSheet(self._panel_stylesheet())
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(14, 16, 14, 16)
        left_layout.setSpacing(12)

        left_layout.addLayout(self._make_panel_label("SISTEMA", "#39d6ff"))

        sys_metrics = [
            ("CEREBRO", "QWEN3 8B"),
            ("VOZ", "WHISPER"),
            ("TTS", "SYNTH"),
            ("NÚCLEO", "LOCAL"),
        ]
        for k, v in sys_metrics:
            left_layout.addLayout(self._metric_row(k, v))

        left_layout.addSpacing(6)
        left_layout.addLayout(self._make_panel_label("COMANDOS", "#4ef2a1"))

        cmd_help = [
            ("WAKE", "DI JARVIS"),
            ("ESCUCHAR", "AUTOMÁTICO"),
            ("TEXTO", "ESCRIBIR"),
            ("MIC", "TOGGLE"),
        ]
        for k, v in cmd_help:
            left_layout.addLayout(self._metric_row(k, v, color="#9aefca"))

        left_layout.addStretch()

        left_layout.addLayout(self._make_panel_label("ESTADO", "#ffc857"))
        self.hud_state = QLabel("ESPERE")
        self.hud_state.setFont(QFont(Palette.MONO, 9, QFont.Bold))
        self.hud_state.setStyleSheet("color:#ffc857;")
        left_layout.addWidget(self.hud_state)

        outer.addWidget(left_panel)

        # ================================================
        # COLUMNA CENTRAL — NÚCLEO + CHAT
        # ================================================
        center_col = QVBoxLayout()
        center_col.setSpacing(12)

        # --- HEADER HOLOGRÁFICO ---
        center_col.addLayout(self._build_header())

        # --- NÚCLEO ---
        core_container = QVBoxLayout()
        core_container.setAlignment(Qt.AlignCenter)
        self.core_widget = HoloCore()
        core_container.addWidget(self.core_widget, alignment=Qt.AlignCenter)

        self.status_label = QLabel("SISTEMA EN ESPERA")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFont(QFont(Palette.MONO, 12, QFont.Bold))
        self.status_label.setStyleSheet("color:#39d6ff; letter-spacing:4px;")
        core_container.addWidget(self.status_label)

        center_col.addLayout(core_container, stretch=1)

        # --- CHAT ---
        self.chat = QTextEdit()
        self.chat.setReadOnly(True)
        self.chat.setFont(QFont(Palette.MONO, 10))
        self.chat.setPlaceholderText(
            "[ TRANSMISIÓN DE DATOS — LA CONVERSACIÓN APARECERÁ AQUÍ ]"
        )
        self.chat.setStyleSheet("""
            QTextEdit {
                background-color: #070d14;
                color: #c9e6f2;
                border: 1px solid #12303d;
                border-radius: 12px;
                padding: 14px;
                selection-background-color: #13516a;
            }
        """)
        center_col.addWidget(self.chat, stretch=1)

        # --- INPUT ---
        center_col.addWidget(self._build_input())

        outer.addLayout(center_col, stretch=1)

        # ================================================
        # PANEL DERECHO — TELEMETRÍA
        # ================================================
        right_panel = QFrame()
        right_panel.setObjectName("hudPanel")
        right_panel.setFixedWidth(210)
        right_panel.setStyleSheet(self._panel_stylesheet())
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(14, 16, 14, 16)
        right_layout.setSpacing(12)

        right_layout.addLayout(self._make_panel_label("TELEMETRÍA", "#b78cff"))

        self.telemetry = QLabel()
        self.telemetry.setFont(QFont(Palette.MONO, 9))
        self.telemetry.setStyleSheet("color:#8fb8c9;")
        self.telemetry.setText(
            "POTENCIA  100%\n"
            "NÚCLEO    ONLINE\n"
            "RED       LOCAL\n"
            "MODELO    QWEN3\n\n"
            "· . . . . . . .\n"
            "· J.A.R.V.I.S\n"
            "· SISTEMAS OK"
        )
        self.telemetry.setTextFormat(Qt.RichText)
        right_layout.addWidget(self.telemetry)

        right_layout.addSpacing(6)
        right_layout.addLayout(self._make_panel_label("PROTOCOLO", "#39d6ff"))

        self.protocol = QLabel(
            "▸ WAKEWORD CARGADO\n"
            "▸ AUDIO: OK\n"
            "▸ TTS: INICIALIZADO\n"
            "▸ CEREBRO: LISTO"
        )
        self.protocol.setFont(QFont(Palette.MONO, 9))
        self.protocol.setStyleSheet("color:#4e7a8a;")
        right_layout.addWidget(self.protocol)

        right_layout.addStretch()

        right_layout.addLayout(self._make_panel_label("MICRÓFONO", "#4ef2a1"))
        self.voice_status = QLabel("● ACTIVO")
        self.voice_status.setFont(QFont(Palette.MONO, 9, QFont.Bold))
        self.voice_status.setStyleSheet("color:#4ef2a1;")
        right_layout.addWidget(self.voice_status)

        self.mic_button = QPushButton("MIC ON")
        self.mic_button.clicked.connect(self.toggle_voice)
        self.mic_button.setStyleSheet(self._button_stylesheet("#4ef2a1", "#0d241b"))
        right_layout.addWidget(self.mic_button)

        outer.addWidget(right_panel)

        self.append_system_message(
            "J.A.R.V.I.S iniciado. Sistemas locales preparados."
        )

    # --------------------------------------------------------
    # CONSTRUCTORES DE UI
    # --------------------------------------------------------

    def _make_panel_label(self, text, color):
        lay = QHBoxLayout()
        bar = QFrame()
        bar.setFixedSize(12, 2)
        bar.setStyleSheet(f"background-color:{color}; border:none;")
        lab = QLabel(text)
        lab.setFont(QFont(Palette.MONO, 9, QFont.Bold))
        lab.setStyleSheet(f"color:{color}; letter-spacing:2px;")
        lay.addWidget(bar)
        lay.addWidget(lab)
        lay.addStretch()
        return lay

    def _metric_row(self, key, value, color="#8fb8c9"):
        row = QHBoxLayout()
        k = QLabel(key)
        k.setFont(QFont(Palette.MONO, 8))
        k.setStyleSheet("color:#4e7a8a;")
        v = QLabel(value)
        v.setFont(QFont(Palette.MONO, 8, QFont.Bold))
        v.setStyleSheet(f"color:{color};")
        row.addWidget(k)
        row.addStretch()
        row.addWidget(v)
        return row

    def _build_header(self):
        header = QHBoxLayout()
        header.setSpacing(12)

        left_block = QVBoxLayout()
        left_block.setSpacing(1)

        title = QLabel("J.A.R.V.I.S")
        title.setFont(QFont(Palette.MONO, 22, QFont.Bold))
        title.setStyleSheet("color:#d8f4ff; letter-spacing:6px;")

        sub = QLabel("JUST A RATHER VERY INTELLIGENT SYSTEM")
        sub.setFont(QFont(Palette.MONO, 8))
        sub.setStyleSheet("color:#4e7a8a; letter-spacing:2px;")

        left_block.addWidget(title)
        left_block.addWidget(sub)
        header.addLayout(left_block)

        header.addStretch()

        header.addWidget(self._hud_chip("LOCAL", "#39d6ff"))
        header.addWidget(self._hud_chip("HOLOGRAFICO", "#4ef2a1"))
        header.addWidget(self._hud_chip("ONLINE", "#ffc857"))

        return header

    def _hud_chip(self, text, color):
        chip = QLabel(text)
        chip.setFont(QFont(Palette.MONO, 8, QFont.Bold))
        chip.setStyleSheet(
            f"color:{color}; border:1px solid {color};"
            f"border-radius:6px; padding:4px 8px; background-color:#0a141c;"
        )
        return chip

    def _build_input(self):
        container = QFrame()
        container.setStyleSheet("""
            QFrame {
                background-color: #070d14;
                border: 1px solid #12303d;
                border-radius: 12px;
            }
        """)

        layout = QHBoxLayout(container)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(8)

        self.input_box = QLineEdit()
        self.input_box.setPlaceholderText(
            "escribe un mensaje para J.A.R.V.I.S >_"
        )
        self.input_box.setFont(QFont(Palette.MONO, 10))
        self.input_box.setStyleSheet("""
            QLineEdit {
                background-color: transparent;
                color: #d8f4ff;
                border: none;
                padding: 10px;
            }
            QLineEdit:focus { border: none; }
        """)
        self.input_box.returnPressed.connect(self.send_message)
        layout.addWidget(self.input_box, stretch=1)

        self.send_button = QPushButton("ENVIAR")
        self.send_button.setFixedSize(90, 42)
        self.send_button.clicked.connect(self.send_message)
        self.send_button.setStyleSheet(
            self._button_stylesheet("#39d6ff", "#0d2130")
        )
        layout.addWidget(self.send_button)

        return container

    def _button_stylesheet(self, color, bg):
        return f"""
            QPushButton {{
                background-color: {bg};
                color: {color};
                border: 1px solid {color};
                border-radius: 8px;
                font-family: {Palette.MONO};
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {color}26;
            }}
            QPushButton:pressed {{
                background-color: {color}40;
            }}
            QPushButton:disabled {{
                color: #2c4a57;
                border-color: #12303d;
                background-color: #0a1018;
            }}
        """

    def _panel_stylesheet(self):
        return """
            QFrame#hudPanel {
                background-color: #080e15;
                border: 1px solid #102b36;
                border-radius: 12px;
            }
        """

    def _global_stylesheet(self):
        return """
            QMainWindow { background-color: #04070c; }
            QWidget { background-color: #04070c; }

            QScrollBar:vertical {
                background: #080f15; width: 8px; margin: 2px;
            }
            QScrollBar::handle:vertical {
                background: #1c4c5e; border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background: #2a6a82;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical { height: 0px; }
        """

    # ========================================================
    # MENSAJES
    # ========================================================

    def append_user_message(self, text):
        self.chat.append(
            f"""
            <div style="margin-top:12px; margin-bottom:4px;
                 color:#39d6ff; font-weight:bold;">
                ▶ TÚ
            </div>
            <div style="color:#d8f4ff; margin-bottom:10px;">
                {self.escape_html(text)}
            </div>
            """
        )
        self.scroll_chat()

    def append_jarvis_message(self, text):
        self.chat.append(
            f"""
            <div style="margin-top:12px; margin-bottom:4px;
                 color:#b78cff; font-weight:bold;">
                ◈ J.A.R.V.I.S
            </div>
            <div style="color:#e3edf2; margin-bottom:10px;">
                {self.escape_html(text)}
            </div>
            """
        )
        self.scroll_chat()

    def append_system_message(self, text):
        self.chat.append(
            f"""
            <div style="margin-top:8px; margin-bottom:8px;
                 color:#4e7a8a; font-size:9pt;">
                [ SYS ] {self.escape_html(text)}
            </div>
            """
        )
        self.scroll_chat()

    @staticmethod
    def escape_html(text):
        return (
            text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("\n", "<br>")
        )

    def scroll_chat(self):
        scrollbar = self.chat.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    # ========================================================
    # ESTADOS
    # ========================================================

    def set_state(self, state):

        states = {
            "WAITING":   ("SISTEMA EN ESPERA", "#39d6ff", "ESPERE"),
            "LISTENING": ("ESCUCHANDO",        "#4ef2a1", "MIC ACTIVO"),
            "PROCESSING":("PROCESANDO",        "#ffc857", "CEREBRO"),
            "SPEAKING":  ("HABLANDO",          "#b78cff", "VOZ"),
        }

        text, color, hud = states.get(state, states["WAITING"])

        self.status_label.setText(text)
        self.status_label.setStyleSheet(
            f"color:{color}; letter-spacing:4px;"
        )

        self.hud_state.setText(hud)
        self.hud_state.setStyleSheet(f"color:{color};")

        self.core_widget.set_state(state)

    # ========================================================
    # ENVIAR MENSAJE
    # ========================================================

    def send_message(self):

        message = self.input_box.text().strip()

        if not message:
            return

        # Si JARVIS sigue procesando, encolamos el mensaje
        # en lugar de ignorarlo silenciosamente.
        if self.processing:

            if self._pending_message is None:

                self._pending_message = message
                self.input_box.clear()

                self.append_system_message(
                    "Mensaje en cola, se enviará al terminar..."
                )

            # con un pendiente ya activo no se pierde lo que
            # hay escrito en la caja
            return

        self.input_box.clear()
        self.append_user_message(message)
        self.start_processing(message)

    # ========================================================
    # PROCESAMIENTO QWEN
    # ========================================================

    def _update_proc_time(self):

        elapsed = int(
            time.monotonic() - self._proc_start
        )

        self.hud_state.setText(
            f"CEREBRO {elapsed}s"
        )

    def start_processing(self, message):

        if self.processing:
            return

        self.processing = True
        self._stream_active = False
        self.set_state("PROCESSING")
        self.send_button.setEnabled(False)

        self._proc_start = time.monotonic()
        self._proc_timer.start()

        worker = JarvisWorker(message)

        worker.token.connect(self.on_token)
        worker.finished.connect(self.on_response)
        worker.error.connect(self.on_error)

        thread = threading.Thread(
            target=worker.run,
            daemon=True,
        )
        thread.start()

        self.active_threads.append(thread)
        self._active_work = worker

    @Slot(str)
    def on_token(self, piece):

        # inserta el encabezado solo la primera vez
        if not self._stream_active:

            self._stream_active = True

            self.chat.append(
                """
                <div style="margin-top:12px; margin-bottom:4px;
                     color:#b78cff; font-weight:bold;">
                    ◈ J.A.R.V.I.S
                </div>
                """
            )

        cursor = self.chat.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertHtml(
            self.escape_html(piece)
        )

        self.scroll_chat()

    @Slot(str)
    def on_response(self, answer):

        self.processing = False
        self.send_button.setEnabled(True)
        self._proc_timer.stop()
        self._stream_active = False

        # La respuesta ya se mostró pieza a pieza con on_token.
        if answer:
            self.set_state("SPEAKING")
            self.start_tts(answer)
        else:
            self.finish_processing()

    @Slot(str)
    def on_error(self, error):

        self.processing = False
        self.send_button.setEnabled(True)
        self._stream_active = False
        self.append_system_message(f"Error: {error}")
        self.finish_processing()

    # ========================================================
    # TTS
    # ========================================================

    def start_tts(self, text):

        worker = TTSWorker(text)

        worker.finished.connect(self.on_tts_finished)
        worker.error.connect(self.on_tts_error)

        thread = threading.Thread(
            target=worker.run,
            daemon=True,
        )
        thread.start()

        self.active_tts_threads.append(thread)
        self._active_tts_work = worker

    @Slot()
    def on_tts_finished(self):
        self.finish_processing()

    @Slot(str)
    def on_tts_error(self, error):
        self.append_system_message(f"Error de voz: {error}")
        self.finish_processing()

    # ========================================================
    # FINALIZAR
    # ========================================================

    def finish_processing(self):
        self.processing = False
        self.send_button.setEnabled(True)
        self._proc_timer.stop()
        self.set_state("WAITING")

        # Si quedó un mensaje en cola, enviarlo ahora.
        pending = self._pending_message
        self._pending_message = None

        if pending:
            self.append_user_message(pending)
            self.start_processing(pending)

    # ========================================================
    # VOZ
    # ========================================================

    def start_voice(self):

        if self.voice_thread is not None:
            if self.voice_thread.is_alive():
                return

        self.voice_enabled = True
        self.voice_status.setText("● ACTIVO")
        self.voice_status.setStyleSheet("color:#4ef2a1;")
        self.mic_button.setText("MIC ON")
        self.mic_button.setStyleSheet(self._button_stylesheet("#4ef2a1", "#0d241b"))

        self.voice_worker = VoiceWorker()

        self.voice_worker.wake_detected.connect(self.on_wake_detected)
        self.voice_worker.listening_started.connect(self.on_listening_started)
        self.voice_worker.command_detected.connect(self.on_voice_command)
        self.voice_worker.processing_started.connect(self.on_voice_processing)
        self.voice_worker.error.connect(self.on_voice_error)

        thread = threading.Thread(
            target=self.voice_worker.run,
            daemon=True,
        )
        thread.start()
        self.voice_thread = thread

    def stop_voice(self):

        self.voice_enabled = False

        if self.voice_worker is not None:
            self.voice_worker.stop()

        if self.voice_thread is not None:
            if self.voice_thread.is_alive():
                self.voice_thread.join(timeout=2000)

        self.voice_worker = None
        self.voice_thread = None

        self.voice_status.setText("○ INACTIVO")
        self.voice_status.setStyleSheet("color:#2c4a57;")
        self.mic_button.setText("MIC OFF")
        self.mic_button.setStyleSheet(self._button_stylesheet("#2c4a57", "#0a1018"))

    # ========================================================
    # EVENTOS DE VOZ
    # ========================================================

    @Slot(float)
    def on_wake_detected(self, score):
        self.set_state("LISTENING")

    @Slot()
    def on_listening_started(self):
        self.set_state("LISTENING")

    @Slot(str)
    def on_voice_command(self, command):
        if not command:
            return
        self.append_user_message(command)
        self.start_processing(command)

    @Slot()
    def on_voice_processing(self):
        self.set_state("PROCESSING")

    @Slot(str)
    def on_voice_error(self, error):
        self.append_system_message(f"Error de micrófono: {error}")

    # ========================================================
    # BOTÓN MICRÓFONO
    # ========================================================

    def toggle_voice(self):
        if self.voice_enabled:
            self.stop_voice()
        else:
            self.start_voice()

    # ========================================================
    # CIERRE
    # ========================================================

    def closeEvent(self, event):

        self.stop_voice()

        for thread in self.active_threads:
            if thread.is_alive():
                thread.join(timeout=2000)

        for thread in self.active_tts_threads:
            if thread.is_alive():
                thread.join(timeout=2000)

        event.accept()


# ============================================================
# MAIN
# ============================================================

def main():

    app = QApplication(sys.argv)
    app.setApplicationName("J.A.R.V.I.S")

    window = JarvisWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
