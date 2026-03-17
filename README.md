# whisper-hotkey

Push-to-talk STT local sur macOS. Maintiens **Shift droit (⇧)** → parle → relâche → le texte s'insère au curseur, n'importe où (Claude Code, Cursor, navigateur, etc.).

- 100% local, aucune donnée envoyée
- Modèle `whisper-large-v3-turbo` via MLX (optimisé Apple Silicon)
- Démarre automatiquement à l'ouverture de session

---

## Prérequis

- Mac Apple Silicon (M1/M2/M3/M4)
- Homebrew installé
- `mlx-whisper` installé : `brew install python && pip3 install mlx-whisper --break-system-packages`
- `cliclick` installé : `brew install cliclick`

---

## Installation

```bash
git clone https://github.com/Assilbeg/whisper-hotkey
cd whisper-hotkey
./setup.sh
```

Le setup installe les dépendances et télécharge le modèle Whisper (~470MB, une seule fois).

---

## Permissions macOS (obligatoires)

Trois permissions à accorder dans **System Settings → Privacy & Security** :

### 1. Accessibility (pour coller le texte)
→ Privacy & Security → **Accessibility** → `+`

Navigue vers :
```
/opt/homebrew/Cellar/python@3.14/3.14.3_1/Frameworks/Python.framework/Versions/3.14/Resources/Python.app
```

### 2. Surveillance des entrées / Input Monitoring (pour détecter la touche ⇧)
→ Privacy & Security → **Surveillance des entrées** → `+`

Même chemin que ci-dessus.

### 3. cliclick — Accessibility (pour envoyer le Cmd+V)
→ Privacy & Security → **Accessibility** → `+`

```
/opt/homebrew/bin/cliclick
```

> **Astuce** : dans le dialog Finder, appuie `Cmd+Shift+G` et colle le chemin directement.

---

## Lancement automatique au démarrage

```bash
# Installe le LaunchAgent (démarre à chaque login)
cp com.ashu.whisper-hotkey.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.ashu.whisper-hotkey.plist
```

---

## Utilisation

| Action | Résultat |
|--------|----------|
| Maintiens ⇧ droit | Enregistrement démarre (son Tink) |
| Relâche ⇧ droit | Transcription → texte collé au curseur (son Pop) |

Les logs sont disponibles dans `/tmp/whisper-hotkey.log`.

---

## Commandes utiles

```bash
# Voir les logs en direct
tail -f /tmp/whisper-hotkey.log

# Redémarrer le daemon
launchctl unload ~/Library/LaunchAgents/com.ashu.whisper-hotkey.plist
launchctl load ~/Library/LaunchAgents/com.ashu.whisper-hotkey.plist

# Arrêter complètement
launchctl unload ~/Library/LaunchAgents/com.ashu.whisper-hotkey.plist
```

---

## Dépannage

**Plus de son / la touche ne répond plus**
→ Le process pynput a perdu la détection. Vérifier que Python.app est bien dans **Surveillance des entrées**, puis relancer le daemon.

**Le texte ne se colle pas (juste "v" qui apparaît)**
→ Vérifier que `cliclick` est bien dans **Accessibility**.

**Première transcription lente**
→ Normal, le modèle se charge en mémoire au démarrage (~8 secondes). Les suivantes sont rapides.
