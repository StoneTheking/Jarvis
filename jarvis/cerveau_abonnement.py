"""Cerveau alternatif : passe par Claude Code (installé et connecté sur le PC),
donc par l'abonnement Claude, au lieu d'une clé API."""

import asyncio
import json
import time

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    CLINotFoundError,
    ResultMessage,
    ToolUseBlock,
    create_sdk_mcp_server,
    query,
    tool,
)

from .actions import OUTILS, Actions
from .cerveau import consignes
from .config import RACINE


class CerveauAbonnement:
    def __init__(self, config: dict, actions: Actions):
        self.actions = actions
        c = config["cerveau"]
        self.oubli = config["general"]["minutes_avant_oubli"] * 60
        self.session = None
        self.dernier_echange = 0.0

        outils = [self._outil(o) for o in OUTILS]
        noms_mcp = [f"mcp__jarvis__{o['name']}" for o in OUTILS]
        integres = ["WebSearch"] if c.get("recherche_web") else []
        self.options = ClaudeAgentOptions(
            system_prompt=consignes(config),
            model=_alias(c["modele"]),
            effort=c["effort"],
            tools=integres,  # aucun outil de Claude Code (fichiers, terminal...) à part la recherche web
            mcp_servers={"jarvis": create_sdk_mcp_server("jarvis", tools=outils)},
            allowed_tools=noms_mcp + integres,
            permission_mode="dontAsk",
            setting_sources=[],  # ignore les réglages Claude Code de l'utilisateur
            cwd=RACINE,
            max_turns=10,
        )

    def _outil(self, definition: dict):
        nom = definition["name"]

        async def executer(entree: dict) -> dict:
            try:
                # Les actions bloquent (clavier, micro) : on les sort de la boucle asyncio.
                texte = await asyncio.to_thread(self.actions.executer, nom, entree)
                return {"content": [{"type": "text", "text": texte}]}
            except Exception as e:
                return {"content": [{"type": "text", "text": f"Erreur : {e}"}], "is_error": True}

        return tool(nom, definition["description"], definition["input_schema"])(executer)

    def repondre(self, demande: str) -> str:
        if time.time() - self.dernier_echange > self.oubli:
            self.session = None
        self.dernier_echange = time.time()
        try:
            return asyncio.run(self._repondre(demande))
        except CLINotFoundError:
            return "Je ne trouve pas Claude Code sur cet ordinateur. Installez-le, puis connectez-vous avec la commande claude."

    async def _repondre(self, demande: str) -> str:
        self.options.resume = self.session  # reprend la conversation en cours
        reponse = ""
        async for message in query(prompt=demande, options=self.options):
            if isinstance(message, AssistantMessage):
                for bloc in message.content:
                    if isinstance(bloc, ToolUseBlock):
                        nom = bloc.name.removeprefix("mcp__jarvis__")
                        print(f"   ⚙️  {nom} {json.dumps(bloc.input, ensure_ascii=False)}")
            elif isinstance(message, ResultMessage):
                self.session = message.session_id
                if message.is_error:
                    print(f"⚠️  Claude Code : {message.result or message.errors}")
                    return "Je n'arrive pas à joindre Claude. Vérifiez que vous êtes connecté avec la commande claude."
                reponse = message.result or ""
        return reponse


def _alias(modele: str) -> str:
    """Claude Code comprend « opus », « sonnet », « haiku » (dernière version de chaque)."""
    return next((f for f in ("opus", "sonnet", "haiku", "fable") if f in modele), modele)
