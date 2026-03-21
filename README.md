# 🚀 Windows Optimization Toolkit

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/version-1.0-blue.svg)](https://github.com/3C0D/Windows-Optimization-Toolkit)

A collection of tools to enhance your Windows experience with audio/video download capabilities, AutoHotkey shortcuts, and productivity utilities.

## 📋 Table of Contents

- [🚀 Windows Optimization Toolkit](#-windows-optimization-toolkit)
  - [📋 Table of Contents](#-table-of-contents)
  - [Overview](#overview)
  - [Prerequisites](#prerequisites)
  - [📥 Audio Video Download](#-audio-video-download)
    - [Fonctionnalités](#fonctionnalités)
    - [Utilisation](#utilisation)
    - [Installation](#installation)
  - [⌨️ Shortcuts Viewer](#️-shortcuts-viewer)
    - [Fonctionnalités](#fonctionnalités-1)
    - [Applications incluses](#applications-incluses)
      - [Browser Shortcuts](#browser-shortcuts)
      - [OCR Traduction](#ocr-traduction)
    - [Utilisation](#utilisation-1)
    - [Installation](#installation-1)
  - [Contributing](#contributing)
  - [License](#license)

## Overview

This toolkit provides utilities to optimize your Windows workflow, including:

- **Video and audio download** capabilities for YouTube and other platforms
- **AutoHotkey productivity tools** for quick access to shortcuts and AI services
- **OCR and translation** features for screen captures

## Prerequisites

- Windows 10/11
- [Python 3.8+](https://www.python.org/downloads/) for Python scripts
- [AutoHotkey v2.0](https://www.autohotkey.com/) for Shortcuts Viewer and productivity tools

## 📥 Audio Video Download

Un outil puissant pour télécharger des vidéos et de l'audio depuis YouTube, Odysee et d'autres sites web.

### Fonctionnalités

- **Téléchargement de vidéos YouTube** avec choix de qualité (jusqu'à 1080p)
- **Extraction audio en MP3** avec différentes qualités (192, 128, 96 kbps)
- **Support pour Odysee** et autres plateformes vidéo
- **Installation automatique** des dépendances et mises à jour
- **Exportation automatique des cookies** depuis Chrome pour accéder aux contenus restreints

### Utilisation

1. Copiez l'URL de la vidéo dans le presse-papier
2. Exécutez `video_audio_download\video_audio_download.bat`
3. Choisissez le type de téléchargement (vidéo ou audio)
4. Sélectionnez la qualité souhaitée
5. Le fichier sera téléchargé dans le dossier approprié et l'explorateur s'ouvrira automatiquement

### Installation

Aucune installation manuelle n'est nécessaire. Le script gère automatiquement :

- La création d'un environnement virtuel Python
- L'installation des modules requis (yt-dlp, pyperclip, etc.)
- La mise à jour de yt-dlp
- L'exportation des cookies depuis Chrome

> **Astuce :** Créez un raccourci sur votre bureau vers le fichier `video_audio_download.bat` pour un accès rapide à l'outil.

Pour plus de détails, consultez le [README dédié](video_audio_download/README.md) de cet outil.

## ⌨️ Shortcuts Viewer

Un outil AutoHotkey pour gérer et afficher vos raccourcis clavier et améliorer votre productivité.

### Fonctionnalités

- **Mémorisation de vos raccourcis personnels** dans un fichier JSON
- **Interface utilisateur intuitive** pour consulter et modifier vos raccourcis
- **Raccourci global** (Win+Shift+/) pour ouvrir l'interface à tout moment
- **Thème sombre** pour un confort visuel optimal
- **Contrôle de la veille du PC** pour empêcher l'ordinateur de se mettre en veille (Shift+Win+V)
- **Menu des services d'IA** avec accès rapide à Claude, ChatGPT, Gemini, etc. (Win+Shift+I)
- **Copie sans formatage Markdown** pour nettoyer le texte copié (Ctrl+Shift+C)
- **Sélection du service OCR** pour choisir entre Claude, Mistral ou Gemini (Win+Q)
- **Toggle toujours-au-dessus** pour épingler/détacher une fenêtre (Ctrl+Win+T)

### Applications incluses

#### Browser Shortcuts

- **Accès rapide aux IA** (Win+Shift+I) : Menu pour accéder à Claude, ChatGPT, Gemini, etc.
- **Recherche intelligente** (Win+Shift+U) : Ouvre l'URL ou recherche le texte sélectionné
- **Traduction rapide** (Win+Shift+T) : Traduit le texte sélectionné via Google
- **Copie sans Markdown** (Ctrl+Shift+C) : Copie le texte sélectionné en supprimant tout formatage Markdown, ou convertit le contenu du presse-papier si aucune sélection

#### OCR Traduction

- **Sélection du service OCR** (Win+Q) : Menu pour choisir entre Claude, Mistral ou Gemini (choix sauvegardé)
- **Capture et traduction d'écran** (Shift+Win+Q) : Capture une zone de l'écran et l'envoie à l'IA sélectionnée pour extraction et traduction du texte
- **Support multilingue** : Détecte automatiquement la langue et traduit en français si nécessaire

### Utilisation

1. Appuyez sur **Win+Shift+/** pour ouvrir l'interface principale
2. Consultez ou modifiez vos raccourcis personnels
3. Utilisez les raccourcis spécifiques pour les fonctionnalités avancées :
   - **Win+Shift+I** : Menu des IA
   - **Win+Shift+U** : Recherche/URL
   - **Win+Shift+T** : Traduction
   - **Ctrl+Shift+C** : Copie sans Markdown
   - **Win+Q** : Sélectionner le service OCR (Claude/Mistral/Gemini)
   - **Shift+Win+Q** : Capture d'écran OCR et traduction
   - **Shift+Win+V** : Basculer le mode veille du PC
   - **Ctrl+Win+T** : Toggle always-on-top (épingler/détacher la fenêtre)

### Installation

1. Assurez-vous d'avoir [AutoHotkey v2.0](https://www.autohotkey.com/) installé
2. Exécutez le script `AutoHotkey/Shortcuts viewer/shortcutsViewer.ahk`

> **Astuce :** Créez un raccourci au démarrage vers le fichier `shortcutsViewer.ahk` pour que les fonctionnalités soient toujours disponibles.
>
> **Astuce IA :** Utilisez le raccourci **Win+Shift+I** pour accéder rapidement à toutes les plateformes d'IA (Claude, ChatGPT, Gemini, etc.) via le menu dédié.

## Contributing

Contributions to the Windows Optimization Toolkit are welcome! Here's how you can contribute:

1. **Fork the repository**
2. **Create a feature branch**

   ```
   git checkout -b feature/amazing-feature
   ```

3. **Commit your changes**

   ```
   git commit -m 'Add some amazing feature'
   ```

4. **Push to the branch**

   ```
   git push origin feature/amazing-feature
   ```

5. **Open a Pull Request**

Please make sure to update tests as appropriate and follow the coding style of the project.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<p align="center">
Made with ❤️ by <a href="https://github.com/3C0D">3C0D</a>
</p>
