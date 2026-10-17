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

## Savoir si Jarvis t'écoute

Une petite **bulle** reste en bas de l'écran (déplaçable à la souris, clic droit → *Quitter Jarvis*) :

| Couleur | Signification |
|---|---|
| ⚪ gris | en veille : dis « Jarvis, … » |
| 🔵 bleu qui pulse | **il t'écoute**, parle maintenant |
| 🟠 orange | il réfléchit (la bulle affiche ce qu'il a compris) |
| 🟣 violet | il agit (ouvre une appli, envoie un message…) |
| 🟢 vert | il parle |

Et deux petits bips : **montant** = « je t'écoute », **descendant** = « c'est noté ».
Si Jarvis a mal compris, la bulle te montre ce qu'il a entendu : pratique pour repérer le problème.

**Il comprend mal ?**
- Jarvis utilise **Whisper**, qui tourne sur ton PC. Au premier lancement, il télécharge environ 500 Mo. Pour encore plus de précision : `modele_whisper = "medium"` (plus lent).
- Whisper n'existe pas encore pour **Python 3.15**. Si l'installation affiche « Whisper n'est pas encore disponible », Jarvis utilise Google, qui se trompe plus souvent. Pour avoir Whisper, installe aussi **Python 3.13** (https://www.python.org/downloads/, garde ton 3.15), puis relance `installer.bat` : il choisira tout seul la bonne version.
- Parle normalement, sans faire de pause entre « Jarvis » et ta demande.
- S'il réagit aux bruits de fond : `sensibilite_micro = 1.5`. S'il ne t'entend pas : `0.7`.
- Mauvais micro ? `lancer_jarvis.bat --micros`, puis mets le bon numéro dans `index_micro`.

## La voix

Par défaut : **Vivienne**, une voix gratuite de Microsoft. Jarvis écrit ses réponses de façon vivante (exclamations, pauses, interjections), et la voix change de mélodie à chaque phrase (`intonations = true`) : elle monte sur un « ! », remonte sur un « ? » et ralentit sur un « … ».

**Pour une voix vraiment humaine** (rires, chuchotements, enthousiasme…), passe à **ElevenLabs** :
1. Crée un compte gratuit sur https://elevenlabs.io (environ 10 000 caractères par mois offerts, soit à peu près 100 à 200 réponses).
2. *Profil → API Keys* → crée une clé, puis colle-la dans le fichier `.env` : `ELEVENLABS_API_KEY=...` (copie `.env.example` en `.env` s'il n'existe pas).
3. Dans `config.toml`, section `[voix]` : `moteur = "elevenlabs"`.
4. Optionnel : choisis une voix française qui te plaît dans la *Voice Library* d'ElevenLabs, copie son ID dans `[voix.elevenlabs]` → `voix`.

Avec le modèle `eleven_v3`, Jarvis glisse lui-même des émotions dans ses phrases ([laughs], [whispers], [excited]…). Si le quota gratuit est épuisé, il repasse tout seul sur Vivienne.

## Continuer à utiliser ton PC pendant que Jarvis agit

Jarvis tourne en fond : tu peux jouer ou travailler pendant qu'il t'écoute et réfléchit. Le seul moment où il « emprunte » ton PC, c'est pour **envoyer un message Discord** :

- **Méthode `clavier`** (par défaut) : il tape le message dans ton appli Discord, depuis **ton compte**, puis te rend la fenêtre que tu utilisais. Ça prend environ 3 secondes, pendant lesquelles il vaut mieux ne pas taper au clavier.
- **Méthode `bot`** : **100 % en arrière-plan**, rien ne bouge à l'écran. Mais le message est envoyé par un bot (par exemple « Jarvis de Pierre ») et pas par ton compte. Pour l'installer :
  1. Va sur https://discord.com/developers/applications → *New Application* → nomme-la (par ex. « Jarvis »).
  2. Onglet *Bot* → *Reset Token* → copie le jeton dans `.env` : `DISCORD_BOT_TOKEN=...`.
  3. Onglet *OAuth2 → URL Generator* : coche `bot`, puis la permission *Send Messages*. Ouvre le lien généré et invite le bot sur un serveur où sont aussi tes amis.
  4. Dans Discord : *Paramètres → Avancés → Mode développeur*. Fais un clic droit sur ton ami → *Copier l'identifiant*, puis colle-le dans `config.toml` → `[discord.ids_bot]`, par ex. `charles = "123456789012345678"`.
  5. Mets `methode = "bot"` dans `[discord]`.

  Jarvis n'utilise volontairement **pas** de « selfbot » (un programme qui se connecte à ton compte avec ton jeton) : Discord l'interdit et peut bannir le compte.

## Personnaliser — `config.toml`

Ouvre `config.toml` avec le Bloc-notes, tout est commenté :

- **`[discord.contacts]`** : associe un prénom au pseudo Discord exact. Ex. `charles = "charles_du_33"`. Sans ça, Jarvis tape le prénom tel quel dans la recherche Discord.
- **`[applications]`** et **`[sites]`** : ajoute tes jeux, applis et sites préférés.
- **`modele`** : `claude-opus-5-5` (le plus intelligent) ou `claude-haiku-5-5` (plus rapide, consomme moins de quota, largement suffisant pour des commandes).
- **`nom_utilisateur`** : comment Jarvis t'appelle (« Monsieur » par défaut 😎).
- **`confirmer_avant_envoi`** : Jarvis te relit chaque message Discord et attend ton « oui » avant de l'envoyer. Mets `false` pour désactiver.

## Combien ça coûte ?

Avec ton abonnement Claude : **rien de plus**. Whisper (reconnaissance vocale) tourne sur ton PC et la voix Vivienne est gratuite. ElevenLabs est gratuit jusqu'à environ 10 000 caractères par mois.

## Vie privée

Whisper tourne sur ton PC : ce que capte le micro **ne part pas sur internet**. Seules tes demandes à Jarvis (les phrases avec « Jarvis » et ce que tu dis juste après) sont envoyées à Claude. Le texte de ses réponses est envoyé à Microsoft ou à ElevenLabs pour fabriquer la voix.

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
| `jarvis/ecoute.py` | micro, reconnaissance vocale (Whisper / Google), détection du prénom |
| `jarvis/reveil.py` | détection « Hey Jarvis » hors ligne (optionnelle) |
| `jarvis/cerveau_abonnement.py` | la discussion avec Claude via ton abonnement (Claude Code) |
| `jarvis/cerveau.py` | la discussion avec Claude via une clé API |
| `jarvis/actions.py` | les actions possibles (ajoute les tiennes ici !) |
| `jarvis/voix.py` | la voix (Edge avec intonations, ou ElevenLabs) |
| `jarvis/interface.py` | la bulle d'état et les bips |

**Ajouter une action** : dans `jarvis/actions.py`, décris-la dans la liste `OUTILS`, puis écris une méthode du même nom dans la classe `Actions`. Claude saura l'utiliser tout seul.

Inspiré de projets open source comme [JarvisAi](https://github.com/PanPenek/JarvisAi), [llm-guy/jarvis](https://github.com/llm-guy/jarvis) et [openWakeWord](https://github.com/dscripka/openWakeWord).
