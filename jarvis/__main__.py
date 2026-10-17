"""Point d'entrée : `python -m jarvis` (voix) ou `python -m jarvis --texte` (clavier)."""

import argparse
import re

from .actions import Actions
from .cerveau import Cerveau
from .config import charger_config
from .ecoute import Clavier, DetecteurPrenom, Oreille, lister_micros
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
    voix = Voix(config, muet=args.muet)
    oreille = Clavier() if args.texte else Oreille(config)
    actions = Actions(config, voix, oreille)
    if config["cerveau"].get("fournisseur", "api") == "abonnement":
        from .cerveau_abonnement import CerveauAbonnement

        cerveau = CerveauAbonnement(config, actions)
    else:
        cerveau = Cerveau(config, actions)
    detecteur = DetecteurPrenom(config)
    reveil = None
    if not args.texte and config["ecoute"].get("mode_reveil") == "hors_ligne":
        from .reveil import ReveilHorsLigne

        reveil = ReveilHorsLigne(config)

    prenom = config["general"]["mot_de_reveil"].capitalize()
    if args.texte:
        print("⌨️  Mode texte : écris directement ta demande (Ctrl+C pour quitter).")
    elif reveil:
        print(f"👂 Dis « Hey {prenom} » pour me parler (Ctrl+C pour quitter).")
    else:
        print(f"👂 Dis « {prenom}, ... » pour me parler (Ctrl+C pour quitter).")
    voix.dire(f"{prenom} en ligne. À votre service, {config['general']['nom_utilisateur']}.")

    try:
        while True:
            commande = attendre_commande(oreille, voix, detecteur, reveil, args.texte)
            if commande:
                converser(commande, cerveau, oreille, voix, detecteur, config)
    except KeyboardInterrupt:
        print("\n👋 À bientôt !")


def attendre_commande(oreille, voix, detecteur, reveil, mode_texte: bool) -> str | None:
    if mode_texte:
        return oreille.ecouter()
    if reveil:
        reveil.attendre()
        voix.dire("Oui ?")
        return oreille.ecouter(attente_max=6)

    phrase = oreille.ecouter()
    if not phrase:
        return None
    commande = detecteur.extraire(phrase)
    if commande == "":  # on a juste dit « Jarvis »
        voix.dire("Oui ?")
        return oreille.ecouter(attente_max=6)
    return commande


def converser(commande: str, cerveau, oreille, voix, detecteur, config) -> None:
    """Répond, puis continue d'écouter quelques secondes pour enchaîner sans redire « Jarvis »."""
    while commande:
        if FIN.match(commande.strip(" .!")):
            voix.dire("Très bien.")
            return
        try:
            voix.dire(cerveau.repondre(commande) or "C'est fait.")
        except Exception as e:
            voix.dire(message_erreur(e))
            return

        suite = oreille.ecouter(attente_max=config["general"]["secondes_de_suivi"])
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
