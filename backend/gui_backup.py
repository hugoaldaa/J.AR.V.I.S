import sys
import time

from PySide6.QtCore import (
    QObject,
    QThread,
    Signal,
    Slot,
    Qt,
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
)

from brain import ask_jarvis
from voice import wait_for_wake_word, listen_command
from tts import speak


# =========================================================
# WORKER PARA QWEN
# =========================================================

class JarvisWorker(QObject):

    finished = Signal(str)
    error = Signal(str)

    def __init__(self, message):
        super().__init__()
        self.message = message

    @Slot()
    def run(self):

        try:

            answer = ask_jarvis(
                self.message
            )

            if answer is None:
                answer = ""

            self.finished.emit(
                answer
            )

        except Exception as e:

            self.error.emit(
                str(e)
            )


# =========================================================
# WORKER PARA TTS
# =========================================================

class TTSWorker(QObject):

    finished = Signal()
    error = Signal(str)

    def __init__(self, text):
        super().__init__()

        self.text = text

    @Slot()
    def run(self):

        try:

            speak(
                self.text
            )

            self.finished.emit()

        except Exception as e:

            self.error.emit(
                str(e)
            )


# =========================================================
# WORKER PARA VOZ
# =========================================================

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

                # -----------------------------------------
                # ESPERAR WAKE WORD
                # -----------------------------------------

                score = wait_for_wake_word(
                    self._stop_event()
                )

                if not self.running:
                    break

                if score is None:
                    continue

                self.wake_detected.emit(
                    score
                )

                # -----------------------------------------
                # ESCUCHAR ORDEN
                # -----------------------------------------

                self.listening_started.emit()

                command = listen_command(
                    self._stop_event()
                )

                if not self.running:
                    break

                if command:

                    self.command_detected.emit(
                        command
                    )

                else:

                    self.processing_started.emit()


            except Exception as e:

                self.error.emit(
                    str(e)
                )

                time.sleep(1)


    def _stop_event(self):

        class StopEvent:

            def __init__(self, worker):

                self.worker = worker


            def is_set(self):

                return not self.worker.running


        return StopEvent(
            self
        )


    def stop(self):

        self.running = False


# =========================================================
# VENTANA PRINCIPAL
# =========================================================

