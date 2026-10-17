"""Écoute du micro, reconnaissance vocale et détection du prénom « Jarvis »."""

import re


class Oreille:
    """Transforme ce que tu dis en texte (reconnaissance vocale Google, gratuite)."""

    def __init__(self, config: dict):
        import speech_recognition as sr

        self.sr = sr
        self.langue = config["ecoute"]["langue"]
        index = config["ecoute"]["index_micro"]
        self.micro = Micro(sr, None if index < 0 else index)
        self.reco = sr.Recognizer()
        self.reco.dynamic_energy_threshold = True
        self.reco.pause_threshold = 0.8
        print("🎙️  Calibrage du micro (silence 1 seconde)...")
        with self.micro as source:
            self.reco.adjust_for_ambient_noise(source, duration=1)

    def ecouter(self, attente_max: float | None = None) -> str | None:
        """Renvoie la phrase entendue, ou None (silence / incompréhensible)."""
        with self.micro as source:
            try:
                audio = self.reco.listen(source, timeout=attente_max, phrase_time_limit=20)
            except self.sr.WaitTimeoutError:
                return None
        try:
            texte = self.reco.recognize_google(audio, language=self.langue)
        except self.sr.UnknownValueError:
            return None
        except self.sr.RequestError as e:
            print(f"⚠️  Reconnaissance vocale indisponible : {e}")
            return None
        print(f"🗣️  Toi : {texte}")
        return texte


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
