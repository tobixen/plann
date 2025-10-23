# Intégration Ollama avec plann

Cette extension permet d'ajouter des événements et des tâches à **plann** en utilisant le **langage naturel**, grâce à [Ollama](https://ollama.ai/).

## 🚀 Fonctionnalités

- ✅ **Langage naturel** : Ajoutez des événements en parlant naturellement
- ✅ **Support vocal** : Parlez directement pour créer vos rendez-vous (optionnel)
- ✅ **IA locale** : Utilise Ollama pour garder vos données privées
- ✅ **Support multilingue** : Français, Anglais, etc.
- ✅ **Événements et tâches** : Gère les deux types automatiquement
- ✅ **Interface graphique** : Widget minimaliste toujours visible

## 📋 Prérequis

### 1. Installer Ollama

Téléchargez et installez Ollama depuis [ollama.ai](https://ollama.ai/)

```bash
# Linux
curl -fsSL https://ollama.ai/install.sh | sh

# macOS
brew install ollama

# Windows
# Téléchargez depuis https://ollama.ai/download
```

### 2. Démarrer Ollama

```bash
ollama serve
```

### 3. Télécharger un modèle

```bash
# Modèle recommandé (léger et performant)
ollama pull llama2

# Alternative : modèles plus puissants
ollama pull llama2:13b
ollama pull mistral
ollama pull mixtral
```

### 4. Installer plann et les dépendances Python

```bash
# Installer plann (requis pour les commandes plann-ai et plann-ai-gui)
pip install .  # ou 'pip install -e .' pour le mode développement

# Installer les dépendances Ollama
pip install -r requirements-ollama.txt

# Optionnel : pour le mode vocal
pip install SpeechRecognition pyaudio
```

## 🎯 Utilisation

### Interface graphique (GUI) - RECOMMANDÉ ! 🎨

Une interface minimaliste pour rester dans un coin de votre bureau :

```bash
# Lancer l'interface graphique
plann-ai-gui
```

**Fonctionnalités de l'interface :**
- 📝 Zone de texte pour saisie en langage naturel
- ➕ Bouton pour ajouter instantanément
- 🎤 Bouton pour saisie vocale
- 📜 Historique des ajouts récents
- 📌 Option "Toujours au premier plan" (activée par défaut)
- 🎨 Design sombre et minimaliste
- ⌨️ Raccourci clavier : Entrée pour ajouter, Shift+Entrée pour nouvelle ligne

**Capture d'écran conceptuelle :**
```
┌─────────────────────────────────┐
│   📅 Plann AI                   │
│   🟢 Connecté à Ollama (llama2) │
├─────────────────────────────────┤
│ Décrivez votre événement :      │
│ ┌─────────────────────────────┐ │
│ │ Réunion demain à 14h       │ │
│ └─────────────────────────────┘ │
│  [➕ Ajouter]  [🎤 Vocal]       │
├─────────────────────────────────┤
│ Historique récent :             │
│ ┌─────────────────────────────┐ │
│ │ [14:23:12] 📝 Réunion...   │ │
│ │ [14:23:15] ✓ Ajouté: Réu...│ │
│ │ [14:24:01] 📝 Acheter pain │ │
│ │ [14:24:03] ✓ Ajouté: Ach...│ │
│ └─────────────────────────────┘ │
│ ☑ Toujours au premier plan 🗑️  │
└─────────────────────────────────┘
```

L'interface se positionne automatiquement dans le coin supérieur droit de votre écran et reste accessible en permanence !

### Mode ligne de commande

#### Mode texte

```bash
# Événements
plann-ai "Rendez-vous dentiste demain à 14h"
plann-ai "Réunion équipe lundi 10h pour 2 heures"
plann-ai "Dîner avec Marie vendredi soir à 19h30"

# Tâches
plann-ai "Acheter du pain"
plann-ai "Finir le rapport pour vendredi"
plann-ai "Appeler le plombier demain matin"
```

#### Mode vocal

```bash
# Activer le microphone et parler
plann-ai --voice
```

### Options avancées

```bash
# Utiliser un modèle spécifique
plann-ai --model mistral "Réunion importante demain"

# Tester sans exécuter (dry-run)
plann-ai --dry-run "Rendez-vous médecin lundi"

# Afficher les détails de parsing
plann-ai --debug "Appel client mardi 15h"

# Tester la connexion à Ollama
plann-ai --test-connection

# Utiliser une autre instance Ollama
plann-ai --ollama-host http://192.168.1.100:11434 "Événement"

# Utiliser une section de configuration spécifique
plann-ai --config-section travail "Réunion projet"
```

## 📖 Exemples détaillés

### Événements de calendrier

```bash
# Avec date et heure
plann-ai "Réunion de travail demain à 9h"

# Avec durée
plann-ai "Conférence lundi 14h pour 3 heures"

# Avec jour de la semaine
plann-ai "Dentiste mardi prochain à 15h30"

# Avec rappel (si mentionné)
plann-ai "Appel important demain 10h, me rappeler 1 heure avant"
```

### Tâches (todos)

```bash
# Tâche simple
plann-ai "Faire les courses"

# Avec date d'échéance
plann-ai "Rendre le dossier pour vendredi"

# Avec priorité implicite
plann-ai "URGENT : envoyer le rapport"

# Tâche avec priorité
plann-ai "Préparer la présentation pour lundi"
```

## ⚙️ Configuration

### Configuration plann (REQUIS)

**Avant de pouvoir utiliser plann-ai ou plann-ai-gui**, vous DEVEZ configurer plann avec vos paramètres CalDAV.

#### Option 1 : Interface graphique de configuration (RECOMMANDÉ) 🎨

**Au premier lancement de plann-ai-gui**, si aucune configuration n'est détectée, un assistant graphique s'affichera automatiquement.

Vous pouvez aussi ouvrir l'assistant manuellement :
- Depuis l'interface : cliquez sur le bouton **⚙️ Configurer**
- En ligne de commande : `python -m plann.gui` (même si pas configuré)

L'assistant vous permet de :
- ✅ Saisir vos paramètres CalDAV (URL, utilisateur, mot de passe)
- ✅ Tester la connexion avant de sauvegarder
- ✅ Voir combien de calendriers sont détectés
- ✅ Sauvegarder automatiquement dans `~/.config/calendar.conf`

**Exemple de serveurs supportés** :
- NextCloud/OwnCloud : `https://votre-cloud.com/remote.php/dav/`
- Google Calendar : `https://apidata.googleusercontent.com/caldav/v2/` (nécessite mot de passe d'application)
- iCloud : `https://caldav.icloud.com/` (nécessite mot de passe d'application)
- Radicale, Baïkal, etc.

#### Option 2 : Configuration manuelle

Le fichier de configuration doit être créé dans `~/.config/calendar.conf` (format JSON ou YAML).

**Exemple rapide (JSON)** :
```json
{
  "default": {
    "caldav_url": "https://votre-serveur.com/caldav/",
    "caldav_user": "votre_utilisateur",
    "caldav_pass": "votre_mot_de_passe"
  }
}
```

**Fichiers d'exemple fournis** :
- `calendar.conf.example` - Exemple minimal en JSON
- `calendar.conf.example.yaml` - Exemple complet en YAML avec NextCloud, Google Calendar, iCloud, etc.

Pour utiliser un exemple :
```bash
# Copier et éditer un exemple
cp calendar.conf.example ~/.config/calendar.conf
# Puis éditez le fichier avec vos paramètres

# Tester la configuration
plann list-calendars
```

### Variables d'environnement

```bash
# URL de l'API Ollama (défaut: http://localhost:11434)
export OLLAMA_HOST="http://localhost:11434"

# Modèle par défaut (défaut: llama2)
export OLLAMA_MODEL="mistral"
```

### Utiliser une section de configuration spécifique

```bash
plann-ai --config-section travail "Réunion demain"
plann-ai --config-section perso "Anniversaire Marie samedi"
```

## 🔧 Dépannage

### Ollama n'est pas accessible

```bash
# Vérifier qu'Ollama tourne
ollama list

# Si ce n'est pas le cas
ollama serve

# Tester la connexion
plann-ai --test-connection
```

### Le modèle n'est pas installé

```bash
# Lister les modèles installés
ollama list

# Installer un modèle
ollama pull llama2
```

### Problème de reconnaissance vocale

```bash
# Vérifier que les dépendances sont installées
pip install SpeechRecognition pyaudio

# Sur Linux, installer portaudio
sudo apt-get install portaudio19-dev python3-pyaudio

# Sur macOS
brew install portaudio
```

### Erreur de parsing

Si le modèle ne comprend pas bien votre texte :

1. Utilisez un modèle plus puissant : `--model mistral`
2. Soyez plus explicite : "Rendez-vous dentiste le 25 octobre à 14h00"
3. Utilisez `--debug` pour voir ce qui est parsé

## 🧪 Tests

### Test de connexion Ollama

```bash
python3 -c "from plann.ollama import test_ollama_connection; test_ollama_connection()"
```

### Test complet

```bash
# Mode dry-run pour voir sans exécuter
plann-ai --dry-run --debug "Rendez-vous test demain à 10h"
```

## 🎨 Exemples d'utilisation avancés

### Script shell pour rappels quotidiens

```bash
#!/bin/bash
# morning_routine.sh

plann-ai "Révision du code à 9h"
plann-ai "Pause café à 10h30 pour 15 minutes"
plann-ai "Déjeuner à 12h30 pour 1 heure"
plann-ai "Réunion d'équipe à 15h pour 30 minutes"
```

### Intégration avec d'autres outils

```bash
# Depuis un fichier
cat taches.txt | while read line; do
  plann-ai "$line"
done

# Avec fzf (sélecteur interactif)
echo "Rendez-vous dentiste\nRéunion équipe\nAppeler client" | \
  fzf --multi | while read line; do
    plann-ai "$line demain"
  done
```

## 🏗️ Architecture technique

### Composants

1. **plann/ollama.py** : Module d'intégration Ollama
   - `OllamaClient` : Communique avec l'API Ollama
   - `NaturalLanguageParser` : Parse le texte en langage naturel
   - `format_for_plann()` : Convertit en format plann

2. **plann/ai_cli.py** : Interface en ligne de commande
   - Utilise Click pour le CLI
   - Interface avec plann.commands
   - Gère les arguments et options

3. **plann/gui.py** : Interface graphique
   - Widget Tkinter minimaliste
   - Mode always-on-top
   - Historique en temps réel

### Flux de données

```
Texte/Voix → plann-ai → OllamaClient → Ollama (modèle IA)
                                           ↓
                        Données structurées (JSON)
                                           ↓
                        format_for_plann()
                                           ↓
                        _add_event / _add_todo
                                           ↓
                             plann → CalDAV
```

### Différences avec calendar-cli

plann-ai utilise l'architecture moderne de plann :
- ✅ Click au lieu d'argparse
- ✅ Fonctions modulaires (_add_event, _add_todo)
- ✅ Meilleure gestion des contextes
- ✅ Priorités sur échelle 1-9 (au lieu de 1-5)
- ✅ Meilleure gestion des calendriers multiples

## 📦 Installation

### Depuis le code source

```bash
# Cloner le repository (ou si vous avez déjà le code)
cd plann

# IMPORTANT: Installer plann lui-même d'abord
pip install .  # ou 'pip install -e .' pour le mode développement

# Installer les dépendances Ollama
pip install -r requirements-ollama.txt

# Optionnel : avec support vocal
pip install ".[voice]"
```

**Note importante**: Vous devez installer le package `plann` lui-même avec `pip install .` avant de pouvoir utiliser les commandes `plann-ai` et `plann-ai-gui`. L'installation des requirements seuls (`pip install -r requirements-ollama.txt`) n'est pas suffisante.

## 🤝 Contribution

Les contributions sont les bienvenues ! N'hésitez pas à :

- Signaler des bugs
- Proposer de nouvelles fonctionnalités
- Améliorer la documentation
- Ajouter des tests

## 📄 Licence

Même licence que plann (GPLv3)

## 🙏 Remerciements

- [Ollama](https://ollama.ai/) pour l'IA locale
- [plann](https://github.com/tobixen/plann) pour l'outil CalDAV
- La communauté open-source

---

**Astuce** : Pour une expérience optimale, utilisez un modèle adapté à votre langue :

- Français : `llama2`, `mistral`, `mixtral`
- Multilingue : `llama2:13b`, `mixtral:8x7b`

Amusez-vous bien avec votre nouveau calendrier en langage naturel ! 🎉
