import sys
import time

from PySide6.QtCore import (
    QObject,
    QThread,
    Signal,
    Slot,
    Qt,
    QTimer,
    QPropertyAnimation,
    QEasingCurve,
)
from PySide6.QtGui import QFont
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
    QSizePolicy,
)

from brain import ask_jarvis
from voice import wait_for_wake_word, listen_command
from tts import speak


# ============================================================
# WORKER DE JARVIS
# ============================================================

class JarvisWorker(QObject):
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, message):
        super().__init__()
        self.message = message

    @Slot()
    def run(self):
        try:
            answer = ask_jarvis(self.message)

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
# NÚCLEO CENTRAL
# ============================================================

class CoreWidget(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setFixedSize(220, 220)

        self.animation = None
        self.pulse_animation = None

        self.core = QLabel(self)
        self.core.setAlignment(Qt.AlignCenter)

        self.core.setFixedSize(150, 150)

        self.core.move(35, 35)

        self.core.setText("J")

        self.core.setFont(
            QFont("Segoe UI", 32, QFont.Bold)
        )

        self.core.setStyleSheet("""
            QLabel {
                background-color: #101820;
                color: #6fdcff;
                border: 2px solid #3abff8;
                border-radius: 75px;
            }
        """)

        self.glow = QLabel(self)
        self.glow.setGeometry(10, 10, 200, 200)

        self.glow.lower()

        self.glow.setStyleSheet("""
            QLabel {
                background-color: transparent;
                border: 1px solid #1d6d8a;
                border-radius: 100px;
            }
        """)

        self.start_animation()

    def start_animation(self):

        self.pulse_animation = QPropertyAnimation(
            self.core,
            b"minimumSize"
        )

        self.pulse_animation.setDuration(1400)
        self.pulse_animation.setStartValue(self.core.minimumSize())
        self.pulse_animation.setEndValue(self.core.minimumSize())

        self.pulse_animation.setEasingCurve(
            QEasingCurve.InOutSine
        )

    def set_state(self, state):

        if state == "WAITING":

            self.core.setText("J")

            self.core.setStyleSheet("""
                QLabel {
                    background-color: #101820;
                    color: #6fdcff;
                    border: 2px solid #3abff8;
                    border-radius: 75px;
                }
            """)

        elif state == "LISTENING":

            self.core.setText("●")

            self.core.setStyleSheet("""
                QLabel {
                    background-color: #10251f;
                    color: #55e6a5;
                    border: 3px solid #55e6a5;
                    border-radius: 75px;
                }
            """)

        elif state == "PROCESSING":

            self.core.setText("···")

            self.core.setStyleSheet("""
                QLabel {
                    background-color: #211c10;
                    color: #ffd166;
                    border: 3px solid #ffd166;
                    border-radius: 75px;
                }
            """)

        elif state == "SPEAKING":

            self.core.setText("J")

            self.core.setStyleSheet("""
                QLabel {
                    background-color: #19142a;
                    color: #b78cff;
                    border: 3px solid #b78cff;
                    border-radius: 75px;
                }
            """)


# ============================================================
# VENTANA PRINCIPAL
# ============================================================

class JarvisWindow(QMainWindow):

    def __init__(self):

        super().__init__()

        self.setWindowTitle("J.A.R.V.I.S")

        self.resize(1050, 760)

        self.setMinimumSize(850, 650)

        self.thread = None
        self.worker = None

        self.active_threads = []
        self.active_tts_threads = []

        self.voice_thread = None
        self.voice_worker = None

        self.tts_thread = None
        self.tts_worker = None

        self.processing = False

        self.voice_enabled = True

        self.setup_ui()

        self.start_voice()

    # ========================================================
    # UI
    # ========================================================

    def setup_ui(self):

        central = QWidget()

        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)

        main_layout.setContentsMargins(
            35,
            25,
            35,
            25
        )

        main_layout.setSpacing(15)

        # ----------------------------------------------------
        # HEADER
        # ----------------------------------------------------

        header = QHBoxLayout()

        title = QLabel("J.A.R.V.I.S")

        title.setFont(
            QFont("Segoe UI", 24, QFont.Bold)
        )

        title.setStyleSheet("""
            QLabel {
                color: #e8f7ff;
            }
        """)

        subtitle = QLabel("LOCAL INTELLIGENT ASSISTANT")

        subtitle.setFont(
            QFont("Segoe UI", 9)
        )

        subtitle.setStyleSheet("""
            QLabel {
                color: #5d8190;
                letter-spacing: 2px;
            }
        """)

        header_text = QVBoxLayout()

        header_text.setSpacing(2)

        header_text.addWidget(title)
        header_text.addWidget(subtitle)

        header.addLayout(header_text)

        header.addStretch()

        self.voice_status = QLabel("MICRÓFONO ACTIVO")

        self.voice_status.setFont(
            QFont("Segoe UI", 9, QFont.Bold)
        )

        self.voice_status.setStyleSheet("""
            QLabel {
                color: #55e6a5;
                padding: 8px 14px;
                border: 1px solid #245c49;
                border-radius: 8px;
                background-color: #0e1d18;
            }
        """)

        header.addWidget(self.voice_status)

        main_layout.addLayout(header)

        # ----------------------------------------------------
        # CORE
        # ----------------------------------------------------

        core_container = QVBoxLayout()

        core_container.setAlignment(Qt.AlignCenter)

        self.core_widget = CoreWidget()

        core_container.addWidget(
            self.core_widget,
            alignment=Qt.AlignCenter
        )

        self.status_label = QLabel("ESPERANDO")

        self.status_label.setAlignment(
            Qt.AlignCenter
        )

        self.status_label.setFont(
            QFont("Segoe UI", 11, QFont.Bold)
        )

        self.status_label.setStyleSheet("""
            QLabel {
                color: #6fdcff;
                letter-spacing: 3px;
            }
        """)

        core_container.addWidget(
            self.status_label
        )

        main_layout.addLayout(core_container)

        # ----------------------------------------------------
        # CHAT
        # ----------------------------------------------------

        self.chat = QTextEdit()

        self.chat.setReadOnly(True)

        self.chat.setFont(
            QFont("Segoe UI", 11)
        )

        self.chat.setPlaceholderText(
            "La conversación aparecerá aquí..."
        )

        self.chat.setStyleSheet("""
            QTextEdit {
                background-color: #0b1117;
                color: #d9e9ef;
                border: 1px solid #1d303b;
                border-radius: 14px;
                padding: 16px;
                selection-background-color: #1f5c73;
            }
        """)

        main_layout.addWidget(
            self.chat,
            stretch=1
        )

        # ----------------------------------------------------
        # INPUT
        # ----------------------------------------------------

        input_container = QFrame()

        input_container.setStyleSheet("""
            QFrame {
                background-color: #0b1117;
                border: 1px solid #1d303b;
                border-radius: 14px;
            }
        """)

        input_layout = QHBoxLayout(
            input_container
        )

        input_layout.setContentsMargins(
            10,
            8,
            10,
            8
        )

        input_layout.setSpacing(8)

        self.input_box = QLineEdit()

        self.input_box.setPlaceholderText(
            "Escribe un mensaje para J.A.R.V.I.S..."
        )

        self.input_box.setFont(
            QFont("Segoe UI", 11)
        )

        self.input_box.setStyleSheet("""
            QLineEdit {
                background-color: transparent;
                color: #e8f7ff;
                border: none;
                padding: 10px;
            }

            QLineEdit:focus {
                border: none;
            }
        """)

        self.input_box.returnPressed.connect(
            self.send_message
        )

        input_layout.addWidget(
            self.input_box,
            stretch=1
        )

        self.mic_button = QPushButton("MIC")

        self.mic_button.setFixedSize(
            70,
            42
        )

        self.mic_button.clicked.connect(
            self.toggle_voice
        )

        self.mic_button.setStyleSheet("""
            QPushButton {
                background-color: #10202a;
                color: #6fdcff;
                border: 1px solid #2b6c82;
                border-radius: 8px;
                font-weight: bold;
            }

            QPushButton:hover {
                background-color: #16313e;
            }

            QPushButton:pressed {
                background-color: #1c4352;
            }
        """)

        input_layout.addWidget(
            self.mic_button
        )

        self.send_button = QPushButton("ENVIAR")

        self.send_button.setFixedSize(
            85,
            42
        )

        self.send_button.clicked.connect(
            self.send_message
        )

        self.send_button.setStyleSheet("""
            QPushButton {
                background-color: #123447;
                color: #7edfff;
                border: 1px solid #2f7895;
                border-radius: 8px;
                font-weight: bold;
            }

            QPushButton:hover {
                background-color: #17465d;
            }

            QPushButton:pressed {
                background-color: #1d566f;
            }
        """)

        input_layout.addWidget(
            self.send_button
        )

        main_layout.addWidget(
            input_container
        )

        # ----------------------------------------------------
        # FOOTER
        # ----------------------------------------------------

        footer = QHBoxLayout()

        self.engine_label = QLabel(
            "QWEN3 8B  •  WHISPER  •  LOCAL"
        )

        self.engine_label.setFont(
            QFont("Segoe UI", 8)
        )

        self.engine_label.setStyleSheet("""
            QLabel {
                color: #45606b;
            }
        """)

        footer.addWidget(
            self.engine_label
        )

        footer.addStretch()

        self.footer_status = QLabel(
            "SISTEMA OPERATIVO"
        )

        self.footer_status.setFont(
            QFont("Segoe UI", 8)
        )

        self.footer_status.setStyleSheet("""
            QLabel {
                color: #55e6a5;
            }
        """)

        footer.addWidget(
            self.footer_status
        )

        main_layout.addLayout(footer)

        # ----------------------------------------------------
        # ESTILO GLOBAL
        # ----------------------------------------------------

        self.setStyleSheet("""
            QMainWindow {
                background-color: #060b10;
            }

            QWidget {
                background-color: #060b10;
            }

            QScrollBar:vertical {
                background: #080f15;
                width: 8px;
                margin: 2px;
            }

            QScrollBar::handle:vertical {
                background: #24404d;
                border-radius: 4px;
            }

            QScrollBar::handle:vertical:hover {
                background: #326477;
            }

            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        self.append_system_message(
            "J.A.R.V.I.S iniciado. Sistemas locales preparados."
        )

    # ========================================================
    # MENSAJES
    # ========================================================

    def append_user_message(self, text):

        self.chat.append(
            f"""
            <div style="
                margin-top:12px;
                margin-bottom:4px;
                color:#6fdcff;
                font-weight:bold;
            ">
                TÚ
            </div>

            <div style="
                color:#d9e9ef;
                margin-bottom:10px;
            ">
                {self.escape_html(text)}
            </div>
            """
        )

        self.scroll_chat()

    def append_jarvis_message(self, text):

        self.chat.append(
            f"""
            <div style="
                margin-top:12px;
                margin-bottom:4px;
                color:#b78cff;
                font-weight:bold;
            ">
                J.A.R.V.I.S
            </div>

            <div style="
                color:#e3edf2;
                margin-bottom:10px;
            ">
                {self.escape_html(text)}
            </div>
            """
        )

        self.scroll_chat()

    def append_system_message(self, text):

        self.chat.append(
            f"""
            <div style="
                margin-top:8px;
                margin-bottom:8px;
                color:#45606b;
                font-size:9pt;
            ">
                {self.escape_html(text)}
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

        scrollbar.setValue(
            scrollbar.maximum()
        )

    # ========================================================
    # ESTADOS
    # ========================================================

    def set_state(self, state):

        states = {

            "WAITING": (
                "ESPERANDO",
                "#6fdcff"
            ),

            "LISTENING": (
                "ESCUCHANDO",
                "#55e6a5"
            ),

            "PROCESSING": (
                "PROCESANDO",
                "#ffd166"
            ),

            "SPEAKING": (
                "HABLANDO",
                "#b78cff"
            ),
        }

        text, color = states.get(
            state,
            states["WAITING"]
        )

        self.status_label.setText(text)

        self.status_label.setStyleSheet(
            f"""
            QLabel {{
                color: {color};
                letter-spacing: 3px;
            }}
            """
        )

        self.core_widget.set_state(state)

    # ========================================================
    # ENVIAR MENSAJE
    # ========================================================

    def send_message(self):

        message = self.input_box.text().strip()

        if not message:
            return

        # Solo bloqueamos mientras Qwen está procesando.
        #
        # Durante el TTS self.processing será False,
        # por lo que el usuario puede escribir.
        if self.processing:
            return

        self.input_box.clear()

        self.append_user_message(message)

        self.start_processing(message)

    # ========================================================
    # PROCESAMIENTO QWEN
    # ========================================================

    def start_processing(self, message):

        if self.processing:
            return

        self.processing = True

        self.set_state("PROCESSING")

        self.send_button.setEnabled(False)

        thread = QThread()
        worker = JarvisWorker(message)

        worker.moveToThread(thread)

        thread.started.connect(worker.run)

        worker.finished.connect(self.on_response)
        worker.error.connect(self.on_error)

        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)

        thread.finished.connect(worker.deleteLater)

        # Guardamos la referencia hasta que termine.
        self.active_threads.append(thread)

        def cleanup():
            if thread in self.active_threads:
                self.active_threads.remove(thread)

            thread.deleteLater()

        thread.finished.connect(cleanup)

        thread.start()

    @Slot(str)
    @Slot(str)
    def on_response(self, answer):

        # Qwen ya ha terminado.
        # Por tanto, podemos escribir otro mensaje
        # mientras JARVIS está hablando.

        self.processing = False
        self.send_button.setEnabled(True)

        if answer:

            self.append_jarvis_message(answer)

            self.set_state("SPEAKING")

            self.start_tts(answer)

        else:

            self.finish_processing()

    @Slot(str)
    def on_error(self, error):

        self.processing = False

        self.send_button.setEnabled(True)

        self.append_system_message(
            f"Error: {error}"
        )

        self.footer_status.setText(
            "ERROR"
        )

        self.footer_status.setStyleSheet("""
            QLabel {
                color: #ff6b6b;
            }
        """)

        self.finish_processing()

    # ========================================================
    # TTS
    # ========================================================

    def start_tts(self, text):

        thread = QThread()
        worker = TTSWorker(text)

        worker.moveToThread(thread)

        thread.started.connect(worker.run)

        worker.finished.connect(self.on_tts_finished)
        worker.error.connect(self.on_tts_error)

        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)

        thread.finished.connect(worker.deleteLater)

        self.active_tts_threads.append(thread)

        def cleanup():
            if thread in self.active_tts_threads:
                self.active_tts_threads.remove(thread)

            thread.deleteLater()

        thread.finished.connect(cleanup)

        thread.start()

    @Slot()
    def on_tts_finished(self):

        self.finish_processing()

        if self.tts_thread is not None:

            self.tts_thread.quit()

    @Slot(str)
    def on_tts_error(self, error):

        self.append_system_message(
            f"Error de voz: {error}"
        )

        if self.tts_thread is not None:

            self.tts_thread.quit()

        self.finish_processing()

    # ========================================================
    # FINALIZAR
    # ========================================================

    def finish_processing(self):

        self.processing = False

        self.send_button.setEnabled(True)

        self.set_state("WAITING")

        self.footer_status.setText(
            "SISTEMA OPERATIVO"
        )

        self.footer_status.setStyleSheet("""
            QLabel {
                color: #55e6a5;
            }
        """)

    # ========================================================
    # VOZ
    # ========================================================

    def start_voice(self):

        if self.voice_thread is not None:

            if self.voice_thread.isRunning():
                return

        self.voice_enabled = True

        self.voice_status.setText(
            "MICRÓFONO ACTIVO"
        )

        self.voice_status.setStyleSheet("""
            QLabel {
                color: #55e6a5;
                padding: 8px 14px;
                border: 1px solid #245c49;
                border-radius: 8px;
                background-color: #0e1d18;
            }
        """)

        self.mic_button.setText("MIC ON")

        self.voice_thread = QThread()

        self.voice_worker = VoiceWorker()

        self.voice_worker.moveToThread(
            self.voice_thread
        )

        self.voice_thread.started.connect(
            self.voice_worker.run
        )

        self.voice_worker.wake_detected.connect(
            self.on_wake_detected
        )

        self.voice_worker.listening_started.connect(
            self.on_listening_started
        )

        self.voice_worker.command_detected.connect(
            self.on_voice_command
        )

        self.voice_worker.processing_started.connect(
            self.on_voice_processing
        )

        self.voice_worker.error.connect(
            self.on_voice_error
        )

        self.voice_thread.finished.connect(
            self.voice_worker.deleteLater
        )

        self.voice_thread.finished.connect(
            self.voice_thread.deleteLater
        )

        self.voice_thread.start()

    def stop_voice(self):

        self.voice_enabled = False

        if self.voice_worker is not None:

            self.voice_worker.stop()

        if self.voice_thread is not None:

            if self.voice_thread.isRunning():

                self.voice_thread.quit()

                self.voice_thread.wait(2000)

        self.voice_worker = None
        self.voice_thread = None

        self.voice_status.setText(
            "MICRÓFONO DESACTIVADO"
        )

        self.voice_status.setStyleSheet("""
            QLabel {
                color: #697c84;
                padding: 8px 14px;
                border: 1px solid #29383e;
                border-radius: 8px;
                background-color: #0b1115;
            }
        """)

        self.mic_button.setText("MIC OFF")

    # ========================================================
    # EVENTOS DE VOZ
    # ========================================================

    @Slot(float)
    def on_wake_detected(self, score):

        self.set_state("LISTENING")

        self.footer_status.setText(
            "PALABRA CLAVE DETECTADA"
        )

    @Slot()
    def on_listening_started(self):

        self.set_state("LISTENING")

        self.footer_status.setText(
            "ESCUCHANDO MICRÓFONO"
        )

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

        self.append_system_message(
            f"Error de micrófono: {error}"
        )

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

        # Detener micrófono
        self.stop_voice()
    
        # Esperar a los workers de Qwen
        for thread in self.active_threads:
        
            if thread.isRunning():
                thread.quit()
                thread.wait(2000)
    
        # Esperar a los workers de TTS
        for thread in self.active_tts_threads:
        
            if thread.isRunning():
                thread.quit()
                thread.wait(2000)
    
        event.accept()


# ============================================================
# MAIN
# ============================================================

def main():

    app = QApplication(sys.argv)

    app.setApplicationName(
        "J.A.R.V.I.S"
    )

    window = JarvisWindow()

    window.show()

    sys.exit(
        app.exec()
    )


if __name__ == "__main__":
    main()