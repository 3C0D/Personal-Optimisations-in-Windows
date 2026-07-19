"""
KVS (Kernel Video Sharing) site downloader.
Used as a fallback for sites that yt-dlp doesn't handle well.
"""

import os

from core.config import OUTPUT_DIR, KVS_SITES
from core.cookies import get_cookies_file
from core.file_utils import open_file_explorer, find_latest_file
from urllib.parse import urlparse


def is_kvs_site(url):
    """Check if the URL belongs to a KVS-powered site."""
    domain = urlparse(url).netloc.lower()
    return any(
        domain == d or domain.endswith("." + d)
        for d in KVS_SITES
    )


def download_kvs_video(url):
    """
    Download video from a KVS site using the KVS extractor module.
    Falls back to yt-dlp if extraction fails.
    """
    print("\nAnalyse de la vidéo KVS...")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    cookies_file = get_cookies_file()

    try:
        # Import the KVS extractor (kept as standalone module)
        from kvs_extractor import KVSExtractor

        extractor = KVSExtractor(cookies_file)
        video_info = extractor.extract_video_info(url)

        if video_info and video_info["sources"]:
            print(f"Titre: {video_info['title']}")
            print(f"Sources trouvées: {len(video_info['sources'])}")

            for i, source in enumerate(video_info["sources"]):
                print(f"  {i + 1}. {source}")

            print("\nTéléchargement en cours...")
            success = extractor.download_video(video_info, OUTPUT_DIR)

            if success:
                latest = find_latest_file(OUTPUT_DIR, (".mp4",))
                if latest:
                    print(f"Fichier téléchargé: {latest}")
                    open_file_explorer(latest)
                else:
                    print("Téléchargement terminé")
                    open_file_explorer(OUTPUT_DIR)
                return True
            else:
                print("Échec du téléchargement KVS")
                return False
        else:
            print("Aucune source vidéo KVS trouvée")
            return False

    except Exception as e:
        print(f"Erreur avec l'extracteur KVS: {e}")
        return False
