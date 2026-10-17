"""Détection hors ligne de « Hey Jarvis » avec openWakeWord (optionnel).

Avantage : rien ne part sur internet tant que tu n'as pas dit « Hey Jarvis ».
Inconvénient : il faut dire « Hey Jarvis » et pas juste « Jarvis ».
"""

import numpy as np

TAUX = 16000
BLOC = 1280  # 80 ms d'audio, la taille conseillée par openWakeWord


class ReveilHorsLigne:
    def __init__(self, seuil: float = 0.5):
        import openwakeword
        from openwakeword.model import Model

        openwakeword.utils.download_models(["hey_jarvis"])
        self.modele = Model(wakeword_models=["hey_jarvis"], inference_framework="onnx")
        self.seuil = seuil

    def attendre(self, micro) -> None:
        """Bloque jusqu'à ce que « Hey Jarvis » soit entendu."""
        micro.vider()
        tampon = b""
        while True:
            tampon += micro.lire()
            while len(tampon) >= BLOC * 2:
                trame, tampon = tampon[: BLOC * 2], tampon[BLOC * 2:]
                scores = self.modele.predict(np.frombuffer(trame, dtype=np.int16))
                if max(scores.values()) >= self.seuil:
                    self.modele.reset()
                    return
