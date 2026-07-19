"""
Video/Audio Downloader — Main entry point.

Workflow:
1. Update yt-dlp if needed (max 1x/day)
2. Check/export cookies
3. Read URL from clipboard
4. Ask user: video or audio?
5. Download via yt-dlp (universal) or KVS fallback
6. Open result in explorer
"""

import os
import re

import pyperclip

from core.cookies import check_and_export_cookies
from core.updater import update_yt_dlp_if_needed
from core.ui import ask_download_type
from core.file_utils import (
    open_file_explorer,
    extract_audio_from_file,
)
from downloaders.ytdlp_downloader import YtdlpDownloader
from downloaders.kvs_downloader import is_kvs_site, download_kvs_video


# ---------------------------------------------------------------------------
# URL helpers
# ---------------------------------------------------------------------------


def is_valid_url(url):
    """Check if string is a valid HTTP(S) URL."""
    return bool(re.match(r"^https?://[^\s]+", url))


def get_url_from_clipboard():
    """
    Read and validate URL or local path from clipboard.

    Returns:
        tuple: (type, content) where type is 'url' or 'local', or None
    """
    print("\nRécupération de l'URL depuis le presse-papier...")
    content = pyperclip.paste()

    if not content:
        print("Le presse-papier est vide.")
        return None

    content = content.strip()

    # Strip surrounding quotes
    if (content.startswith('"') and content.endswith('"')) or (
        content.startswith("'") and content.endswith("'")
    ):
        content = content[1:-1]

    print(f"Contenu du presse-papier : '{content}'")

    if is_valid_url(content):
        return ("url", content)
    elif os.path.exists(content):
        print("Chemin local détecté.")
        return ("local", content)
    else:
        print(
            "Le contenu du presse-papier n'est pas une URL valide "
            "ni un chemin local existant."
        )
        return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    print("\n===== Début du processus =====\n")

    # Step 1: Update yt-dlp (throttled to 1x/day)
    update_yt_dlp_if_needed()

    # Step 2: Check cookies
    check_and_export_cookies()

    # Step 3: Get URL from clipboard
    result = get_url_from_clipboard()
    if not result:
        return

    content_type, content = result

    # Step 4: Handle local files (audio extraction only)
    if content_type == "local":
        print(f"\nFichier local: {content}")
        audio_path = extract_audio_from_file(content)
        if audio_path:
            open_file_explorer(audio_path)
        return

    # Step 5: Ask download type (video or audio)
    url = content
    print(f"\nTraitement de l'URL : {url}")
    download_type = ask_download_type()

    # Step 6: Download
    try:
        # Try KVS extractor first for KVS sites
        if is_kvs_site(url):
            print("\nSite KVS détecté, utilisation de l'extracteur spécialisé...")
            if download_kvs_video(url):
                return
            print("KVS échoué, tentative avec yt-dlp...")

        # Universal yt-dlp download (handles YouTube, Instagram, generic, etc.)
        downloader = YtdlpDownloader()
        downloader.download(url, download_type)

    except KeyboardInterrupt:
        print("\n\nTéléchargement interrompu par l'utilisateur.")
    except Exception as e:
        print(f"\nErreur lors du traitement : {e}")

    print("\n===== Processus terminé =====")


if __name__ == "__main__":
    main()
