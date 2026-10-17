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
        from openwakeword.model import Model

        openwakeword.utils.download_models(["hey_jarvis"])
        self.modele = Model(wakeword_models=["hey_jarvis"], inference_framework="onnx")
        self.seuil = seuil
        index = config["ecoute"]["index_micro"]
        self.index_micro = None if index < 0 else index

    def attendre(self) -> None:
        """Bloque jusqu'à ce que « Hey Jarvis » soit entendu."""
        import sounddevice as sd

        with sd.RawInputStream(samplerate=TAUX, blocksize=BLOC, device=self.index_micro,
                               channels=1, dtype="int16") as flux:
            while True:
                donnees, _ = flux.read(BLOC)
                scores = self.modele.predict(np.frombuffer(donnees, dtype=np.int16))
                if max(scores.values()) >= self.seuil:
                    self.modele.reset()
                    return
