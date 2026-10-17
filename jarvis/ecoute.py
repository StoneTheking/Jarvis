"""Écoute du micro, reconnaissance vocale et détection du prénom « Jarvis »."""

import re


# Phrases que Whisper « invente » parfois sur du bruit ou du silence.
HALLUCINATIONS = re.compile(
    r"sous-titr|amara|merci d'avoir regard|abonnez-vous|n'oubliez pas de|radio-canada|"
    r"merci de votre attention|à bientôt pour une nouvelle vidéo",
    re.I,
)


class Oreille:
    """Transforme ce que tu dis en texte, avec Whisper (sur ton PC) ou Google (en ligne)."""

    def __init__(self, config: dict):
        import speech_recognition as sr

        self.sr = sr
        e = config["ecoute"]
        self.langue = e["langue"]
        self.moteur = e.get("moteur", "whisper")
        index = e["index_micro"]
        self.micro = Micro(sr, None if index < 0 else index)
        self.reco = sr.Recognizer()
        self.reco.dynamic_energy_threshold = True
        self.reco.pause_threshold = 1.0  # silence qui marque la fin d'une phrase (secondes)
        self.reco.non_speaking_duration = 0.4
        if self.moteur == "whisper":
            try:
                self._charger_whisper(e.get("modele_whisper", "small"), config)
            except ImportError:
                print("⚠️  Whisper n'est pas installé (voir le README) : j'utilise la reconnaissance de Google.")
                self.moteur = "google"
        print("🎙️  Calibrage du micro (reste silencieux 1 seconde)...")
        with self.micro as source:
            self.reco.adjust_for_ambient_noise(source, duration=1)
        self.reco.energy_threshold *= e.get("sensibilite_micro", 1.0)

    def _charger_whisper(self, modele: str, config: dict) -> None:
        from faster_whisper import WhisperModel

        print(f"🧠 Chargement de la reconnaissance vocale Whisper « {modele} » "
              "(la première fois, téléchargement de quelques centaines de Mo)...")
        self.whisper = WhisperModel(modele, device="cpu", compute_type="int8")
        # Donner à Whisper le vocabulaire attendu l'aide énormément (noms propres surtout).
        noms = list(config["applications"])[:12] + list(config["discord"]["contacts"])
        prenom = config["general"]["mot_de_reveil"].capitalize()
        self.vocabulaire = f"{prenom}. " + ", ".join(noms) + "."

    def ecouter(self, attente_max: float | None = None) -> str | None:
        """Renvoie la phrase entendue, ou None (silence / incompréhensible)."""
        with self.micro as source:
            try:
                audio = self.reco.listen(source, timeout=attente_max, phrase_time_limit=15)
            except self.sr.WaitTimeoutError:
                return None
        texte = self._whisper(audio) if self.moteur == "whisper" else self._google(audio)
        if texte:
            print(f"🗣️  Toi : {texte}")
        return texte or None

    def _whisper(self, audio) -> str:
        import numpy as np

        echantillons = np.frombuffer(audio.get_raw_data(convert_rate=16000, convert_width=2), np.int16)
        if len(echantillons) < 16000 * 0.4:  # moins de 0,4 s : un bruit, pas une phrase
            return ""
        segments, _ = self.whisper.transcribe(
            echantillons.astype(np.float32) / 32768,
            language=self.langue.split("-")[0],
            initial_prompt=self.vocabulaire,
            beam_size=5,
            vad_filter=True,
            condition_on_previous_text=False,
        )
        morceaux = [s.text for s in segments if s.no_speech_prob < 0.6 and s.avg_logprob > -1.0]
        texte = " ".join(morceaux).strip()
        return "" if HALLUCINATIONS.search(texte) else texte

    def _google(self, audio) -> str:
        try:
            return self.reco.recognize_google(audio, language=self.langue)
        except self.sr.UnknownValueError:
            return ""
        except self.sr.RequestError as e:
            print(f"⚠️  Reconnaissance vocale indisponible : {e}")
            return ""


class Clavier:
    """Remplace le micro par le clavier (mode --texte, pratique pour tester)."""

    def ecouter(self, attente_max: float | None = None) -> str | None:
        try:
            texte = input("🗣️  Toi : ").strip()
        except EOFError:
            raise KeyboardInterrupt
        return texte or None


class DetecteurPrenom:
    def __init__(self, config: dict):
        g = config["general"]
        mots = [g["mot_de_reveil"], *g.get("variantes_mot_de_reveil", [])]
        # Les plus longs d'abord pour que « jarvisse » ne soit pas coupé en « jarvis » + « se ».
        motif = "|".join(re.escape(m.lower()) for m in sorted(mots, key=len, reverse=True))
        self.regex = re.compile(rf"\b(?:{motif})\b[\s,.!?:;]*", re.IGNORECASE)

    def extraire(self, phrase: str) -> str | None:
        """Si la phrase contient le prénom, renvoie la commande sans le prénom
        (chaîne vide si on a juste dit « Jarvis »). Sinon renvoie None."""
        if not self.regex.search(phrase):
            return None
        commande = self.regex.sub(" ", phrase, count=1)
        return re.sub(r"\s+", " ", commande).strip(" ,.!?:;")


def Micro(sr, index: int | None):
    """Micro pour speech_recognition, basé sur sounddevice (pas besoin de PyAudio,
    qui ne s'installe pas sur les versions récentes de Python)."""

    class _Flux:
        def __init__(self, flux):
            self.flux = flux

        def read(self, n: int) -> bytes:
            donnees, _ = self.flux.read(n)
            return bytes(donnees)

    class _Micro(sr.AudioSource):
        def __init__(self):
            self.SAMPLE_RATE = 16000
            self.SAMPLE_WIDTH = 2
            self.CHUNK = 1024
            self.stream = None

        def __enter__(self):
            import sounddevice as sd

            flux = sd.RawInputStream(samplerate=self.SAMPLE_RATE, blocksize=self.CHUNK,
                                     device=index, channels=1, dtype="int16")
            flux.start()
            self.stream = _Flux(flux)
            return self

        def __exit__(self, *_):
            self.stream.flux.stop()
            self.stream.flux.close()
            self.stream = None

    return _Micro()


def lister_micros() -> None:
    import sounddevice as sd

    for i, appareil in enumerate(sd.query_devices()):
        if appareil["max_input_channels"] > 0:
            print(f"[{i}] {appareil['name']}")
