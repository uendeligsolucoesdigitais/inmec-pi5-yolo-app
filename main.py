import sys
from PySide6.QtWidgets import QApplication
from core.initializer import SystemInitializer
from splashscreen import SplashScreen

def main():
    sistema = SystemInitializer()
    sistema.iniciar_sistema()

    app = QApplication(sys.argv)
    splash = SplashScreen()
    splash.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
