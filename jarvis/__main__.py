"""Point d'entrée : `python -m jarvis` (voix) ou `python -m jarvis --texte` (clavier)."""

import argparse
import re

from .actions import Actions
from .cerveau import Cerveau
from .config import charger_config
from .ecoute import Clavier, DetecteurPrenom, Oreille, lister_micros
from .interface import Interface
from .voix import Voix

FIN = re.compile(r"^(stop|au revoir|c'est tout|merci c'est tout|merci|rien|laisse tomber|non merci)$", re.I)


def main() -> None:
    parser = argparse.ArgumentParser(description="Jarvis, ton assistant vocal.")
    parser.add_argument("--texte", action="store_true", help="parler à Jarvis au clavier au lieu du micro")
    parser.add_argument("--muet", action="store_true", help="Jarvis écrit ses réponses sans les dire")
    parser.add_argument("--micros", action="store_true", help="lister les micros disponibles")
    args = parser.parse_args()

    if args.micros:
        lister_micros()
        return

    config = charger_config()
    prenom = config["general"]["mot_de_reveil"].capitalize()
    hors_ligne = not args.texte and config["ecoute"].get("mode_reveil") == "hors_ligne"
    appel = f"Hey {prenom}" if hors_ligne else prenom
    i = config.get("interface", {})
    interface = Interface(
        bulle=i.get("bulle", True) and not args.texte,
        sons=i.get("sons", True) and not args.texte,
        astuce_veille=f"Dis « {appel} » pour me parler",
    )
    interface.lancer(lambda: demarrer(config, args, interface, prenom, appel, hors_ligne))


def demarrer(config, args, interface, prenom, appel, hors_ligne) -> None:
    interface.etat("reflexion", "Démarrage…")
    voix = Voix(config, interface, muet=args.muet)
    oreille = Clavier() if args.texte else Oreille(config)
    actions = Actions(config, voix, oreille, interface)
    if config["cerveau"].get("fournisseur", "api") == "abonnement":
        from .cerveau_abonnement import CerveauAbonnement

        cerveau = CerveauAbonnement(config, actions)
    else:
        cerveau = Cerveau(config, actions)
    detecteur = DetecteurPrenom(config)
    reveil = None
    if hors_ligne:
        from .reveil import ReveilHorsLigne

        reveil = ReveilHorsLigne(config)

    if args.texte:
        print("⌨️  Mode texte : écris directement ta demande (Ctrl+C pour quitter).")
    else:
        print(f"👂 Dis « {appel}, ... » pour me parler (Ctrl+C ou clic droit sur la bulle pour quitter).")
    voix.dire(f"{prenom} en ligne ! À votre service, {config['general']['nom_utilisateur']}.")

    try:
        while True:
            interface.etat("veille")
            commande = attendre_commande(oreille, voix, detecteur, reveil, interface, args.texte)
            if commande:
                converser(commande, cerveau, oreille, voix, detecteur, interface, config)
    except KeyboardInterrupt:
        print("\n👋 À bientôt !")


def attendre_commande(oreille, voix, detecteur, reveil, interface, mode_texte: bool) -> str | None:
    if mode_texte:
        return oreille.ecouter()
    if reveil:
        reveil.attendre()
        return ecouter_commande(oreille, interface)

    phrase = oreille.ecouter()
    if not phrase:
        return None
    commande = detecteur.extraire(phrase)
    if commande is None:
        interface.etat("veille", f"Entendu sans « Jarvis » : {phrase}")
        return None
    if commande == "":  # on a juste dit « Jarvis »
        return ecouter_commande(oreille, interface)
    interface.bip(montant=False)  # « bien reçu »
    return commande


def ecouter_commande(oreille, interface, attente: float = 6, astuce: str = "Vas-y, je t'écoute") -> str | None:
    interface.bip(montant=True)
    interface.etat("ecoute", astuce)
    texte = oreille.ecouter(attente_max=attente)
    interface.bip(montant=False)
    return texte


def converser(commande: str, cerveau, oreille, voix, detecteur, interface, config) -> None:
    """Répond, puis continue d'écouter quelques secondes pour enchaîner sans redire « Jarvis »."""
    while commande:
        if FIN.match(commande.strip(" .!")):
            voix.dire("Très bien !")
            return
        interface.etat("reflexion", f"« {commande} »")
        try:
            voix.dire(cerveau.repondre(commande) or "C'est fait !")
        except Exception as e:
            interface.etat("erreur", str(e))
            voix.dire(message_erreur(e))
            return

        if not isinstance(oreille, Oreille):  # mode texte : pas de fenêtre de suivi
            return
        suite = ecouter_commande(oreille, interface, config["general"]["secondes_de_suivi"],
                                 "Tu peux enchaîner sans redire mon nom")
        if suite is not None:
            sans_prenom = detecteur.extraire(suite)
            suite = suite if sans_prenom is None else sans_prenom
        commande = suite


def message_erreur(e: Exception) -> str:
    print(f"⚠️  {type(e).__name__} : {e}")
    try:
        import anthropic
    except ImportError:
        return "J'ai rencontré un problème technique."
    if isinstance(e, anthropic.AuthenticationError):
        return "Ma clé d'accès à Claude est invalide. Vérifiez le fichier point env."
    if isinstance(e, anthropic.APIConnectionError):
        return "Je n'arrive pas à me connecter à internet."
    if isinstance(e, anthropic.RateLimitError):
        return "Je suis un peu débordé, réessayez dans une minute."
    return "J'ai rencontré un problème technique."


if __name__ == "__main__":
    main()
