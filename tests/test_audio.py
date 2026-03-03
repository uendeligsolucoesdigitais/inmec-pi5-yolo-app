# Em qualquer parte da sua aplicação:
from core.audio_player import AudioPlayer

# Callback opcional para o rodapé (ex.: statusBar do seu QMainWindow)
def show_status(msg, ms):
    # Exemplo: self.statusBar().showMessage(msg, ms)
    print(f"[STATUS] {msg} ({ms} ms)")

player = AudioPlayer(mp3_dir="mp3", status_callback=show_status, status_duration_ms=3000)

# Reproduz em uma thread, sem travar a UI
player.playmp3("sucesso")        # aceita com ou sem “.mp3”, ex.: "sucesso" ou "sucesso.mp3"
player.playmp3("alerta.mp3")
