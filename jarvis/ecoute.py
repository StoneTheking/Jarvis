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
        self.micro = Micro(None if index < 0 else index)
        self.reco = sr.Recognizer()
        self.pause = e.get("pause_fin_de_phrase", 1.6)  # silence qui marque la fin d'une phrase
        self.sensibilite = e.get("sensibilite_micro", 1.0)
        if self.moteur == "whisper":
            try:
                self._charger_whisper(e.get("modele_whisper", "small"), config)
            except ImportError:
                print("⚠️  Whisper n'est pas installé (voir le README) : j'utilise la reconnaissance de Google.")
                self.moteur = "google"
        print("🎙️  Calibrage du micro (reste silencieux 1 seconde)...")
        self.micro.vider()
        niveaux = [_volume(self.micro.lire()) for _ in range(16)]
        self.bruit_de_fond = float(sorted(niveaux)[len(niveaux) // 2])

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
        """Renvoie la phrase entendue, ou None (silence / incompréhensible).
        Si la phrase a l'air coupée en plein milieu, attend la suite et la recolle."""
        texte = ""
        for _ in range(3):
            audio = self._enregistrer(attente_max if not texte else 3.0)
            if audio is None:
                break
            morceau = self._whisper(audio) if self.moteur == "whisper" else self._google(audio)
            texte = f"{texte} {morceau.strip()}".strip()
            if not texte or not _inacheve(texte):
                break
            print(f"   … (j'attends la suite de : « {texte} »)")
        if texte:
            print(f"🗣️  Toi : {texte}")
        return texte or None

    def _enregistrer(self, attente_max: float | None):
        """Enregistre une phrase : démarre quand le volume dépasse nettement le bruit de
        fond, s'arrête après `self.pause` secondes de vrai silence. Le seuil de fin est
        plus bas que celui de début, pour ne pas couper sur une syllabe faible."""
        from collections import deque

        duree_bloc = Micro.BLOC / Micro.TAUX
        avant = deque(maxlen=int(0.6 / duree_bloc))  # garde le début du premier mot
        ecoule = 0.0
        while True:  # 1) attendre que tu parles
            bloc = self.micro.lire()
            niveau = _volume(bloc)
            if niveau > max(self.bruit_de_fond * 3.0, 120) * self.sensibilite:
                break
            # Le bruit de fond évolue doucement (ventilateur, musique...).
            self.bruit_de_fond = 0.97 * self.bruit_de_fond + 0.03 * niveau
            avant.append(bloc)
            ecoule += duree_bloc
            if attente_max is not None and ecoule > attente_max:
                return None

        seuil_fin = max(self.bruit_de_fond * 1.8, 80) * self.sensibilite
        phrase = list(avant) + [bloc]
        silence = parole = 0.0
        while silence < self.pause and parole + silence < 25:  # 2) enregistrer jusqu'au silence
            bloc = self.micro.lire()
            phrase.append(bloc)
            if _volume(bloc) > seuil_fin:
                parole += duree_bloc + silence
                silence = 0.0
            else:
                silence += duree_bloc
        if parole < 0.3:  # un claquement, pas une phrase
            return None
        return self.sr.AudioData(b"".join(phrase), Micro.TAUX, 2)

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


# Mots après lesquels une phrase ne peut pas s'arrêter.
MOTS_DE_LIAISON = {
    "à", "a", "de", "du", "des", "que", "qu", "et", "ou", "mais", "pour", "avec", "sur", "dans",
    "le", "la", "les", "un", "une", "mon", "ma", "mes", "ton", "ta", "son", "sa", "au", "aux",
    "en", "par", "lui", "leur", "dis", "dis-lui", "euh", "heu", "hum", "parce", "comme", "si",
}


def _inacheve(texte: str) -> bool:
    """Devine si la phrase a été coupée au milieu (tu as hésité ou repris ton souffle)."""
    t = texte.lower().strip()
    if t.endswith((",", "...", "…", "-")):
        return True
    t = t.rstrip(" .!?")
    dernier = re.split(r"[\s']+", t)[-1] if t else ""
    if dernier in MOTS_DE_LIAISON:
        return True
    # « envoie un message à Charles » : il manque le contenu du message.
    return bool(re.search(r"(message|écri[st]|dis)\b.*\b(à|a|pour)\s+\w+$", t)) and " que " not in f" {t} "


def _volume(bloc: bytes) -> float:
    import numpy as np

    echantillons = np.frombuffer(bloc, np.int16).astype(np.float32)
    return float(np.sqrt(np.mean(echantillons ** 2))) if len(echantillons) else 0.0


class Micro:
    """Micro ouvert en permanence : le son s'accumule dans une file, donc rien n'est
    perdu pendant que Jarvis transcrit ou réfléchit."""

    TAUX = 16000
    BLOC = 1024  # 64 ms

    def __init__(self, index: int | None):
        import queue

        import sounddevice as sd

        self.file = queue.Queue()
        self.flux = sd.RawInputStream(samplerate=self.TAUX, blocksize=self.BLOC, device=index,
                                      channels=1, dtype="int16", callback=self._recevoir)
        self.flux.start()

    def _recevoir(self, donnees, _blocs, _temps, _statut) -> None:
        self.file.put(bytes(donnees))

    def lire(self) -> bytes:
        return self.file.get()

    def vider(self) -> None:
        """Oublie le son déjà capté (par exemple la voix de Jarvis elle-même)."""
        import queue

        while True:
            try:
                self.file.get_nowait()
            except queue.Empty:
                return


def lister_micros() -> None:
    import sounddevice as sd

    for i, appareil in enumerate(sd.query_devices()):
        if appareil["max_input_channels"] > 0:
            print(f"[{i}] {appareil['name']}")
