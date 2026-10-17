"""Détection hors ligne de « Hey Jarvis » avec openWakeWord (optionnel).

Avantage : rien ne part sur internet tant que tu n'as pas dit « Hey Jarvis ».
Inconvénient : il faut dire « Hey Jarvis » et pas juste « Jarvis ».
"""

import numpy as np

TAUX = 16000
BLOC = 1280  # 80 ms d'audio, la taille conseillée par openWakeWord


class ReveilHorsLigne:
    def __init__(self, config: dict, seuil: float = 0.5):
        import openwakeword
        import pyaudio
        from openwakeword.model import Model

        openwakeword.utils.download_models(["hey_jarvis"])
        self.modele = Model(wakeword_models=["hey_jarvis"], inference_framework="onnx")
        self.seuil = seuil
        self.pyaudio = pyaudio
        index = config["ecoute"]["index_micro"]
        self.index_micro = None if index < 0 else index

    def attendre(self) -> None:
        """Bloque jusqu'à ce que « Hey Jarvis » soit entendu."""
        audio = self.pyaudio.PyAudio()
        flux = audio.open(format=self.pyaudio.paInt16, channels=1, rate=TAUX, input=True,
                          frames_per_buffer=BLOC, input_device_index=self.index_micro)
        try:
            while True:
                trame = np.frombuffer(flux.read(BLOC, exception_on_overflow=False), dtype=np.int16)
                scores = self.modele.predict(trame)
                if max(scores.values()) >= self.seuil:
                    self.modele.reset()
                    return
        finally:
            flux.stop_stream()
            flux.close()
            audio.terminate()