class JarvisWindow(QMainWindow):

    def __init__(self):

        super().__init__()

        self.setWindowTitle(
            "J.A.R.V.I.S"
        )

        self.resize(
            1000,
            700
        )

        # -----------------------------------------
        # QWEN
        # -----------------------------------------

        self.thread = None
        self.worker = None

        # -----------------------------------------
        # TTS
        # -----------------------------------------

        self.tts_thread = None
        self.tts_worker = None

        # -----------------------------------------
        # VOZ
        # -----------------------------------------

        self.voice_thread = None
        self.voice_worker = None

        self.voice_enabled = False

        # -----------------------------------------
        # ESTADO
        # -----------------------------------------

        self.processing = False

        self.setup_ui()

        self.start_voice()


    # =====================================================
    # UI
    # =====================================================

    def setup_ui(self):

        central = QWidget()

        self.setCentralWidget(
            central
        )

        main_layout = QVBoxLayout(
            central
        )

        main_layout.setContentsMargins(
            30,
            30,
            30,
            30
        )

        main_layout.setSpacing(
            20
        )


        # -----------------------------------------
        # TÍTULO
        # -----------------------------------------

        title = QLabel(
            "J.A.R.V.I.S"
        )

        title.setAlignment(
            Qt.AlignCenter
        )

        title_font = QFont()

        title_font.setPointSize(
            28
        )

        title_font.setBold(
            True
        )

        title.setFont(
            title_font
        )

        main_layout.addWidget(
            title
        )


        # -----------------------------------------
        # ESTADO
        # -----------------------------------------

        self.status = QLabel(
            "ESPERANDO"
        )

        self.status.setAlignment(
            Qt.AlignCenter
        )

        status_font = QFont()

        status_font.setPointSize(
            11
        )

        status_font.setBold(
            True
        )

        self.status.setFont(
            status_font
        )

        main_layout.addWidget(
            self.status
        )


        # -----------------------------------------
        # NÚCLEO
        # -----------------------------------------

        self.core = QLabel(
            "●"
        )

        self.core.setAlignment(
            Qt.AlignCenter
        )

        core_font = QFont()

        core_font.setPointSize(
            90
        )

        self.core.setFont(
            core_font
        )

        main_layout.addWidget(
            self.core
        )


        # -----------------------------------------
        # CHAT
        # -----------------------------------------

        self.chat = QTextEdit()

        self.chat.setReadOnly(
            True
        )

        main_layout.addWidget(
            self.chat,
            1
        )


        # -----------------------------------------
        # INPUT
        # -----------------------------------------

        input_layout = QHBoxLayout()


        self.input = QLineEdit()

        self.input.setPlaceholderText(
            "Escribe una orden..."
        )

        self.input.returnPressed.connect(
            self.send_message
        )

        input_layout.addWidget(
            self.input,
            1
        )


        # -----------------------------------------
        # BOTÓN ENVIAR
        # -----------------------------------------

        self.send_button = QPushButton(
            "Enviar"
        )

        self.send_button.clicked.connect(
            self.send_message
        )

        input_layout.addWidget(
            self.send_button
        )


        # -----------------------------------------
        # BOTÓN MICRÓFONO
        # -----------------------------------------

        self.mic_button = QPushButton(
            "Micrófono"
        )

        self.mic_button.clicked.connect(
            self.toggle_voice
        )

        input_layout.addWidget(
            self.mic_button
        )


        main_layout.addLayout(
            input_layout
        )


        # -----------------------------------------
        # ESTILO
        # -----------------------------------------

        self.setStyleSheet("""

            QMainWindow {
                background-color: #0b0f14;
            }

            QLabel {
                color: #e6edf3;
            }

            QLineEdit {
                background-color: #161b22;
                color: #e6edf3;

                border: 1px solid #30363d;
                border-radius: 10px;

                padding: 12px;

                font-size: 15px;
            }

            QTextEdit {
                background-color: #0d1117;
                color: #e6edf3;

                border: 1px solid #30363d;
                border-radius: 12px;

                padding: 15px;

                font-size: 15px;
            }

            QPushButton {
                background-color: #21262d;
                color: #e6edf3;

                border: 1px solid #30363d;
                border-radius: 10px;

                padding: 10px 18px;

                font-size: 14px;
            }

            QPushButton:hover {
                background-color: #30363d;
            }

            QPushButton:pressed {
                background-color: #161b22;
            }

            QPushButton:disabled {
                color: #6e7681;
                background-color: #161b22;
            }

        """)


    # =====================================================
    # TEXTO
    # =====================================================

    def send_message(self):
        message = self.input_box.text().strip()
    
        if not message:
            return
    
        if self.processing:
            return
    
        self.input_box.clear()
    
        self.chat.append(f"<b>TÚ:</b> {message}")
    
        self.processing = True
        self.status_label.setText("PROCESANDO")
    
        self.start_processing(message)


    # =====================================================
    # PROCESAR QWEN
    # =====================================================

    def start_processing(self, message):

        if self.processing:
            return

        self.processing = True

        self.status.setText(
            "PROCESANDO"
        )

        self.input.setEnabled(
            False
        )

        self.send_button.setEnabled(
            False
        )

        # -----------------------------------------
        # THREAD
        # -----------------------------------------

        self.thread = QThread()

        self.worker = JarvisWorker(
            message
        )

        self.worker.moveToThread(
            self.thread
        )

        self.thread.started.connect(
            self.worker.run
        )

        self.worker.finished.connect(
            self.on_response
        )

        self.worker.error.connect(
            self.on_error
        )

        self.worker.finished.connect(
            self.thread.quit
        )

        self.worker.error.connect(
            self.thread.quit
        )

        self.thread.finished.connect(
            self.worker.deleteLater
        )

        self.thread.finished.connect(
            self.thread.deleteLater
        )

        self.thread.start()


    # =====================================================
    # RESPUESTA DE QWEN
    # =====================================================

    @Slot(str)
    def on_response(self, answer):
        if answer:
            self.chat.append(f"<b>JARVIS:</b> {answer}")

            # El procesamiento de Qwen ya ha terminado.
            self.processing = False

            self.status_label.setText("HABLANDO")
            self.start_tts(answer)
        else:
            self.finish_processing()


    # =====================================================
    # INICIAR TTS
    # =====================================================

    def start_tts(self, text):

        self.tts_thread = QThread()

        self.tts_worker = TTSWorker(
            text
        )

        self.tts_worker.moveToThread(
            self.tts_thread
        )

        self.tts_thread.started.connect(
            self.tts_worker.run
        )

        self.tts_worker.finished.connect(
            self.on_tts_finished
        )

        self.tts_worker.error.connect(
            self.on_tts_error
        )

        self.tts_worker.finished.connect(
            self.tts_thread.quit
        )

        self.tts_worker.error.connect(
            self.tts_thread.quit
        )

        self.tts_thread.finished.connect(
            self.tts_worker.deleteLater
        )

        self.tts_thread.finished.connect(
            self.tts_thread.deleteLater
        )

        self.tts_thread.start()


    # =====================================================
    # TTS TERMINADO
    # =====================================================

    @Slot()
    def on_tts_finished(self):

        self.finish_processing()


    # =====================================================
    # ERROR TTS
    # =====================================================

    @Slot(str)
    def on_tts_error(self, error):

        self.chat.append(
            f"<b>Error de voz:</b> {error}"
        )

        self.finish_processing()


    # =====================================================
    # ERROR QWEN
    # =====================================================

    @Slot(str)
    def on_error(self, error):

        self.chat.append(
            f"<b>Error:</b> {error}"
        )

        self.finish_processing()


    # =====================================================
    # TERMINAR PROCESAMIENTO
    # =====================================================

    def finish_processing(self):

        self.processing = False

        self.status.setText(
            "ESPERANDO"
        )

        self.input.setEnabled(
            True
        )

        self.send_button.setEnabled(
            True
        )

        self.input.setFocus()


    # =====================================================
    # VOZ
    # =====================================================

    def start_voice(self):

        # Evitar crear dos workers
        if self.voice_enabled:
            return

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
            self.on_listening
        )

        self.voice_worker.command_detected.connect(
            self.on_voice_command
        )

        self.voice_worker.error.connect(
            self.on_voice_error
        )

        self.voice_thread.start()

        self.voice_enabled = True

        self.mic_button.setText(
            "Micrófono ON"
        )


    # =====================================================
    # WAKE WORD
    # =====================================================

    @Slot(float)
    def on_wake_detected(self, score):

        self.status.setText(
            "ESCUCHANDO"
        )

        self.core.setText(
            "●"
        )


    # =====================================================
    # ESCUCHANDO
    # =====================================================

    @Slot()
    def on_listening(self):

        self.status.setText(
            "ESCUCHANDO"
        )


    # =====================================================
    # ORDEN POR VOZ
    # =====================================================

    @Slot(str)
    def on_voice_command(self, command):

        if self.processing:
            return

        self.chat.append(
            f"<b>Tú:</b> {command}"
        )

        self.start_processing(
            command
        )


    # =====================================================
    # ERROR VOZ
    # =====================================================

    @Slot(str)
    def on_voice_error(self, error):

        self.chat.append(
            f"<b>Error de voz:</b> {error}"
        )

        self.status.setText(
            "ESPERANDO"
        )


    # =====================================================
    # BOTÓN MICRÓFONO
    # =====================================================

    def toggle_voice(self):

        if self.voice_enabled:

            if self.voice_worker:

                self.voice_worker.stop()

            self.voice_enabled = False

            self.mic_button.setText(
                "Micrófono OFF"
            )

            self.status.setText(
                "MICRÓFONO OFF"
            )

        else:

            self.start_voice()


    # =====================================================
    # CERRAR
    # =====================================================

    def closeEvent(self, event):

        # -----------------------------------------
        # VOZ
        # -----------------------------------------

        if self.voice_worker:

            self.voice_worker.stop()

        if self.voice_thread:

            self.voice_thread.quit()

            self.voice_thread.wait(
                2000
            )

        # -----------------------------------------
        # QWEN
        # -----------------------------------------

        if self.thread:

            self.thread.quit()

            self.thread.wait(
                2000
            )

        # -----------------------------------------
        # TTS
        # -----------------------------------------

        if self.tts_thread:

            self.tts_thread.quit()

            self.tts_thread.wait(
                2000
            )

        event.accept()


# =========================================================
# MAIN
# =========================================================

def main():

    app = QApplication(
        sys.argv
    )

    window = JarvisWindow()

    window.show()

    sys.exit(
        app.exec()
    )


if __name__ == "__main__":

    main()