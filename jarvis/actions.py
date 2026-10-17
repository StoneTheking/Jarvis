"""Les actions que Jarvis peut faire sur ton ordinateur (les « outils » donnés à Claude)."""

import datetime
import difflib
import os
import platform
import re
import shutil
import subprocess
import time
import urllib.parse
import webbrowser
from pathlib import Path

SYSTEME = platform.system()  # "Windows", "Darwin" (macOS) ou "Linux"

OUI = re.compile(r"\b(oui|ouais|ouai|vas[- ]y|envoie|ok|okay|d'accord|carrément|confirme|go|yes)\b", re.I)
NON = re.compile(r"\b(non|pas|annule|attends|stop|change)\b", re.I)


def _schema(proprietes: dict, requis: list[str]) -> dict:
    return {
        "type": "object",
        "properties": proprietes,
        "required": requis,
        "additionalProperties": False,
    }


OUTILS = [
    {
        "name": "ouvrir_application",
        "description": "Ouvre une application installée sur l'ordinateur (Discord, Spotify, Steam, Chrome, la calculatrice, un jeu...).",
        "strict": True,
        "input_schema": _schema(
            {"nom": {"type": "string", "description": "Nom de l'application, ex. « discord »."}},
            ["nom"],
        ),
    },
    {
        "name": "fermer_application",
        "description": "Ferme une application en cours d'exécution.",
        "strict": True,
        "input_schema": _schema(
            {"nom": {"type": "string", "description": "Nom de l'application, ex. « spotify »."}},
            ["nom"],
        ),
    },
    {
        "name": "ouvrir_site",
        "description": "Ouvre un site web dans le navigateur, par son nom (« youtube ») ou son adresse.",
        "strict": True,
        "input_schema": _schema(
            {"site": {"type": "string", "description": "Nom connu du site ou URL complète."}},
            ["site"],
        ),
    },
    {
        "name": "rechercher_dans_navigateur",
        "description": "Lance une recherche Google ou YouTube dans le navigateur de l'utilisateur, pour qu'il voie les résultats à l'écran.",
        "strict": True,
        "input_schema": _schema(
            {
                "requete": {"type": "string"},
                "plateforme": {"type": "string", "enum": ["google", "youtube"]},
            },
            ["requete", "plateforme"],
        ),
    },
    {
        "name": "envoyer_message_discord",
        "description": (
            "Envoie un message privé Discord à quelqu'un, depuis le compte Discord de l'utilisateur. "
            "Reformule le message à la première personne comme si l'utilisateur l'écrivait lui-même "
            "(« dis-lui que je l'aime bien » devient « Je t'aime bien ! »)."
        ),
        "strict": True,
        "input_schema": _schema(
            {
                "destinataire": {"type": "string", "description": "Prénom ou surnom du destinataire."},
                "message": {"type": "string", "description": "Texte exact à envoyer."},
            },
            ["destinataire", "message"],
        ),
    },
    {
        "name": "controle_multimedia",
        "description": "Règle le volume de l'ordinateur ou contrôle la musique / vidéo en cours.",
        "strict": True,
        "input_schema": _schema(
            {
                "action": {
                    "type": "string",
                    "enum": ["monter_volume", "baisser_volume", "couper_son", "lecture_pause", "piste_suivante", "piste_precedente"],
                },
                "repetitions": {
                    "type": "integer",
                    "description": "Nombre d'appuis (1 appui ≈ 2 % de volume). Mettre 1 pour les autres actions.",
                },
            },
            ["action", "repetitions"],
        ),
    },
    {
        "name": "date_et_heure",
        "description": "Donne la date et l'heure actuelles.",
        "strict": True,
        "input_schema": _schema({}, []),
    },
]

RECHERCHE_WEB = {"type": "web_search_20260209", "name": "web_search", "max_uses": 3}


