# 🤖 Jarvis — ton assistant vocal perso

Tu dis **« Jarvis, ouvre-moi Discord »**, il ouvre Discord.
Tu dis **« Jarvis, envoie un message à Charles sur Discord, dis-lui que je l'aime bien »**, il écrit « Je t'aime bien ! » à Charles.
Tu peux aussi juste discuter avec lui, lui demander la météo, l'heure, de monter le son, de mettre pause...

Le cerveau, c'est **Claude** (l'IA d'Anthropic), via ton abonnement Claude. Tout le reste (micro, voix, actions) tourne sur ton PC.

## Ce qu'il sait faire

| Tu dis... | Jarvis... |
|---|---|
| « Jarvis, ouvre Spotify » | ouvre l'appli (toute appli du menu Démarrer marche) |
| « Jarvis, ferme Steam » | ferme l'appli |
| « Jarvis, envoie à Charles sur Discord que j'arrive dans 10 minutes » | te demande confirmation, puis envoie le message |
| « Jarvis, mets YouTube » / « cherche des recettes de crêpes sur YouTube » | ouvre le site / la recherche |
| « Jarvis, quel temps fait-il à Bordeaux demain ? » | cherche sur internet et te répond |
| « Jarvis, monte le son » / « mets pause » / « musique suivante » | contrôle le volume et les médias |
| « Jarvis, quelle heure est-il ? » | te répond |
| « Jarvis » (tout seul) | répond « Oui ? » et attend ta demande |

Après chaque réponse, Jarvis **continue d'écouter 8 secondes** : tu peux enchaîner sans redire son prénom. Dis « merci » ou « c'est tout » pour terminer.

## Installation (Windows)

1. Installe **Python 3.11 ou plus récent** depuis https://www.python.org/downloads/ et **coche « Add Python to PATH »** pendant l'installation.
2. Télécharge ce dossier (bouton vert *Code* → *Download ZIP*) et dézippe-le.
3. Double-clique sur **`installer.bat`**.
4. **Connecte ton abonnement Claude** (à faire une seule fois) :
   - ouvre **PowerShell** et colle : `irm https://claude.ai/install.ps1 | iex` (ça installe Claude Code) ;
   - ferme puis rouvre PowerShell, tape `claude`, et connecte-toi avec ton compte Claude (Pro ou Max) ;
   - une fois connecté, tape `/exit`. C'est tout, Jarvis réutilisera cette connexion.
5. Double-clique sur **`lancer_jarvis.bat`**. Jarvis dit « Jarvis en ligne » : c'est parti !

> 💡 Pour tester sans micro : `lancer_jarvis.bat --texte` (tu écris au clavier au lieu de parler).
> Mauvais micro utilisé ? `lancer_jarvis.bat --micros` liste tes micros ; mets le bon numéro dans `config.toml` → `index_micro`.

Sous macOS / Linux : `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`, installe Claude Code (`curl -fsSL https://claude.ai/install.sh | bash`), connecte-toi avec `claude`, puis lance `python -m jarvis`. (Sur Mac, il faut autoriser le Terminal dans *Accessibilité* pour l'envoi de messages Discord.)

### Abonnement ou clé API ?

Par défaut, Jarvis utilise **ton abonnement Claude** via Claude Code (`fournisseur = "abonnement"` dans `config.toml`) :

- ✅ rien à payer en plus ;
- ⚠️ ça consomme les mêmes quotas que quand tu utilises Claude Code ;
- ⚠️ c'est un peu plus lent : environ 3 secondes par réponse (10 s pour la toute première), et jusqu'à 30-40 s quand il cherche sur internet. Mettre `modele = "claude-haiku-5-5"` accélère.

Si un jour tu veux plus de rapidité, tu peux passer en `fournisseur = "api"` avec une clé API (https://console.anthropic.com/settings/keys) collée dans le fichier `.env` (copie `.env.example`). C'est facturé à l'usage, moins de 0,1 centime par demande avec Haiku.

## Personnaliser — `config.toml`

Ouvre `config.toml` avec le Bloc-notes, tout est commenté :

- **`[discord.contacts]`** : associe un prénom au pseudo Discord exact. Ex. `charles = "charles_du_33"`. Sans ça, Jarvis tape le prénom tel quel dans la recherche Discord.
- **`[applications]`** et **`[sites]`** : ajoute tes jeux, applis et sites préférés.
- **`modele`** : `claude-opus-5-5` (le plus intelligent) ou `claude-haiku-5-5` (plus rapide, consomme moins de quota, largement suffisant pour des commandes).
- **`voix_edge`** : change la voix de Jarvis (plusieurs voix françaises dispo).
- **`nom_utilisateur`** : comment Jarvis t'appelle (« Monsieur » par défaut 😎).
- **`mode_reveil`** : voir ci-dessous.

## Combien ça coûte ?

Avec ton abonnement Claude : **rien de plus**. La reconnaissance vocale (Google) et la voix (Microsoft Edge) sont gratuites aussi.

## Bon à savoir

- **Envoi de messages Discord** : Jarvis ouvre Discord, fait `Ctrl+K`, tape le nom du contact, puis colle le message, exactement comme tu le ferais à la main. Ne touche ni à la souris ni au clavier pendant ces 5 secondes. Par sécurité, il te relit le message et attend ton « oui » avant d'envoyer (désactivable : `confirmer_avant_envoi = false`).
  Jarvis n'utilise volontairement **pas** de « selfbot » (un programme qui se connecte à ton compte avec ton jeton) : Discord l'interdit et peut bannir le compte.
- **Vie privée** : en mode `google` (par défaut), tout ce que capte le micro part à la reconnaissance vocale de Google pour détecter « Jarvis ». Si ça te gêne, mets `mode_reveil = "hors_ligne"` et installe `pip install openwakeword` : la détection se fait alors sur ton PC, mais il faut dire **« Hey Jarvis »**.
- Seules les phrases qui contiennent « Jarvis », et ce que tu dis juste après, sont envoyées à Claude.

## Comment c'est fait

```
micro ──► reconnaissance vocale ──► « Jarvis » détecté ?
                                          │ oui
                                          ▼
                       Claude (cerveau) ◄──► actions sur le PC
                                          │      (ouvrir une appli, Discord, volume...)
                                          ▼
                                   voix de Jarvis
```

| Fichier | Rôle |
|---|---|
| `jarvis/__main__.py` | la boucle principale (écouter → comprendre → répondre) |
| `jarvis/ecoute.py` | micro, reconnaissance vocale, détection du prénom |
| `jarvis/reveil.py` | détection « Hey Jarvis » hors ligne (optionnelle) |
| `jarvis/cerveau_abonnement.py` | la discussion avec Claude via ton abonnement (Claude Code) |
| `jarvis/cerveau.py` | la discussion avec Claude via une clé API |
| `jarvis/actions.py` | les actions possibles (ajoute les tiennes ici !) |
| `jarvis/voix.py` | la voix |

**Ajouter une action** : dans `jarvis/actions.py`, décris-la dans la liste `OUTILS`, puis écris une méthode du même nom dans la classe `Actions`. Claude saura l'utiliser tout seul.

Inspiré de projets open source comme [JarvisAi](https://github.com/PanPenek/JarvisAi), [llm-guy/jarvis](https://github.com/llm-guy/jarvis) et [openWakeWord](https://github.com/dscripka/openWakeWord).
