"""Le cerveau de Jarvis : Claude via une clé API, avec les actions de actions.py comme outils."""

import json
import platform
import time

import anthropic

from .actions import OUTILS, RECHERCHE_WEB, Actions

CONSIGNES = """Tu es Jarvis, l'assistant vocal personnel de {nom}, inspiré du Jarvis d'Iron Man : \
efficace, poli, avec une pointe d'humour britannique. Tu tournes sur son ordinateur ({systeme}).

Tout ce que tu écris est lu à voix haute :
- Réponds en français, en une à trois phrases courtes, comme à l'oral.
- Jamais de markdown, de listes, d'émojis, d'URL ni de code. Ne cite pas tes sources.
- Quand tu as fait une action, confirme-la en quelques mots (« C'est fait, Discord est ouvert. »).

Ce que tu entends vient d'une reconnaissance vocale : il peut y avoir des fautes \
(« discorde » pour « Discord »). Devine l'intention la plus probable plutôt que de faire répéter.

Utilise les outils pour agir sur l'ordinateur. Si une demande dépasse tes outils, dis-le simplement.

Applications connues : {applis}.
Sites connus : {sites}.
Contacts Discord connus : {contacts}."""


class Cerveau:
    def __init__(self, config: dict, actions: Actions):
        self.client = anthropic.Anthropic()
        self.actions = actions
        c = config["cerveau"]
        self.modele = c["modele"]
        self.effort = c["effort"]
        self.oubli = config["general"]["minutes_avant_oubli"] * 60
        self.outils = OUTILS + ([RECHERCHE_WEB] if c.get("recherche_web") else [])
        self.consignes = consignes(config)
        self.messages: list = []
        self.dernier_echange = 0.0

    def repondre(self, demande: str) -> str:
        if time.time() - self.dernier_echange > self.oubli:
            self.messages = []
        self.dernier_echange = time.time()
        self.messages.append({"role": "user", "content": demande})

        for _ in range(10):  # au plus 10 allers-retours d'outils par demande
            reponse = self._appeler_claude()

            if reponse.stop_reason == "refusal":
                self.messages = []
                return "Désolé, je ne peux pas vous aider avec ça."

            self.messages.append({"role": "assistant", "content": reponse.content})

            if reponse.stop_reason == "pause_turn":  # recherche web encore en cours
                continue
            if reponse.stop_reason != "tool_use":
                return _texte(reponse)

            resultats = []
            for bloc in reponse.content:
                if bloc.type != "tool_use":
                    continue
                print(f"   ⚙️  {bloc.name} {json.dumps(bloc.input, ensure_ascii=False)}")
                try:
                    resultat = {"content": self.actions.executer(bloc.name, bloc.input)}
                except Exception as e:
                    resultat = {"content": f"Erreur : {e}", "is_error": True}
                resultats.append({"type": "tool_result", "tool_use_id": bloc.id, **resultat})
            self.messages.append({"role": "user", "content": resultats})

        return "Je me suis un peu perdu en route, pouvez-vous reformuler ?"

    def _appeler_claude(self):
        parametres = dict(
            model=self.modele,
            max_tokens=16000,
            system=self.consignes,
            tools=self.outils,
            messages=self.messages,
            output_config={"effort": self.effort},
            cache_control={"type": "ephemeral"},
        )
        # Si le modèle refuse une demande, on la relance automatiquement sur un
        # autre modèle (Haiku n'a pas cette option).
        if not self.modele.startswith("claude-haiku"):
            parametres.update(betas=["server-side-fallback-2026-07-01"], fallbacks="default")
        return self.client.beta.messages.create(**parametres)


def consignes(config: dict) -> str:
    return CONSIGNES.format(
        nom=config["general"]["nom_utilisateur"],
        systeme=platform.system(),
        applis=", ".join(config["applications"]) or "aucune",
        sites=", ".join(config["sites"]) or "aucun",
        contacts=", ".join(config["discord"]["contacts"]) or "aucun",
    )


def _texte(reponse) -> str:
    return " ".join(b.text for b in reponse.content if b.type == "text").strip()