LIBELLES = {
    "ouvrir_application": "Ouverture de {nom}",
    "fermer_application": "Fermeture de {nom}",
    "ouvrir_site": "Ouverture de {site}",
    "rechercher_dans_navigateur": "Recherche : {requete}",
    "envoyer_message_discord": "Message Discord pour {destinataire}",
    "controle_multimedia": "Son / musique",
    "date_et_heure": "Coup d'œil à l'horloge",
}


class Actions:
    def __init__(self, config: dict, voix, oreille, interface):
        self.config = config
        self.voix = voix
        self.oreille = oreille
        self.interface = interface

    def executer(self, nom: str, entree: dict) -> str:
        fonction = getattr(self, nom, None)
        if fonction is None or nom.startswith("_"):
            raise ValueError(f"Outil inconnu : {nom}")
        self.interface.etat("action", LIBELLES.get(nom, nom).format(**entree))
        try:
            return fonction(**entree)
        finally:
            self.interface.etat("reflexion")

    # ------------------------------------------------------------------ applis

    def ouvrir_application(self, nom: str) -> str:
        cle = nom.lower().strip()
        applis = self.config["applications"]
        proche = difflib.get_close_matches(cle, list(applis), n=1, cutoff=0.75)
        if proche:
            _lancer(applis[proche[0]])
            return f"{proche[0]} ouvert."

        raccourci = _chercher_raccourci_windows(cle)
        if raccourci:
            os.startfile(raccourci)
            return f"{raccourci.stem} ouvert."

        if _lancer(cle):
            return f"{nom} lancé."
        return f"Je ne trouve pas d'application nommée « {nom} ». L'utilisateur peut l'ajouter dans config.toml, section [applications]."

    def fermer_application(self, nom: str) -> str:
        import psutil

        cle = re.sub(r"[^a-z0-9]", "", nom.lower())
        if len(cle) < 3:
            return "Nom d'application trop court pour la fermer sans risque."
        fermes = set()
        for proc in psutil.process_iter(["name"]):
            nom_proc = (proc.info["name"] or "").lower()
            if cle in re.sub(r"[^a-z0-9]", "", nom_proc):
                try:
                    proc.terminate()
                    fermes.add(proc.info["name"])
                except psutil.Error:
                    pass
        if not fermes:
            return f"Aucune application « {nom} » n'est ouverte."
        return f"Fermé : {', '.join(sorted(fermes))}."

    # ------------------------------------------------------------------- web

    def ouvrir_site(self, site: str) -> str:
        sites = self.config["sites"]
        proche = difflib.get_close_matches(site.lower().strip(), list(sites), n=1, cutoff=0.75)
        if proche:
            url = sites[proche[0]]
        elif "." in site and " " not in site.strip():
            url = site if site.startswith("http") else f"https://{site.strip()}"
        else:
            url = "https://www.google.com/search?btnI=1&q=" + urllib.parse.quote(site)
        webbrowser.open(url)
        return f"Ouvert : {url}"

    def rechercher_dans_navigateur(self, requete: str, plateforme: str) -> str:
        q = urllib.parse.quote(requete)
        if plateforme == "youtube":
            url = f"https://www.youtube.com/results?search_query={q}"
        else:
            url = f"https://www.google.com/search?q={q}"
        webbrowser.open(url)
        return f"Recherche {plateforme} ouverte pour « {requete} »."

    # --------------------------------------------------------------- discord

    def envoyer_message_discord(self, destinataire: str, message: str) -> str:
        reglages = self.config["discord"]
        if reglages.get("confirmer_avant_envoi", True):
            self.voix.dire(f"J'envoie à {destinataire} : « {message} ». C'est bon ?")
            self.interface.bip(montant=True)
            self.interface.etat("ecoute", "Oui pour envoyer, non pour annuler")
            reponse = self.oreille.ecouter(attente_max=7)
            self.interface.bip(montant=False)
            if not reponse or NON.search(reponse) or not OUI.search(reponse):
                return "Envoi annulé : l'utilisateur n'a pas confirmé."
        self.interface.etat("action", f"Message Discord pour {destinataire}")
        if reglages.get("methode", "clavier") == "bot":
            return _discord_par_bot(reglages, destinataire, message)
        return _discord_par_clavier(reglages, destinataire, message)

    # ---------------------------------------------------------------- divers

    def controle_multimedia(self, action: str, repetitions: int) -> str:
        import pyautogui

        touches = {
            "monter_volume": "volumeup",
            "baisser_volume": "volumedown",
            "couper_son": "volumemute",
            "lecture_pause": "playpause",
            "piste_suivante": "nexttrack",
            "piste_precedente": "prevtrack",
        }
        n = max(1, min(int(repetitions), 50)) if action in ("monter_volume", "baisser_volume") else 1
        pyautogui.press(touches[action], presses=n, interval=0.02)
        return "Fait."

    def date_et_heure(self) -> str:
        jours = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
        mois = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
                "août", "septembre", "octobre", "novembre", "décembre"]
        m = datetime.datetime.now()
        return f"{jours[m.weekday()]} {m.day} {mois[m.month - 1]} {m.year}, {m.hour}h{m.minute:02d}"


