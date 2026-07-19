"""
User interaction helpers.
Single implementation for download type choices, file replacement prompts, etc.
"""

import os


def ask_download_type():
    """
    Ask the user whether to download video or audio.

    Returns:
        str: "video" or "audio"
    """
    print("\nQue souhaitez-vous télécharger ?")
    print("1. Vidéo (avec audio)")
    print("2. Audio uniquement (MP3)")

    while True:
        try:
            choice = input(
                "\nEntrez votre choix (1-2) ou appuyez sur Entrée pour la vidéo: "
            )
            if not choice.strip():
                return "video"
            choice = int(choice)
            if choice == 1:
                return "video"
            elif choice == 2:
                return "audio"
            else:
                print("Veuillez entrer 1 ou 2")
        except ValueError:
            print("Veuillez entrer un nombre valide")


def ask_replace_file(filepath):
    """
    Ask the user if they want to replace an existing file.

    Args:
        filepath: Path to the existing file

    Returns:
        bool: True if user wants to replace, False to cancel
    """
    filename = os.path.basename(filepath)

    print("\n" + "=" * 60)
    print(f"ATTENTION: Le fichier '{filename}' existe déjà !")
    print(f"Chemin: {filepath}")
    print("=" * 60)

    while True:
        choice = input("Voulez-vous remplacer ce fichier ? (o/n): ").lower()
        if choice in ("o", "oui", "y", "yes"):
            return True
        elif choice in ("n", "non", "no"):
            return False
        else:
            print("Veuillez répondre par 'o' (oui) ou 'n' (non).")


def ask_extract_audio_from_existing(filepath):
    """
    When a video file already exists, ask if user wants to extract audio from it.

    Args:
        filepath: Path to the existing video file

    Returns:
        bool: True if user wants to extract audio
    """
    filename = os.path.basename(filepath)

    print(f"\nLe fichier vidéo '{filename}' existe déjà.")
    print("Souhaitez-vous en extraire l'audio (MP3) ?")

    while True:
        choice = input("Extraire l'audio ? (o/n): ").lower()
        if choice in ("o", "oui", "y", "yes"):
            return True
        elif choice in ("n", "non", "no"):
            return False
        else:
            print("Veuillez répondre par 'o' (oui) ou 'n' (non).")


def ask_video_quality(quality_options):
    """
    Ask the user to select video quality from available options.

    Args:
        quality_options: List of dicts with 'display_name' and 'format_string'

    Returns:
        dict: Selected quality option
    """
    if not quality_options:
        return None

    print("\nFormats vidéo disponibles:")
    for i, option in enumerate(quality_options, 1):
        print(f"  {i}. {option['display_name']}")

    while True:
        try:
            user_input = input(
                "\nChoisissez la qualité (numéro) ou "
                "appuyez sur Entrée pour la meilleure qualité: "
            )
            if not user_input.strip():
                return quality_options[0]
            idx = int(user_input)
            if 1 <= idx <= len(quality_options):
                return quality_options[idx - 1]
            print(f"Veuillez entrer un nombre entre 1 et {len(quality_options)}")
        except ValueError:
            print("Veuillez entrer un nombre valide")
