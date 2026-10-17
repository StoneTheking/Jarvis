"""Synthèse vocale : voix Microsoft Edge (edge-tts), repli sur pyttsx3 hors ligne."""

import asyncio
import os
import tempfile
import time


class Voix:
    def __init__(self, config: dict, muet: bool = False):
        self.voix = config["voix"]["voix_edge"]
        self.vitesse = config["voix"]["vitesse"]
        self.muet = muet
        self._moteur_hors_ligne = None
        if not muet:
            import pygame

            pygame.mixer.init()

    def dire(self, texte: str) -> None:
        texte = texte.strip()
        if not texte:
            return
        print(f"🤖 Jarvis : {texte}")
        if self.muet:
            return
        try:
            self._dire_edge(texte)
        except Exception as e:  # pas d'internet, voix inconnue...
            print(f"   (voix Edge indisponible : {e} — voix hors ligne utilisée)")
            self._dire_hors_ligne(texte)

    def _dire_edge(self, texte: str) -> None:
        import edge_tts
        import pygame

        fd, chemin = tempfile.mkstemp(suffix=".mp3")
        os.close(fd)
        try:
            asyncio.run(edge_tts.Communicate(texte, self.voix, rate=self.vitesse).save(chemin))
            pygame.mixer.music.load(chemin)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                time.sleep(0.05)
            pygame.mixer.music.unload()
        finally:
            os.remove(chemin)

    def _dire_hors_ligne(self, texte: str) -> None:
        import pyttsx3

        if self._moteur_hors_ligne is None:
            self._moteur_hors_ligne = pyttsx3.init()
            for v in self._moteur_hors_ligne.getProperty("voices"):
                if "fr" in (v.id + v.name).lower():
                    self._moteur_hors_ligne.setProperty("voice", v.id)
                    break
        self._moteur_hors_ligne.say(texte)
        self._moteur_hors_ligne.runAndWait()
