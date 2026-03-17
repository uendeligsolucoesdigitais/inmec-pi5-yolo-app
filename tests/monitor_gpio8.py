#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

try:
    import gpiod
except Exception as e:
    print(f"Erro ao importar gpiod: {e}")
    sys.exit(1)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Monitor GPIO 8 - Raspberry Pi 5")
        self.setMinimumSize(430, 260)

        # Ajuste aqui se necessário:
        self.chip_name = "gpiochip0"
        self.gpio_line = 8  # BCM GPIO 8

        self.request = None

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(14)
        self.central_widget.setLayout(self.layout)

        self.title_label = QLabel("Status da IO08 / GPIO 8")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setFont(QFont("Arial", 18, QFont.Weight.Bold))

        self.status_label = QLabel("INICIALIZANDO...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setFont(QFont("Arial", 22, QFont.Weight.Bold))
        self.status_label.setMinimumHeight(70)

        self.value_label = QLabel("Valor lógico: --")
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.value_label.setFont(QFont("Arial", 14))

        self.info_label = QLabel(
            f"Chip: {self.chip_name} | Linha BCM: {self.gpio_line}\n"
            "Atualização automática a cada 200 ms"
        )
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.info_label.setFont(QFont("Arial", 11))

        self.refresh_button = QPushButton("Atualizar agora")
        self.refresh_button.setMinimumHeight(42)
        self.refresh_button.clicked.connect(self.update_gpio_status)

        self.layout.addWidget(self.title_label)
        self.layout.addWidget(self.status_label)
        self.layout.addWidget(self.value_label)
        self.layout.addWidget(self.info_label)
        self.layout.addWidget(self.refresh_button)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_gpio_status)

        self.apply_unknown_style()
        self.setup_gpio()
        self.timer.start(200)

    def setup_gpio(self):
        try:
            # API compatível com libgpiod v2
            config = {
                self.gpio_line: gpiod.LineSettings(
                    direction=gpiod.line.Direction.INPUT
                )
            }

            self.request = gpiod.request_lines(
                self.chip_name,
                consumer="monitor-gpio8-pyqt6",
                config=config,
            )

            self.update_gpio_status()

        except Exception as e:
            self.request = None
            self.status_label.setText("ERRO")
            self.value_label.setText("Valor lógico: indisponível")
            self.apply_error_style()

            QMessageBox.critical(
                self,
                "Erro ao inicializar GPIO",
                "Não foi possível abrir a linha GPIO.\n\n"
                f"Chip: {self.chip_name}\n"
                f"Linha BCM: {self.gpio_line}\n\n"
                f"Erro: {e}\n\n"
                "Verifique:\n"
                "- se o pacote gpiod está instalado\n"
                "- se a linha BCM está correta\n"
                "- se o usuário tem permissão de acesso ao gpiochip\n"
                "- se a GPIO não está em uso por outro processo"
            )

    def read_gpio_value(self):
        if self.request is None:
            raise RuntimeError("GPIO não inicializada.")

        value = self.request.get_value(self.gpio_line)

        # compatível com enum Value.ACTIVE / INACTIVE
        if hasattr(value, "name"):
            return 1 if value.name == "ACTIVE" else 0

        # fallback caso venha inteiro
        return 1 if int(value) else 0

    def update_gpio_status(self):
        try:
            value = self.read_gpio_value()

            if value == 1:
                self.status_label.setText("NÍVEL ALTO")
                self.value_label.setText("Valor lógico: 1")
                self.apply_high_style()
            else:
                self.status_label.setText("NÍVEL BAIXO")
                self.value_label.setText("Valor lógico: 0")
                self.apply_low_style()

        except Exception as e:
            self.status_label.setText("ERRO DE LEITURA")
            self.value_label.setText(f"Valor lógico: erro ({e})")
            self.apply_error_style()

    def apply_high_style(self):
        self.central_widget.setStyleSheet("""
            QWidget {
                background-color: #0f172a;
                color: white;
            }
            QLabel {
                color: white;
            }
            QPushButton {
                background-color: #1d4ed8;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
        """)
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: #15803d;
                color: white;
                border-radius: 12px;
                padding: 14px;
            }
        """)

    def apply_low_style(self):
        self.central_widget.setStyleSheet("""
            QWidget {
                background-color: #111827;
                color: white;
            }
            QLabel {
                color: white;
            }
            QPushButton {
                background-color: #1d4ed8;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
        """)
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: #b91c1c;
                color: white;
                border-radius: 12px;
                padding: 14px;
            }
        """)

    def apply_error_style(self):
        self.central_widget.setStyleSheet("""
            QWidget {
                background-color: #1f2937;
                color: white;
            }
            QLabel {
                color: white;
            }
            QPushButton {
                background-color: #374151;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4b5563;
            }
        """)
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: #92400e;
                color: white;
                border-radius: 12px;
                padding: 14px;
            }
        """)

    def apply_unknown_style(self):
        self.central_widget.setStyleSheet("""
            QWidget {
                background-color: #0b1220;
                color: white;
            }
            QLabel {
                color: white;
            }
            QPushButton {
                background-color: #1d4ed8;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
        """)
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: #475569;
                color: white;
                border-radius: 12px;
                padding: 14px;
            }
        """)

    def closeEvent(self, event):
        try:
            self.timer.stop()
            if self.request is not None:
                self.request.release()
        except Exception:
            pass
        event.accept()


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()