# ------------------------------------------------------------------ utilitaires


def _lancer(cible: str) -> bool:
    """Lance une appli, un exécutable ou un lien (discord://, spotify:...)."""
    est_lien = bool(re.match(r"^[a-z][a-z0-9+.-]*:", cible, re.I)) and not re.match(r"^[a-z]:\\", cible, re.I)
    if SYSTEME == "Windows":
        if est_lien or Path(cible).exists():
            os.startfile(cible)
        else:
            subprocess.Popen(f'start "" "{cible}"', shell=True)
        return True
    if SYSTEME == "Darwin":
        commande = ["open", cible] if est_lien else ["open", "-a", cible]
        return subprocess.run(commande, capture_output=True).returncode == 0
    if est_lien:
        subprocess.Popen(["xdg-open", cible])
        return True
    executable = shutil.which(cible) or shutil.which(cible.replace(" ", "-"))
    if executable:
        subprocess.Popen([executable], start_new_session=True)
        return True
    return False


def _chercher_raccourci_windows(nom: str) -> Path | None:
    """Cherche l'appli dans le menu Démarrer (presque toutes les applis installées y sont)."""
    if SYSTEME != "Windows":
        return None
    dossiers = [
        Path(os.environ.get("APPDATA", "")) / "Microsoft/Windows/Start Menu/Programs",
        Path(os.environ.get("PROGRAMDATA", "")) / "Microsoft/Windows/Start Menu/Programs",
        Path.home() / "Desktop",
    ]
    raccourcis = {}
    for dossier in dossiers:
        if dossier.is_dir():
            for f in dossier.rglob("*"):
                if f.suffix.lower() in (".lnk", ".url"):
                    raccourcis.setdefault(f.stem.lower(), f)
    for stem, chemin in raccourcis.items():
        if stem == nom:
            return chemin
    proche = difflib.get_close_matches(nom, list(raccourcis), n=1, cutoff=0.6)
    if proche:
        return raccourcis[proche[0]]
    contient = sorted((s for s in raccourcis if nom in s), key=len)
    return raccourcis[contient[0]] if contient else None


