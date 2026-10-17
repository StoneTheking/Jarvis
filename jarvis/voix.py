"""Synthèse vocale : voix Microsoft Edge (gratuite) ou ElevenLabs (très expressive),
avec repli sur pyttsx3 hors ligne."""

import asyncio
import json
import os
import re
import tempfile
import time
import urllib.request


class Voix:
    def __init__(self, config: dict, interface, muet: bool = False):
        reglages = config["voix"]
        self.moteur = reglages.get("moteur", "edge")
        self.voix = reglages["voix_edge"]
        self.vitesse = reglages["vitesse"]
        self.hauteur = reglages.get("hauteur", "+0Hz")
        self.intonations = reglages.get("intonations", True)
        self.eleven = reglages.get("elevenlabs", {})
        self.interface = interface
        self.muet = muet
        self._moteur_hors_ligne = None
        self.apres_parler = lambda: None  # branché sur le micro pour qu'il ne s'entende pas
        if not muet:
            import pygame

            pygame.mixer.init()

    def dire(self, texte: str) -> None:
        texte = texte.strip()
        sans_balises = re.sub(r"\s*\[[a-z ]+\]\s*", " ", texte).strip()  # [laughs], [whispers]...
        if not sans_balises:
            return
        print(f"🤖 Jarvis : {sans_balises}")
        self.interface.etat("parle", sans_balises)
        if self.muet:
            return
        fd, chemin = tempfile.mkstemp(suffix=".mp3")
        os.close(fd)
        try:
            if self.moteur == "elevenlabs":
                try:
                    self._generer_elevenlabs(texte, chemin)
                except Exception as e:  # quota épuisé, pas de clé...
                    print(f"   (ElevenLabs indisponible : {e} — voix Edge utilisée)")
                    self._generer_edge(sans_balises, chemin)
            else:
                self._generer_edge(sans_balises, chemin)
            self._jouer(chemin)
        except Exception as e:  # pas d'internet, voix inconnue...
            print(f"   (voix en ligne indisponible : {e} — voix hors ligne utilisée)")
            self._dire_hors_ligne(sans_balises)
        finally:
            os.remove(chemin)
            self.apres_parler()

    def _generer_edge(self, texte: str, chemin: str) -> None:
        import edge_tts

        if not self.intonations:
            asyncio.run(edge_tts.Communicate(texte, self.voix, rate=self.vitesse, pitch=self.hauteur).save(chemin))
            return

        # Chaque phrase reçoit sa propre mélodie selon son émotion, puis on recolle le tout.
        phrases = [p for p in re.split(r"(?<=[.!?…])\s+", texte) if p.strip()]

        async def generer(phrase: str) -> bytes:
            vitesse, hauteur, volume = _melodie(phrase)
            communication = edge_tts.Communicate(
                phrase, self.voix,
                rate=_ajouter(self.vitesse, vitesse, "%"),
                pitch=_ajouter(self.hauteur, hauteur, "Hz"),
                volume=f"{volume:+d}%",
            )
            morceaux = []
            async for bloc in communication.stream():
                if bloc["type"] == "audio":
                    morceaux.append(bloc["data"])
            return b"".join(morceaux)

        async def tout_generer() -> list[bytes]:
            return await asyncio.gather(*(generer(p) for p in phrases))

        with open(chemin, "wb") as f:
            for audio in asyncio.run(tout_generer()):
                f.write(audio)

    def _generer_elevenlabs(self, texte: str, chemin: str) -> None:
        cle = os.environ.get("ELEVENLABS_API_KEY")
        if not cle:
            raise RuntimeError("ELEVENLABS_API_KEY manquante dans le fichier .env")
        url = (f"https://api.elevenlabs.io/v1/text-to-speech/{self.eleven.get('voix', 'JBFqnCBsd6RMkjVDRZzb')}"
               "?output_format=mp3_44100_128")
        corps = json.dumps({
            "text": texte,
            "model_id": self.eleven.get("modele", "eleven_v3"),
        }).encode()
        requete = urllib.request.Request(url, data=corps, method="POST", headers={
            "xi-api-key": cle, "Content-Type": "application/json", "Accept": "audio/mpeg"})
        with urllib.request.urlopen(requete, timeout=20) as reponse, open(chemin, "wb") as f:
            f.write(reponse.read())

    def _jouer(self, chemin: str) -> None:
        import pygame

        pygame.mixer.music.load(chemin)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(0.05)
        pygame.mixer.music.unload()

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


def _melodie(phrase: str) -> tuple[int, int, int]:
    """(vitesse %, hauteur Hz, volume %) à ajouter selon le ton de la phrase."""
    fin = phrase.rstrip(" »\"'")
    if fin.endswith("!"):
        return 6, 9, 8  # enthousiasme : plus vif, plus haut, plus fort
    if fin.endswith("?"):
        return 2, 5, 0  # question : la voix monte
    if fin.endswith(("…", "...")):
        return -10, -4, -5  # hésitation, confidence : plus lent et plus grave
    if re.match(r"^(oh|ah|hmm|hum|eh bien|bon|tiens)\b", phrase, re.I):
        return -4, 3, 0
    return 0, 0, 0


def _ajouter(base: str, delta: int, unite: str) -> str:
    valeur = int(re.sub(r"[^\d+-]", "", base) or 0) + delta
    return f"{valeur:+d}{unite}"