def _discord_par_clavier(reglages: dict, destinataire: str, message: str) -> str:
    """Tape le message dans l'appli Discord comme un humain, puis rend la main à la
    fenêtre que tu utilisais (environ 3 secondes d'interruption)."""
    import pyautogui

    pseudo = reglages["contacts"].get(destinataire.lower().strip(), destinataire)
    fenetre_precedente = _fenetre_active()
    if not _activer_fenetre("Discord"):
        _lancer("discord://")
        time.sleep(reglages.get("delai_ouverture", 4))
        _activer_fenetre("Discord")

    ctrl = "command" if SYSTEME == "Darwin" else "ctrl"
    ancien_presse_papier = _lire_presse_papier()
    try:
        pyautogui.hotkey(ctrl, "k")  # recherche rapide de Discord
        time.sleep(0.6)
        _coller(pseudo, ctrl)
        time.sleep(1.2)
        pyautogui.press("enter")
        time.sleep(1.0)
        _coller(message, ctrl)
        time.sleep(0.2)
        pyautogui.press("enter")
        time.sleep(0.2)
    finally:
        _ecrire_presse_papier(ancien_presse_papier)
        if fenetre_precedente is not None:
            try:
                fenetre_precedente.activate()
            except Exception:
                pass
    return f"Message tapé et envoyé dans la conversation Discord « {pseudo} »."


def _discord_par_bot(reglages: dict, destinataire: str, message: str) -> str:
    """Envoie le message en message privé via un bot Discord : rien ne s'affiche à
    l'écran, le clavier n'est pas touché. Le message vient du bot, pas de ton compte."""
    import json
    import urllib.error
    import urllib.request

    jeton = os.environ.get("DISCORD_BOT_TOKEN")
    if not jeton:
        return "Erreur : DISCORD_BOT_TOKEN manquant dans le fichier .env."
    identifiant = reglages.get("ids_bot", {}).get(destinataire.lower().strip())
    if not identifiant:
        return (f"Erreur : pas d'identifiant Discord pour « {destinataire} ». L'utilisateur doit "
                "l'ajouter dans config.toml, section [discord.ids_bot].")

    def appel(chemin: str, donnees: dict) -> dict:
        requete = urllib.request.Request(
            f"https://discord.com/api/v10{chemin}", data=json.dumps(donnees).encode(), method="POST",
            headers={"Authorization": f"Bot {jeton}", "Content-Type": "application/json",
                     "User-Agent": "DiscordBot (https://github.com/stonetheking/jarvis, 1.0)"})
        with urllib.request.urlopen(requete, timeout=10) as reponse:
            return json.load(reponse)

    try:
        salon = appel("/users/@me/channels", {"recipient_id": str(identifiant)})
        appel(f"/channels/{salon['id']}/messages", {"content": message})
    except urllib.error.HTTPError as e:
        return (f"Erreur Discord {e.code} : {e.read().decode(errors='ignore')[:200]}. "
                "Le destinataire doit partager un serveur avec le bot et accepter ses messages privés.")
    return f"Message envoyé à {destinataire} par le bot Discord."


def _fenetre_active():
    if SYSTEME != "Windows":
        return None
    try:
        import pygetwindow

        return pygetwindow.getActiveWindow()
    except Exception:
        return None


def _activer_fenetre(titre: str) -> bool:
    """Met au premier plan la fenêtre dont le titre se termine par `titre`, si elle existe."""
    if SYSTEME != "Windows":
        return False
    try:
        import pygetwindow

        fenetres = [w for w in pygetwindow.getWindowsWithTitle(titre) if w.title.endswith(titre)]
        if not fenetres:
            return False
        if fenetres[0].isMinimized:
            fenetres[0].restore()
        try:
            fenetres[0].activate()
        except Exception:
            # Windows refuse parfois de changer de fenêtre active : un appui sur Alt débloque.
            import pyautogui

            pyautogui.press("alt")
            fenetres[0].activate()
        time.sleep(0.4)
        return True
    except Exception:
        return False


def _coller(texte: str, ctrl: str) -> None:
    """Colle via le presse-papier (pyautogui ne sait pas taper les accents)."""
    import pyautogui

    _ecrire_presse_papier(texte)
    pyautogui.hotkey(ctrl, "v")


def _lire_presse_papier() -> str:
    try:
        import pyperclip

        return pyperclip.paste()
    except Exception:
        return ""


def _ecrire_presse_papier(texte: str) -> None:
    import pyperclip

    pyperclip.copy(texte)
