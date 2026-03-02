import sys
import subprocess
import os
import re
import time
import json
import tempfile
import http.cookiejar
import shutil

from urllib.parse import urlparse
import pyperclip
import yt_dlp
from bs4 import BeautifulSoup
from tqdm import tqdm
import requests
import browser_cookie3

# Import du KVS extractor
from kvs_extractor import KVSExtractor

# Platform specific
if sys.platform == "win32":
    import winreg


def open_file_explorer(path):
    """
    Open Windows file explorer at specified location.

    Args:
        path (str): Path of file or folder to open
    """
    # Normalize path to avoid issues with slashes
    normalized_path = os.path.normpath(path)

    # Try to open file explorer directly
    try:
        # Check if it's a file or folder
        if os.path.isfile(normalized_path):
            # Open folder containing file and select the file
            subprocess.Popen(f'explorer /select,"{normalized_path}"', shell=True)
        else:
            # Open folder directly
            subprocess.Popen(f'explorer "{normalized_path}"', shell=True)
    except Exception as e:
        print(f"Note: Unable to automatically open file explorer: {e}")
        print(f"File path: {normalized_path}")


def get_windows_downloads_folder():
    """
    Obtient le chemin exact du dossier Téléchargements sur Windows en utilisant le registre.
    Cette méthode fonctionne quelle que soit la langue du système.

    Returns:
        str: Chemin du dossier Téléchargements
    """
    try:
        # GUID du dossier Téléchargements dans Windows
        downloads_guid = "{374DE290-123F-4565-9164-39C4925E467B}"

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders",
        ) as key:
            downloads = winreg.QueryValueEx(key, downloads_guid)
            return downloads[0]
    except Exception:
        # Fallback 1: Essayer avec le nom connu
        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders",
            ) as key:
                downloads = winreg.QueryValueEx(key, "Downloads")
                return downloads[0]
        except Exception:
            # Fallback 2: Utiliser la méthode standard
            user_profile = os.environ.get("USERPROFILE")
            if user_profile:
                # Essayer les noms courants
                for name in ["Téléchargements", "Downloads"]:
                    path = os.path.join(user_profile, name)
                    if os.path.exists(path):
                        return path
                # Dernier recours
                return os.path.join(user_profile, "Downloads")
            else:
                return os.path.join(os.path.expanduser("~"), "Downloads")


def get_download_path(source_type):
    """
    Obtient le chemin de téléchargement pour un type de source donné.
    Crée les dossiers nécessaires s'ils n'existent pas.

    Args:
        source_type (str): Type de source ('youtube', 'youtube_audio', 'generic', 'generic_audio')

    Returns:
        str: Chemin complet vers le dossier de téléchargement
    """
    # Obtenir le dossier Téléchargements/Downloads de l'utilisateur
    # Comme ce script est conçu pour Windows, on utilise directement la fonction spécifique
    downloads_folder = get_windows_downloads_folder()

    # Déterminer si c'est un téléchargement audio ou vidéo
    is_audio = "_audio" in source_type.lower()
    base_type = source_type.lower().replace("_audio", "")

    # Déterminer le dossier principal (Audio ou Video)
    main_folder = "Audio" if is_audio else "Video"

    # Créer le chemin complet selon le type de source
    if base_type == "youtube":
        path = os.path.join(downloads_folder, main_folder, "Youtube")
    else:  # generic
        path = os.path.join(downloads_folder, main_folder, "Generic")

    # Créer les dossiers s'ils n'existent pas
    os.makedirs(path, exist_ok=True)

    return path


def check_and_export_cookies():
    """Check if cookies.txt file exists, otherwise export from Chrome"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cookies_file = os.path.join(script_dir, "cookies.txt")

    if os.path.exists(cookies_file):
        # Cookie file already exists, check if it's valid
        try:
            cookie_jar = http.cookiejar.MozillaCookieJar(cookies_file)
            cookie_jar.load()
            # If we get here, the file is valid
            print("\nCookies file already present and valid.")
            return
        except Exception:
            # File exists but is not valid, recreate it
            try:
                os.remove(cookies_file)
                print(
                    "\nCorrupted cookies file detected and deleted. Attempting to recreate..."
                )
            except Exception:
                pass

    # If we get here, either file doesn't exist or was corrupted and deleted
    print("\nChecking YouTube cookies...")
    print("Cookies allow access to age-restricted videos and private content.")

    # If we get here, cookies need to be exported
    try:
        print("\nExporting cookies from Chrome...")
        # Create an empty but valid cookie file
        cookie_jar = http.cookiejar.MozillaCookieJar(cookies_file)

        try:
            # Try with Chrome first
            cookies = browser_cookie3.chrome()
            for cookie in cookies:
                cookie_jar.set_cookie(cookie)
            cookie_jar.save()
            print("Cookies exported successfully from Chrome.")
        except Exception as chrome_error:
            # If Chrome fails, create an empty but valid cookie file
            print(f"Error exporting cookies from Chrome: {chrome_error}")
            print("Creating empty but valid cookie file...")

            # Create Netscape format cookie file header
            with open(cookies_file, "w") as f:
                f.write("# Netscape HTTP Cookie File\n")
                f.write("# https://curl.haxx.se/docs/http-cookies.html\n")
                f.write(
                    "# This file was generated by yt-dlp! Edit at your own risk.\n\n"
                )

            print("Empty cookie file created successfully.")
            print(
                "\nWarning: Without valid cookies, age-restricted videos will not be accessible."
            )
            print("You can continue using the script for videos without restrictions.")
    except Exception as e:
        print(f"Error managing cookies: {e}")
        print("\nTo use YouTube cookies, you must:")
        print("1. Log in to your YouTube account via Chrome browser")
        print("2. Keep your session active in Chrome")
        print("3. Rerun this script")
        print("\nNote: Only Chrome cookies are supported for now.")


def update_yt_dlp():
    """Update yt-dlp to stable version via uv"""
    try:
        print("\nChecking for yt-dlp updates...")
        print("Regular updates are necessary to bypass YouTube API changes.")
        # Use uv to update yt-dlp (project uses uv, not pip)
        result = subprocess.run(
            ["uv", "pip", "install", "--upgrade", "yt-dlp"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            output = result.stdout.lower()
            if (
                "already up-to-date" in output
                or "already satisfied" in output
                or "audited" in output
            ):
                print("yt-dlp is already up to date.")
            else:
                print("yt-dlp has been successfully updated.")
        else:
            print(f"Error updating yt-dlp: {result.stderr}")
    except Exception as e:
        print(f"Error updating yt-dlp: {e}")


def detect_kvs_sites(url):
    """
    Détecte si l'URL appartient à un site utilisant KVS (Kernel Video Sharing)
    """
    kvs_sites = [
        "pervarchive.com",
        "www.pervarchive.com",
        "pervertium.com",
        "www.pervertium.com",
        "tezfiles.com",
        "www.tezfiles.com",
        "www.analdin.com",
        # Ajoutez d'autres sites KVS ici
    ]

    domain = urlparse(url).netloc.lower()

    for kvs_domain in kvs_sites:
        if domain == kvs_domain or domain.endswith("." + kvs_domain):
            print(f"Site KVS détecté: {domain}")
            return True

    return False


def download_kvs_video(url):
    """Télécharge une vidéo depuis un site KVS"""
    print("\nAnalyse de la vidéo KVS...")

    # Déterminer le chemin de destination
    local_path = get_download_path("generic")

    # Utiliser le fichier cookies s'il existe
    cookies_file = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "cookies.txt"
    )

    try:
        # Créer l'extracteur KVS
        extractor = KVSExtractor(cookies_file if os.path.exists(cookies_file) else None)

        # Extraire les informations vidéo
        video_info = extractor.extract_video_info(url)

        if video_info and video_info["sources"]:
            print(f"Titre: {video_info['title']}")
            print(f"Sources trouvées: {len(video_info['sources'])}")

            for i, source in enumerate(video_info["sources"]):
                print(f"  {i + 1}. {source}")

            # Télécharger automatiquement
            print("\nTéléchargement en cours...")
            success = extractor.download_video(video_info, local_path)

            if success:
                # Trouver le fichier téléchargé le plus récent
                files = [f for f in os.listdir(local_path) if f.endswith(".mp4")]
                if files:
                    latest_file = os.path.join(
                        local_path,
                        max(
                            files,
                            key=lambda x: os.path.getctime(os.path.join(local_path, x)),
                        ),
                    )
                    print(f"Fichier téléchargé: {latest_file}")
                    open_file_explorer(latest_file)
                else:
                    print("Téléchargement terminé")
                    open_file_explorer(local_path)
            else:
                print("Échec du téléchargement")
        else:
            print("Aucune source vidéo trouvée")
            print("Tentative avec yt-dlp comme fallback...")
            download_generic_video_with_fallback(url)

    except Exception as e:
        print(f"Erreur avec l'extracteur KVS: {e}")
        print("Tentative avec yt-dlp comme fallback...")
        download_generic_video_with_fallback(url)


def detect_protected_sites(url):
    """
    Detect if the URL belongs to a protected site that requires yt-dlp specialized handling
    Returns the site type or 'generic' if not protected
    """
    protected_sites = {
        "m6.fr": "m6",
        "www.m6.fr": "m6",
        "m6plus.fr": "m6",
        "www.m6plus.fr": "m6",
        "tf1.fr": "tf1",
        "www.tf1.fr": "tf1",
        "lci.tf1.fr": "tf1",
        "france.tv": "francetv",
        "www.france.tv": "francetv",
        "francetvinfo.fr": "francetv",
        "www.francetvinfo.fr": "francetv",
        "6play.fr": "m6",
        "www.6play.fr": "m6",
        "tf1play.fr": "tf1",
        "www.tf1play.fr": "tf1",
        "pluzz.francetv.fr": "francetv",
        "rumble.com": "rumble",
        "www.rumble.com": "rumble",
        "twitter.com": "twitter",
        "www.twitter.com": "twitter",
        "x.com": "twitter",
        "www.x.com": "twitter",
    }

    domain = urlparse(url).netloc.lower()

    for site_domain, site_type in protected_sites.items():
        if domain == site_domain or domain.endswith("." + site_domain):
            print(f"Protected site detected: {site_type} ({domain})")
            return site_type

    return "generic"


def validate_downloaded_file(filepath, expected_min_size_mb=10):
    """
    Validate that the downloaded file is complete and not just a chunk
    """
    if not os.path.exists(filepath):
        return False, "File does not exist"

    file_size_mb = os.path.getsize(filepath) / (1024 * 1024)

    if file_size_mb < expected_min_size_mb:
        return (
            False,
            f"File too small: {file_size_mb:.2f} MB (minimum: {expected_min_size_mb} MB)",
        )

    # Try to detect if file is corrupted by checking first few bytes
    try:
        with open(filepath, "rb") as f:
            header = f.read(100)
            if b"<html" in header.lower() or b"<!doctype" in header.lower():
                return False, "File appears to be HTML (likely error page)"

            # Check if file starts with typical video file headers
            video_headers = [
                b"\x00\x00\x00\x20ftyp",  # MP4
                b"\x00\x00\x00\x18ftyp",  # MP4
                b"RIFF",  # AVI/WAV
                b"\x1a\x45\xdf\xa3",  # MKV
                b"FWS",  # Flash Video
                b"FLV",  # FLV
                b"\x00\x00\x00\x20ftypmp4",  # MP4 variant
                b"\x00\x00\x00\x20ftypM4A",  # M4A audio
                b"\x00\x00\x00\x20ftypf4v",  # FLV variant
            ]

            is_valid_video = any(header.startswith(h) for h in video_headers)
            if not is_valid_video:
                return False, "File does not appear to be a valid video/audio format"

    except Exception as e:
        return False, f"Error validating file: {e}"

    return True, f"File validation successful: {file_size_mb:.2f} MB"


def get_available_video_qualities(available_formats):
    """
    Récupère les formats vidéo disponibles, limités à 1080p maximum.
    Retourne une liste de formats triés par qualité.
    """
    # Définir les résolutions standard à proposer
    standard_resolutions = [1080, 720, 480]

    # Préparer les options de qualité à présenter à l'utilisateur
    quality_options = []

    # Filtrer les formats qui contiennent de la vidéo (pas seulement audio)
    video_formats = [f for f in available_formats if f.get("vcodec") != "none"]

    # Extraire les hauteurs disponibles
    available_heights = set()
    for fmt in video_formats:
        height = fmt.get("height", 0)
        if (
            height > 0 and height <= 1080
        ):  # Ignorer les résolutions > 1080p et les formats sans hauteur
            available_heights.add(height)

    # Trier les hauteurs par ordre décroissant
    sorted_heights = sorted(available_heights, reverse=True)

    # Pour chaque résolution standard, vérifier si elle est disponible ou trouver la plus proche
    for res in standard_resolutions:
        # Trouver la résolution disponible la plus proche inférieure ou égale
        closest_height = None
        for height in sorted_heights:
            if height <= res:
                closest_height = height
                break

        if closest_height is None:
            continue  # Pas de résolution disponible inférieure ou égale à celle demandée

        # Créer une chaîne de format qui combine vidéo+audio pour cette résolution
        format_string = f"bestvideo[height<={res}]+bestaudio/best[height<={res}]"

        quality_options.append(
            {
                "format_string": format_string,
                "height": res,
                "display_name": f"{res}p",
                "ext": "mp4",  # On force mp4 comme format de sortie
            }
        )

        # Limiter à 3 options maximum
        if len(quality_options) >= 3:
            break

    # Si aucune option n'a été ajoutée (cas rare), ajouter une option par défaut
    if not quality_options and sorted_heights:
        height = sorted_heights[0]
        quality_options.append(
            {
                "format_string": f"bestvideo[height<={height}]+bestaudio/best[height<={height}]",
                "height": height,
                "display_name": f"{height}p",
                "ext": "mp4",
            }
        )

    return quality_options


def is_valid_youtube_url(url):
    youtube_regex = (
        r"(https?://)?(www\.)?"
        r"(youtube|youtu|youtube-nocookie)\.(com|be)/"
        r"(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})"
    )
    return bool(re.match(youtube_regex, url))


def is_valid_instagram_url(url):
    instagram_regex = r"https?://(www\.)?instagram\.com/(p|reel|tv)/([a-zA-Z0-9_-]+)"
    return bool(re.match(instagram_regex, url))


def is_valid_url(url):
    """Vérifie si la chaîne est une URL valide"""
    url_regex = r"^https?://[^\s]+"
    return bool(re.match(url_regex, url))


def get_url_from_clipboard():
    """Récupère et valide l'URL ou le chemin local depuis le presse-papier"""
    print("\nRécupération de l'URL depuis le presse-papier...")
    content = pyperclip.paste()

    if not content:
        print("Le presse-papier est vide.")
        return None

    content = content.strip()
    # Supprimer les guillemets si présents
    if (content.startswith('"') and content.endswith('"')) or (
        content.startswith("'") and content.endswith("'")
    ):
        content = content[1:-1]
    print(f"Contenu du presse-papier : '{content}'")

    if is_valid_url(content):
        if is_valid_youtube_url(content):
            print("URL YouTube valide trouvée.")
            return ("youtube", content)
        elif is_valid_instagram_url(content):
            print("URL Instagram valide trouvée.")
            return ("instagram", content)
        else:
            print("URL générique trouvée.")
            return ("generic", content)
    else:
        # Vérifier si c'est un chemin local
        if os.path.exists(content):
            print("Chemin local détecté.")
            return ("local", content)
        else:
            print(
                "Le contenu du presse-papier n'est pas une URL valide ni un chemin local existant."
            )
            return None


def download_youtube_video(url):
    print("\nAnalyse de la vidéo YouTube...")

    # Demander à l'utilisateur s'il souhaite télécharger la vidéo ou seulement l'audio
    print("\nQue souhaitez-vous télécharger ?")
    print("1. Vidéo (avec audio)")
    print("2. Audio uniquement (MP3)")

    download_type = None
    while download_type is None:
        try:
            choice = input(
                "\nEntrez votre choix (1-2) ou appuyez sur Entrée pour la vidéo: "
            )
            if not choice.strip():
                download_type = "video"
            else:
                choice = int(choice)
                if choice == 1:
                    download_type = "video"
                elif choice == 2:
                    download_type = "audio"
                else:
                    print("Veuillez entrer 1 ou 2")
        except ValueError:
            print("Veuillez entrer un nombre valide")

    # Déterminer le chemin de destination en fonction du type de téléchargement
    if download_type == "video":
        local_path = get_download_path("youtube")
    else:  # audio
        local_path = get_download_path("youtube_audio")

    # Add cookies file if available
    cookies_file = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "cookies.txt"
    )
    use_cookies = os.path.exists(cookies_file)

    # Options pour l'extraction des informations
    info_opts = {
        "noplaylist": True,
        "nocheckcertificate": True,
        "ignoreerrors": True,
        "no_color": True,
        "geo_bypass": True,
        "geo_bypass_country": "US",
        "extractor_retries": 10,
        "socket_timeout": 60,
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "web"],
                "player_skip": ["js", "configs"],
            }
        },
    }

    # Use cookies if available
    if use_cookies:
        info_opts["cookiesfrombrowser"] = ("chrome", None, None, None)

    try:
        # Extraire les informations de la vidéo sans télécharger
        with yt_dlp.YoutubeDL(info_opts) as ydl:
            print("Extraction des informations de la vidéo...")
            info = ydl.extract_info(url, download=False)

            if info is None:
                raise Exception(
                    "Impossible d'extraire les infos. "
                    "Vidéo indisponible ou cookies expirés."
                )

            video_title = info.get("title", "video")

            # Déterminer l'extension en fonction du type de téléchargement
            file_ext = ".mp3" if download_type == "audio" else ".mp4"
            filename = f"{video_title}{file_ext}"
            filepath = os.path.join(local_path, filename)

            # Vérifier si le fichier existe déjà AVANT de choisir la qualité
            file_exists = False

            try:
                # Vérifier directement si le fichier existe (méthode standard)
                if os.path.exists(filepath):
                    file_exists = True
                else:
                    # Méthode avancée: vérifier tous les fichiers du dossier en normalisant les guillemets
                    if os.path.exists(local_path):
                        # Normaliser le titre de la vidéo pour la comparaison
                        normalized_title = (
                            (video_title or "")
                            .replace('"', "")
                            .replace(
                                """, "")
                            .replace(""",
                                "",
                            )
                            .replace("＇", "")
                        )

                        for file in os.listdir(local_path):
                            # Obtenir le nom du fichier sans extension et le normaliser
                            file_name_without_ext = os.path.splitext(file)[0]
                            normalized_file_name = (
                                file_name_without_ext.replace('"', "")
                                .replace(
                                    """, "")
                                .replace(""",
                                    "",
                                )
                                .replace("＇", "")
                            )

                            # Comparer les noms normalisés
                            if normalized_file_name == normalized_title:
                                file_exists = True
                                # Utiliser le chemin réel du fichier trouvé
                                filepath = os.path.join(local_path, file)
                                break
            except Exception as e:
                print(f"Erreur lors de la vérification du fichier: {e}")

            if file_exists:
                print("\n" + "=" * 60)
                print(f"ATTENTION: Le fichier '{video_title}' existe déjà !")
                print(f"Chemin: {filepath}")
                print("=" * 60)

                # Demander à l'utilisateur s'il souhaite remplacer le fichier
                while True:
                    choice = input("Voulez-vous remplacer ce fichier ? (o/n): ").lower()
                    if choice in ["o", "oui", "y", "yes"]:
                        print("Le fichier existant sera remplacé.")
                        try:
                            # Supprimer le fichier existant
                            os.remove(filepath)
                            print("Fichier existant supprimé.")
                            break  # Sortir de la boucle et continuer le téléchargement
                        except Exception as e:
                            print(f"Impossible de supprimer le fichier existant: {e}")
                            return
                    elif choice in ["n", "non", "no"]:
                        print("Téléchargement annulé.")
                        return
                    else:
                        print("Veuillez répondre par 'o' (oui) ou 'n' (non).")

            # Gérer différemment selon le type de téléchargement (vidéo ou audio)
            if download_type == "video":
                # Récupérer les formats disponibles pour la vidéo
                quality_options = get_available_video_qualities(info.get("formats", []))

                if not quality_options:
                    print(
                        "Aucun format vidéo disponible. Utilisation du format par défaut."
                    )
                    format_option = "best"
                else:
                    # Afficher les options de qualité disponibles
                    print("\nFormats vidéo disponibles:")
                    for i, option in enumerate(quality_options, 1):
                        print(f"  {i}. {option['display_name']}")

                    # Demander à l'utilisateur de choisir
                    choice = None
                    while choice is None:
                        try:
                            user_input = input(
                                "\nChoisissez la qualité (numéro) ou appuyez sur Entrée pour la meilleure qualité: "
                            )
                            if not user_input.strip():
                                choice = 1  # Meilleure qualité par défaut
                            else:
                                choice = int(user_input)
                                if choice < 1 or choice > len(quality_options):
                                    print(
                                        f"Veuillez entrer un nombre entre 1 et {len(quality_options)}"
                                    )
                                    choice = None
                        except ValueError:
                            print("Veuillez entrer un nombre valide")

                    # Récupérer le format choisi
                    selected_option = quality_options[choice - 1]
                    format_option = selected_option["format_string"]
                    print(f"\nTéléchargement en {selected_option['display_name']}...")

                # Format vidéo sélectionné

            else:  # Audio uniquement
                # Options de qualité audio
                audio_quality_options = [
                    {"bitrate": "192", "display_name": "Haute qualité (192 kbps)"},
                    {"bitrate": "128", "display_name": "Qualité standard (128 kbps)"},
                    {"bitrate": "96", "display_name": "Basse qualité (96 kbps)"},
                ]

                # Afficher les options de qualité audio
                print("\nFormats audio disponibles:")
                for i, option in enumerate(audio_quality_options, 1):
                    print(f"  {i}. {option['display_name']}")

                # Demander à l'utilisateur de choisir
                choice = None
                while choice is None:
                    try:
                        user_input = input(
                            "\nChoisissez la qualité audio (numéro) ou appuyez sur Entrée pour la meilleure qualité: "
                        )
                        if not user_input.strip():
                            choice = 1  # Meilleure qualité par défaut
                        else:
                            choice = int(user_input)
                            if choice < 1 or choice > len(audio_quality_options):
                                print(
                                    f"Veuillez entrer un nombre entre 1 et {len(audio_quality_options)}"
                                )
                                choice = None
                    except ValueError:
                        print("Veuillez entrer un nombre valide")

                # Récupérer la qualité audio choisie
                selected_audio_option = audio_quality_options[choice - 1]
                audio_bitrate = selected_audio_option["bitrate"]
                print(
                    f"\nTéléchargement audio en {selected_audio_option['display_name']}..."
                )

                # Pour l'audio, on utilise le meilleur format audio disponible
                format_option = "bestaudio/best"

                # Format audio sélectionné

            # Options pour le téléchargement
            ydl_opts = {
                "format": format_option,
                "outtmpl": os.path.join(local_path, "%(title)s.%(ext)s"),
                "ffmpeg_location": r"C:\ffmpeg\bin",
                "noplaylist": True,
                "nocheckcertificate": True,
                "ignoreerrors": True,
                "no_color": True,
                "geo_bypass": True,
                "geo_bypass_country": "US",
                "extractor_retries": 10,
                "socket_timeout": 60,
                "extractor_args": {
                    "youtube": {
                        "player_client": ["android", "web"],
                        "player_skip": ["js", "configs"],
                    }
                },
            }

            # Options spécifiques selon le type de téléchargement
            if download_type == "video":
                # Pour la vidéo, forcer la sortie en MP4
                ydl_opts["merge_output_format"] = "mp4"
            else:  # Audio uniquement
                # Pour l'audio, extraire l'audio et convertir en MP3
                ydl_opts["extractaudio"] = True
                ydl_opts["audioformat"] = "mp3"
                ydl_opts["audioquality"] = (
                    audio_bitrate  # Utiliser la qualité choisie par l'utilisateur
                )
                # Options supplémentaires pour la conversion audio
                ydl_opts["postprocessors"] = [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": audio_bitrate,
                    }
                ]

            # Pas besoin de forcer le remplacement car on a déjà supprimé le fichier existant si nécessaire

            if use_cookies:
                ydl_opts["cookiesfrombrowser"] = ("chrome", None, None, None)

            # Télécharger la vidéo avec le format choisi
            try:
                ydl_instance = yt_dlp.YoutubeDL(ydl_opts)
            except Exception:
                ydl_opts.pop("cookiesfrombrowser", None)
                ydl_instance = yt_dlp.YoutubeDL(ydl_opts)
            with ydl_instance as ydl:
                ydl.download([url])
                # Vérifier le fichier réel (au cas où le nom aurait été modifié par yt-dlp)
                file_ext = ".mp3" if download_type == "audio" else ".mp4"
                final_path = os.path.join(local_path, filename)

                # Si le fichier n'existe pas avec le nom prévu, chercher le fichier réel
                if not os.path.exists(final_path):
                    files = os.listdir(local_path)
                    matching_files = [
                        os.path.join(local_path, f)
                        for f in files
                        if f.endswith(file_ext)
                    ]

                    if matching_files:
                        newest_file = max(
                            matching_files, key=os.path.getctime, default=None
                        )
                        if newest_file:
                            final_path = newest_file
                    else:
                        # Si aucun fichier correspondant n'est trouvé, utiliser le dossier
                        print(
                            f"Aucun fichier {file_ext} récent trouvé, ouverture du dossier."
                        )
                        final_path = local_path

                print("Téléchargement terminé avec succès.")
                print(f"Fichier enregistré dans: {final_path}")

                # Ouvrir l'explorateur au bon endroit
                open_file_explorer(final_path)

    except Exception as e:
        print(f"Erreur avec yt-dlp : {str(e)}")
        print("Tentative avec méthode alternative...")

        # Méthode alternative avec subprocess
        try:
            # Options différentes selon le type de téléchargement
            if download_type == "video":
                # Demander à l'utilisateur de choisir la qualité vidéo pour la méthode alternative
                print("\nOptions de qualité vidéo pour la méthode alternative:")
                print("  1. Meilleure qualité (jusqu'à 1080p)")
                print("  2. Qualité moyenne (720p)")
                print("  3. Qualité basse (480p ou moins)")

                choice = None
                while choice is None:
                    try:
                        user_input = input(
                            "\nChoisissez la qualité (1-3) ou appuyez sur Entrée pour la meilleure qualité: "
                        )
                        if not user_input.strip():
                            choice = 1
                        else:
                            choice = int(user_input)
                            if choice < 1 or choice > 3:
                                print("Veuillez entrer un nombre entre 1 et 3")
                                choice = None
                    except ValueError:
                        print("Veuillez entrer un nombre valide")

                # Définir le format en fonction du choix
                format_option = (
                    "bestvideo[height<=1080]+bestaudio/best[height<=1080]"
                    if choice == 1
                    else (
                        "bestvideo[height<=720]+bestaudio/best[height<=720]"
                        if choice == 2
                        else "bestvideo[height<=480]+bestaudio/best[height<=480]"
                    )
                )

                cmd = [
                    sys.executable,
                    "-m",
                    "yt_dlp",
                    "--format",
                    format_option,
                    "--output",
                    os.path.join(local_path, "%(title)s.%(ext)s"),
                    "--ffmpeg-location",
                    r"C:\ffmpeg\bin",
                    "--no-playlist",
                    "--no-check-certificate",
                    "--geo-bypass",
                    "--merge-output-format",
                    "mp4",
                ]

            else:  # Audio uniquement
                # Demander à l'utilisateur de choisir la qualité audio pour la méthode alternative
                print("\nOptions de qualité audio pour la méthode alternative:")
                print("  1. Haute qualité (192 kbps)")
                print("  2. Qualité standard (128 kbps)")
                print("  3. Basse qualité (96 kbps)")

                choice = None
                while choice is None:
                    try:
                        user_input = input(
                            "\nChoisissez la qualité audio (1-3) ou appuyez sur Entrée pour la meilleure qualité: "
                        )
                        if not user_input.strip():
                            choice = 1
                        else:
                            choice = int(user_input)
                            if choice < 1 or choice > 3:
                                print("Veuillez entrer un nombre entre 1 et 3")
                                choice = None
                    except ValueError:
                        print("Veuillez entrer un nombre valide")

                # Définir la qualité audio en fonction du choix
                audio_quality = (
                    "192" if choice == 1 else ("128" if choice == 2 else "96")
                )

                cmd = [
                    sys.executable,
                    "-m",
                    "yt_dlp",
                    "--format",
                    "bestaudio/best",
                    "--output",
                    os.path.join(local_path, "%(title)s.%(ext)s"),
                    "--ffmpeg-location",
                    r"C:\ffmpeg\bin",
                    "--no-playlist",
                    "--no-check-certificate",
                    "--geo-bypass",
                    "--extract-audio",
                    "--audio-format",
                    "mp3",
                    "--audio-quality",
                    audio_quality,
                ]

            # Pas besoin de forcer le remplacement car on a déjà supprimé le fichier existant si nécessaire

            if use_cookies:
                cmd.extend(["--cookies-from-browser", "chrome"])

            cmd.append(url)

            print("\nTéléchargement avec la qualité sélectionnée...")
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                print(f"Erreur subprocess: {result.stderr}")
                raise Exception(result.stderr)

            # Essayer de trouver le fichier le plus récent avec la bonne extension
            try:
                file_ext = ".mp3" if download_type == "audio" else ".mp4"
                files = os.listdir(local_path)
                matching_files = [
                    os.path.join(local_path, f) for f in files if f.endswith(file_ext)
                ]

                if matching_files:
                    newest_file = max(matching_files, key=os.path.getctime)
                    print("Téléchargement terminé avec succès.")
                    print(f"Fichier enregistré dans: {newest_file}")
                    open_file_explorer(newest_file)
                else:
                    # Si aucun fichier correspondant n'est trouvé, ouvrir le dossier
                    print("Téléchargement terminé avec succès.")
                    print(f"Fichier enregistré dans le dossier: {local_path}")
                    open_file_explorer(local_path)
            except Exception as e:
                print(f"Erreur lors de la recherche du fichier: {e}")
                print("Téléchargement terminé avec succès.")
                print(f"Fichier enregistré dans le dossier: {local_path}")
                # En cas d'erreur, ouvrir simplement le dossier
                open_file_explorer(local_path)

        except Exception as e2:
            print(f"Toutes les tentatives ont échoué. Erreur finale : {str(e2)}")
            return


def download_instagram_video(url):
    """Télécharge une vidéo depuis Instagram avec yt-dlp"""
    print("\nAnalyse de la vidéo Instagram...")

    # Demander à l'utilisateur s'il souhaite télécharger la vidéo ou seulement l'audio
    print("\nQue souhaitez-vous télécharger ?")
    print("1. Vidéo (avec audio)")
    print("2. Audio uniquement (MP3)")

    download_type = None
    while download_type is None:
        try:
            choice = input(
                "\nEntrez votre choix (1-2) ou appuyez sur Entrée pour la vidéo: "
            )
            if not choice.strip():
                download_type = "video"
            else:
                choice = int(choice)
                if choice == 1:
                    download_type = "video"
                elif choice == 2:
                    download_type = "audio"
                else:
                    print("Veuillez entrer 1 ou 2")
        except ValueError:
            print("Veuillez entrer un nombre valide")

    # Déterminer le chemin de destination en fonction du type de téléchargement
    if download_type == "video":
        local_path = get_download_path("generic")
    else:  # audio
        local_path = get_download_path("generic_audio")

    # Add cookies file if available
    cookies_file = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "cookies.txt"
    )
    use_cookies = os.path.exists(cookies_file)

    try:
        # Options pour l'extraction des informations
        info_opts = {
            "noplaylist": True,
            "nocheckcertificate": True,
            "ignoreerrors": True,
            "no_color": True,
            "extractor_retries": 10,
            "socket_timeout": 60,
            "ffmpeg_location": r"C:\ffmpeg\bin",
            # Bypass Instagram "inappropriate content" filter
            "age_limit": 99,
        }

        # Use cookies file to avoid Chrome DB lock errors
        if use_cookies:
            info_opts["cookiefile"] = cookies_file

        # Extraire les informations de la vidéo sans télécharger
        with yt_dlp.YoutubeDL(info_opts) as ydl:
            print("Extraction des informations de la vidéo Instagram...")
            info = ydl.extract_info(url, download=False)

            # If info is None, Instagram blocked extraction
            if info is None:
                raise Exception(
                    "Instagram a bloqué l'extraction. "
                    "Contenu restreint ou cookies expirés."
                )

            video_title = info.get("title", "instagram_video")

            # Nettoyer le titre pour le nom de fichier
            clean_title = re.sub(r'[<>:"/\\|?*]', "_", video_title or "instagram_video")

            # Déterminer l'extension en fonction du type de téléchargement
            file_ext = ".mp3" if download_type == "audio" else ".mp4"
            filename = f"{clean_title}{file_ext}"
            filepath = os.path.join(local_path, filename)

            # Vérifier si le fichier existe déjà
            if os.path.exists(filepath):
                print("\n" + "=" * 60)
                print(f"ATTENTION: Le fichier '{video_title}' existe déjà !")
                print(f"Chemin: {filepath}")
                print("=" * 60)

                while True:
                    choice = input("Voulez-vous remplacer ce fichier ? (o/n): ").lower()
                    if choice in ["o", "oui", "y", "yes"]:
                        print("Le fichier existant sera remplacé.")
                        try:
                            os.remove(filepath)
                            print("Fichier existant supprimé.")
                            break
                        except Exception as e:
                            print(f"Impossible de supprimer le fichier existant: {e}")
                            return
                    elif choice in ["n", "non", "no"]:
                        print("Téléchargement annulé.")
                        return
                    else:
                        print("Veuillez répondre par 'o' (oui) ou 'n' (non).")

            # Options pour le téléchargement
            ydl_opts = {
                "format": "best" if download_type == "video" else "bestaudio/best",
                "outtmpl": os.path.join(local_path, "%(title)s.%(ext)s"),
                "ffmpeg_location": r"C:\ffmpeg\bin",
                "noplaylist": True,
                "nocheckcertificate": True,
                "ignoreerrors": True,
                "no_color": True,
                "extractor_retries": 10,
                "socket_timeout": 60,
                # Bypass Instagram "inappropriate content" filter
                "age_limit": 99,
            }

            # Options spécifiques selon le type de téléchargement
            if download_type == "video":
                # Pour la vidéo, forcer la sortie en MP4
                ydl_opts["merge_output_format"] = "mp4"
            else:  # Audio uniquement
                # Pour l'audio, extraire l'audio et convertir en MP3
                ydl_opts["extractaudio"] = True
                ydl_opts["audioformat"] = "mp3"
                ydl_opts["audioquality"] = "192"
                # Options supplémentaires pour la conversion audio
                ydl_opts["postprocessors"] = [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }
                ]

            # Use cookies file to avoid Chrome DB lock errors
            if use_cookies:
                ydl_opts["cookiefile"] = cookies_file

            # Télécharger la vidéo avec yt-dlp
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                print("\nTéléchargement Instagram en cours...")
                ydl.download([url])

                # Vérifier le fichier téléchargé
                file_ext = ".mp3" if download_type == "audio" else ".mp4"
                final_path = filepath

                # Si le fichier n'existe pas avec le nom prévu, chercher le fichier réel
                if not os.path.exists(final_path):
                    files = os.listdir(local_path)
                    matching_files = [
                        os.path.join(local_path, f)
                        for f in files
                        if f.endswith(file_ext)
                    ]

                    if matching_files:
                        newest_file = max(
                            matching_files, key=os.path.getctime, default=None
                        )
                        if newest_file:
                            final_path = newest_file

                print("Téléchargement Instagram terminé avec succès.")
                print(f"Fichier enregistré dans: {final_path}")
                open_file_explorer(final_path)

    except Exception as e:
        print(f"Erreur avec yt-dlp pour Instagram : {str(e)}")
        print("Tentative avec méthode alternative...")

        # Méthode alternative avec subprocess
        try:
            cmd = [
                sys.executable,
                "-m",
                "yt_dlp",
                "--format",
                "best" if download_type == "video" else "bestaudio/best",
                "--output",
                os.path.join(local_path, "%(title)s.%(ext)s"),
                "--ffmpeg-location",
                r"C:\ffmpeg\bin",
                "--no-playlist",
                "--no-check-certificate",
                "--age-limit",
                "99",
            ]

            if download_type == "video":
                cmd.extend(["--merge-output-format", "mp4"])
            else:
                cmd.extend(
                    [
                        "--extract-audio",
                        "--audio-format",
                        "mp3",
                        "--audio-quality",
                        "192",
                    ]
                )

            # Use cookies file to avoid Chrome DB lock errors
            if use_cookies:
                cmd.extend(["--cookies", cookies_file])

            cmd.append(url)

            print("\nTéléchargement Instagram avec subprocess...")
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                print(f"Erreur subprocess: {result.stderr}")
                raise Exception(result.stderr)

            # Essayer de trouver le fichier le plus récent avec la bonne extension
            try:
                file_ext = ".mp3" if download_type == "audio" else ".mp4"
                files = os.listdir(local_path)
                matching_files = [
                    os.path.join(local_path, f) for f in files if f.endswith(file_ext)
                ]

                if matching_files:
                    newest_file = max(matching_files, key=os.path.getctime)
                    print("Téléchargement Instagram terminé avec succès.")
                    print(f"Fichier enregistré dans: {newest_file}")
                    open_file_explorer(newest_file)
                else:
                    print("Téléchargement Instagram terminé avec succès.")
                    print(f"Fichier enregistré dans le dossier: {local_path}")
                    open_file_explorer(local_path)
            except Exception as e:
                print(f"Erreur lors de la recherche du fichier: {e}")
                print("Téléchargement Instagram terminé avec succès.")
                print(f"Fichier enregistré dans le dossier: {local_path}")
                open_file_explorer(local_path)

        except Exception as e2:
            print(
                f"Toutes les tentatives Instagram ont échoué. Erreur finale : {str(e2)}"
            )
            return


def download_local_audio(file_path):
    """Extrait l'audio d'un fichier vidéo local"""
    print("\nExtraction de l'audio depuis le fichier local...")

    if not os.path.exists(file_path):
        print("Le fichier n'existe pas.")
        return

    # Déterminer le chemin de sortie
    input_dir = os.path.dirname(file_path)
    input_filename = os.path.basename(file_path)
    name_without_ext = os.path.splitext(input_filename)[0]
    output_filename = name_without_ext + ".mp3"

    # Obtenir les dossiers de base
    downloads_folder = get_windows_downloads_folder()
    video_folder = os.path.join(downloads_folder, "Video")
    audio_folder = os.path.join(downloads_folder, "Audio")

    output_path = None
    if input_dir.startswith(video_folder):
        # Obtenir le sous-dossier relatif
        relative_path = os.path.relpath(input_dir, video_folder)
        if relative_path and not relative_path.startswith("."):
            audio_subfolder = os.path.join(audio_folder, relative_path)
            os.makedirs(audio_subfolder, exist_ok=True)
            output_path = os.path.join(audio_subfolder, output_filename)
        else:
            output_path = os.path.join(input_dir, output_filename)
    else:
        # Pas dans un dossier Video, mettre dans le même dossier
        output_path = os.path.join(input_dir, output_filename)

    # Vérifier si le fichier de sortie existe déjà
    if os.path.exists(output_path):
        print(f"\nLe fichier audio '{output_filename}' existe déjà.")
        while True:
            choice = input("Voulez-vous remplacer ce fichier ? (o/n): ").lower()
            if choice in ["o", "oui", "y", "yes"]:
                try:
                    os.remove(output_path)
                    print("Fichier existant supprimé.")
                    break
                except Exception as e:
                    print(f"Impossible de supprimer le fichier existant: {e}")
                    return
            elif choice in ["n", "non", "no"]:
                print("Extraction annulée.")
                return
            else:
                print("Veuillez répondre par 'o' (oui) ou 'n' (non).")

    # Extraire l'audio avec ffmpeg
    ffmpeg_path = r"C:\ffmpeg\bin\ffmpeg.exe"
    cmd = [
        ffmpeg_path,
        "-i",
        file_path,
        "-vn",
        "-acodec",
        "mp3",
        "-ab",
        "192k",
        output_path,
    ]

    try:
        print("Extraction en cours...")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            print("Extraction d'audio terminée.")
            print(f"Fichier enregistré dans: {output_path}")
            open_file_explorer(output_path)
        else:
            print("Échec de l'extraction audio.")
            print(f"Erreur: {result.stderr}")
            print(
                "Le fichier n'est peut-être pas un fichier vidéo dont on peut extraire l'audio."
            )
    except Exception as e:
        print(f"Erreur lors de l'extraction: {e}")


def download_rumble_video(url):
    """
    Download video from Rumble using yt-dlp CLI with browser impersonation
    Rumble requires --impersonate flag which works better via CLI than Python API
    """
    print("\nDownloading from Rumble...")
    print("Using browser impersonation to bypass anti-bot protection...")

    local_path = get_download_path("generic")

    # Build yt-dlp command with impersonation
    cmd = [
        sys.executable,
        "-m",
        "yt_dlp",
        "--impersonate",
        "chrome-116",  # Use specific Chrome version (Windows-10)
        # Don't specify format - let yt-dlp choose the best automatically
        "--output",
        os.path.join(local_path, "%(title)s.%(ext)s"),
        "--ffmpeg-location",
        r"C:\ffmpeg\bin",
        "--no-playlist",
        "--merge-output-format",
        "mp4",
        url,
    ]

    # Add cookies if available
    cookies_file = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "cookies.txt"
    )
    if os.path.exists(cookies_file):
        cmd.extend(["--cookies-from-browser", "chrome"])
        print(f"Using cookies: {cookies_file}")

    try:
        print("\nStarting download...")
        print("(You can press Ctrl+C to stop)")

        # Run yt-dlp command
        result = subprocess.run(
            cmd,
            check=False,
            text=True,
            capture_output=False,  # Show output in real-time
        )

        if result.returncode == 0:
            print("\n✅ Download completed successfully!")

            # Find the downloaded file
            files = [f for f in os.listdir(local_path) if f.endswith(".mp4")]
            if files:
                latest_file = os.path.join(
                    local_path,
                    max(
                        files,
                        key=lambda x: os.path.getctime(os.path.join(local_path, x)),
                    ),
                )
                print(f"File: {latest_file}")

                # Get file size
                size_mb = os.path.getsize(latest_file) / (1024 * 1024)
                print(f"Size: {size_mb:.2f} MB")

                # Open file explorer
                open_file_explorer(latest_file)
        else:
            print(f"\n❌ Download failed with exit code: {result.returncode}")
            print("Please check the error messages above.")

    except KeyboardInterrupt:
        print("\n\n⚠️  Download interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()


def download_protected_site_video(url, site_type, download_type="video"):
    """
    Download video from protected sites using yt-dlp specialized handling
    Uses temporary directory to avoid yt-dlp cache issues
    FIXED: Forces video track selection from DASH manifests
    """
    print(f"\nDownloading from protected site: {site_type}")

    # Determine final destination path
    local_path = get_download_path("generic")

    # Create TEMPORARY directory to avoid yt-dlp cache

    temp_dir = None
    try:
        # Create unique temporary directory
        temp_dir = tempfile.mkdtemp(prefix=f"ytdl_{site_type}_")
        print(f"Using temporary directory: {temp_dir}")

        # Add cookies file if available
        cookies_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "cookies.txt"
        )
        use_cookies = os.path.exists(cookies_file)

        # CRITICAL FIX: Use format IDs directly from DASH manifest
        # This bypasses yt-dlp's format detection issues
        # Strategy: Download best video + best French audio, let ffmpeg merge
        format_selector = (
            # Method 1: Try explicit video+audio selection with language preference
            "bv*[ext=mp4]+ba[language=fr]/bv*+ba[language=fr]/"
            # Method 2: Best video with any audio, prefer French
            "bv*[ext=mp4]+ba/bv*+ba/"
            # Method 3: Any video+audio combo
            "b[ext=mp4]/b/"
            # Method 4: Last resort - best available
            "best"
        )

        if download_type == "audio":
            format_selector = "bestaudio/best"
            local_path = get_download_path("generic_audio")

        # Options for protected sites - Enhanced DASH handling
        ydl_opts = {
            "format": format_selector,
            "noplaylist": True,
            "nocheckcertificate": True,
            "ignoreerrors": False,
            "no_color": True,
            "geo_bypass": True,
            "geo_bypass_country": "FR",
            "extractor_retries": 10,
            "socket_timeout": 60,
            "file_access_retries": 10,
            "fragment_retries": 10,
            "skip_unavailable_fragments": False,
            "keep_fragments": False,
            "extract_flat": False,
            "write_info_json": False,
            "write_sub": False,
            "write_automatic_sub": False,
            "ignore_subtitles": True,
            "writethumbnail": False,
            "write_description": False,
            "write_duration": False,
            "write_chapters": False,
            "write_annotations": False,
            "ffmpeg_location": r"C:\ffmpeg\bin",
            "outtmpl": os.path.join(temp_dir, "%(title)s.%(ext)s"),
            "nooverwrites": True,
            "merge_output_format": "mp4",
            # HTTP headers to bypass 403 errors (especially for Rumble)
            "http_headers": {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept": (
                    "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
                ),
                "Accept-Language": "en-us,en;q=0.5",
                "Sec-Fetch-Mode": "navigate",
            },
            # CRITICAL: Enhanced post-processing for DASH
            "postprocessors": [
                {
                    "key": "FFmpegVideoConvertor",
                    "preferedformat": "mp4",
                },
            ],
            "postprocessor_args": {
                # Copy video stream, encode audio to AAC
                "ffmpeg": ["-c:v", "copy", "-c:a", "aac", "-b:a", "192k"]
            },
            # CRITICAL FIX: Force yt-dlp to list ALL formats including video
            "listformats": False,  # Don't just list, actually try to download
            "format_sort": [
                "res",
                "lang:fr",
                "proto:https",
            ],  # Prefer higher res, French audio
            "verbose": True,
            # IMPORTANT: Disable any format filtering that might hide video tracks
            "youtube_include_dash_manifest": True,
            "youtube_include_hls_manifest": True,
        }

        # Override options for audio-only download
        if download_type == "audio":
            ydl_opts["merge_output_format"] = "mp3"
            ydl_opts["postprocessors"] = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ]
            ydl_opts.pop("postprocessor_args", None)

        # Add site-specific options
        if site_type == "m6":
            ydl_opts.update(
                {
                    "extractor_args": {
                        "m6": {
                            "player_client": ["android", "web"],
                        },
                        # CRITICAL: Force generic extractor to parse DASH properly
                        "generic": {
                            "dash_manifest_url": True,
                        },
                    },
                }
            )
        elif site_type == "tf1":
            ydl_opts.update(
                {
                    "extractor_args": {
                        "tf1": {
                            "player_client": ["android", "web"],
                        },
                        "generic": {
                            "dash_manifest_url": True,
                        },
                    },
                }
            )
        elif site_type == "francetv":
            ydl_opts.update(
                {
                    "extractor_args": {
                        "francetv": {
                            "player_client": ["android", "web"],
                        },
                        "generic": {
                            "dash_manifest_url": True,
                        },
                    },
                }
            )
        elif site_type == "rumble":
            # Rumble requires browser impersonation to bypass 403 errors
            # This makes yt-dlp simulate a real Chrome browser
            print("Using Rumble-optimized settings with browser impersonation...")
            ydl_opts["impersonate"] = "chrome"  # Simulate Chrome browser

        if use_cookies:
            ydl_opts["cookiesfrombrowser"] = ("chrome", None, None, None)

        # DIAGNOSTIC: First, list all available formats
        print("\n" + "=" * 60)
        print("DIAGNOSTIC: Analyzing available formats...")
        print("=" * 60)

        with yt_dlp.YoutubeDL(
            {"listformats": True, "cookiesfrombrowser": ("chrome", None, None, None)}
        ) as ydl_list:
            try:
                info = ydl_list.extract_info(url, download=False)
                if info is None:
                    raise Exception("Extraction des formats impossible.")
                formats = info.get("formats", [])

                print(f"\nTotal formats found: {len(formats)}")

                # Separate video and audio
                video_formats = [
                    f
                    for f in formats
                    if f.get("vcodec") != "none" and f.get("vcodec") is not None
                ]
                audio_formats = [
                    f
                    for f in formats
                    if f.get("acodec") != "none" and f.get("vcodec") == "none"
                ]
                combined_formats = [
                    f
                    for f in formats
                    if f.get("vcodec") != "none" and f.get("acodec") != "none"
                ]

                print(f"Video-only tracks: {len(video_formats)}")
                print(f"Audio-only tracks: {len(audio_formats)}")
                print(f"Combined (video+audio) tracks: {len(combined_formats)}")

                # Display audio languages
                audio_languages = set()
                for fmt in audio_formats:
                    lang = fmt.get("language") or fmt.get("lang", "unknown")
                    audio_languages.add(lang)
                print(f"Audio languages: {', '.join(sorted(audio_languages))}")

                # CRITICAL: If no video-only tracks, try to use combined formats
                if len(video_formats) == 0 and len(combined_formats) > 0:
                    print("\n⚠ WARNING: No separate video tracks found!")
                    print("Using combined video+audio formats instead...")
                    # Update format selector for combined formats
                    format_selector = "best[ext=mp4]/best"
                    ydl_opts["format"] = format_selector
                elif len(video_formats) == 0:
                    print("\n❌ ERROR: No video tracks found at all!")
                    print("The video might be:")
                    print("  1. Geo-blocked despite using French IP")
                    print("  2. DRM-protected (undownloadable)")
                    print("  3. Incorrectly parsed by yt-dlp")
                    print("\nTrying alternative extraction method...")

                    # FALLBACK: Try to extract DASH manifest URL directly
                    try:
                        manifest_url = info.get("manifest_url") or info.get("url")
                        if manifest_url and ".mpd" in manifest_url:
                            print(f"\nFound DASH manifest: {manifest_url[:80]}...")
                            print("Attempting direct manifest parsing...")
                            # This will force yt-dlp to re-parse the manifest
                            ydl_opts["format"] = "bestvideo+bestaudio/best"
                    except Exception as e:
                        print(f"Manifest extraction failed: {e}")

                # Show detailed format info for debugging
                if video_formats:
                    print("\n📹 Video formats available:")
                    for fmt in video_formats[:3]:  # Show first 3
                        height = fmt.get("height", "?")
                        fps = fmt.get("fps", "?")
                        vcodec = fmt.get("vcodec", "?")
                        filesize = fmt.get("filesize") or fmt.get("filesize_approx", 0)
                        size_mb = filesize / (1024 * 1024) if filesize else 0
                        print(f"  - {height}p @ {fps}fps ({vcodec}) - ~{size_mb:.1f}MB")

                if audio_formats:
                    print("\n🔊 Audio formats available:")
                    for fmt in audio_formats[:3]:
                        lang = fmt.get("language", "?")
                        acodec = fmt.get("acodec", "?")
                        bitrate = fmt.get("tbr") or fmt.get("abr", "?")
                        print(f"  - {lang} ({acodec}) @ {bitrate}kbps")

            except Exception as e:
                print(f"⚠ Format analysis failed: {e}")
                print("Proceeding with download attempt anyway...")

        print("\n" + "=" * 60)
        print("Starting download...")
        print("=" * 60)

        # Now proceed with actual download
        try:
            ydl_instance = yt_dlp.YoutubeDL(ydl_opts)
        except Exception:
            ydl_opts.pop("cookiesfrombrowser", None)
            ydl_instance = yt_dlp.YoutubeDL(ydl_opts)
        with ydl_instance as ydl:
            # Extract info for the video title
            info = ydl.extract_info(url, download=False)
            if info is None:
                raise Exception("Extraction impossible pour ce site.")
            video_title = info.get("title", f"video_{site_type}")

            print(f"\nDownloading: {video_title}")
            print(f"Format: {format_selector}")
            ydl.download([url])

            # Find the downloaded file in temp directory
            temp_files = [
                f
                for f in os.listdir(temp_dir)
                if f.endswith((".mp4", ".mkv", ".webm", ".m4a", ".mp3"))
            ]

            if temp_files:
                # Find the most recent file
                temp_file_path = os.path.join(
                    temp_dir,
                    max(
                        temp_files,
                        key=lambda x: os.path.getctime(os.path.join(temp_dir, x)),
                    ),
                )

                downloaded_filename = os.path.basename(temp_file_path)
                clean_filename_from_temp = downloaded_filename

                # Remove numbered suffixes like (1), (2), etc.
                pattern = r"\s*\(\d+\)(\.\w+)$"
                if re.search(pattern, clean_filename_from_temp):
                    clean_filename_from_temp = re.sub(
                        pattern, r"\1", clean_filename_from_temp
                    )
                    print(
                        f"Cleaned filename: {downloaded_filename} -> "
                        f"{clean_filename_from_temp}"
                    )

                # Ensure correct extension based on download type
                current_ext = os.path.splitext(clean_filename_from_temp)[1].lower()
                expected_ext = ".mp3" if download_type == "audio" else ".mp4"
                if current_ext != expected_ext:
                    base_name = os.path.splitext(clean_filename_from_temp)[0]
                    clean_filename_from_temp = base_name + expected_ext

                # Create final clean filename
                clean_final_filename = re.sub(
                    r'[<>:"/\\|?*]', "_", clean_filename_from_temp
                )
                final_path = os.path.join(local_path, clean_final_filename)

                # Get file size
                file_size_mb = os.path.getsize(temp_file_path) / (1024 * 1024)
                print(
                    f"\n📦 Downloaded file: {downloaded_filename} ({file_size_mb:.2f} MB)"
                )

                # Check if it's video or just audio
                file_ext = os.path.splitext(temp_file_path)[1].lower()
                if file_ext == ".m4a":
                    print("\n⚠ WARNING: Downloaded file is AUDIO ONLY (.m4a)")
                    print("This means video tracks were not available or not selected.")
                    print("Possible reasons:")
                    print("  1. Video is DRM-protected")
                    print("  2. DASH manifest parsing failed")
                    print("  3. Geo-blocking despite French IP")
                else:
                    print(f"\n✅ Downloaded file appears to be VIDEO ({file_ext})")

                # Validate the download
                is_valid, message = validate_downloaded_file(
                    temp_file_path, expected_min_size_mb=3
                )

                if is_valid or file_ext == ".m4a":  # Accept audio files for now
                    # Check if file exists at destination
                    if os.path.exists(final_path):
                        try:
                            os.remove(final_path)
                            print("Removed existing file at destination")
                        except Exception as e:
                            print(f"Warning: Cannot remove existing file: {e}")

                    # Move file from temp to final destination
                    shutil.move(temp_file_path, final_path)

                    print("\n" + "=" * 60)
                    if file_ext == ".m4a":
                        print("[PARTIAL SUCCESS] Audio downloaded (video unavailable)")
                    else:
                        print("[SUCCESS] Download completed successfully!")
                    print("=" * 60)
                    print(f"File: {final_path}")
                    print(f"Size: {file_size_mb:.2f} MB")
                    print("=" * 60)

                    open_file_explorer(final_path)
                else:
                    print(f"\n⚠ File validation failed: {message}")
                    failed_filename = re.sub(
                        r'[<>:"/\\|?*]', "_", f"{video_title}_FAILED.mp4"
                    )
                    final_path = os.path.join(local_path, failed_filename)
                    shutil.move(temp_file_path, final_path)
                    print(f"Saved for inspection: {final_path}")
                    open_file_explorer(final_path)
            else:
                print("\n❌ ERROR: No file found in temporary directory!")
                print("Download completely failed.")

    except Exception as e:
        error_msg = str(e)
        print(f"\n❌ ERROR: {error_msg}")

        # Handle specific yt-dlp errors
        if "Unknown algorithm ID" in error_msg:
            print("\n⚠️  YT-DLP VERSION ISSUE DETECTED")
            print(
                "This error indicates that your yt-dlp version doesn't support this site."
            )
            print("Please update yt-dlp:")
            print("  Run: uv pip install --upgrade yt-dlp")
            print("\nAlternatively, the site might be blocking downloads.")

        import traceback

        print("\nFull traceback:")
        traceback.print_exc()

    finally:
        # Cleanup
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
                print("\n🧹 Cleaned up temp directory")
            except Exception as e:
                print(f"Warning: Cleanup failed: {e}")


def download_generic_video_with_fallback(url):
    """
    Download video from generic URL with fallback to yt-dlp if generic method fails
    OPTIMIZED: Skip generic method for protected sites
    """
    print("\nQue souhaitez-vous télécharger ?")
    print("1. Vidéo (avec audio)")
    print("2. Audio uniquement (MP3)")
    download_type = None
    while download_type is None:
        choice = input(
            "\nEntrez votre choix (1-2) ou appuyez sur Entrée pour la vidéo: "
        ).strip()
        if not choice or choice == "1":
            download_type = "video"
        elif choice == "2":
            download_type = "audio"
        else:
            print("Choix invalide.")
    # Check if it's a protected site FIRST - don't waste time with generic method
    site_type = detect_protected_sites(url)

    if site_type != "generic":
        print(f"\nProtected site detected: {site_type} ({url})")
        print("Skipping generic method - using specialized yt-dlp...")

        # Use specialized handler for each protected site
        try:
            if site_type == "rumble":
                # Rumble requires special CLI-based impersonation
                download_rumble_video(url)
            else:
                # Other protected sites use the standard handler
                download_protected_site_video(url, site_type, download_type)
        except Exception as e:
            print(f"Download failed for protected site: {str(e)}")
            print("Please check:")
            print("1. The URL is valid and accessible")
            print("2. Cookies are properly configured")
            print("3. Internet connection is stable")
        return

    # Only use generic method for truly generic/unprotected sites
    print("\nAttempting download with generic method...")
    # Determine validation path based on download type
    local_path = get_download_path(
        "generic_audio" if download_type == "audio" else "generic"
    )

    try:
        # Try the original generic download method
        download_generic_video(url, download_type=download_type)

        # Check if the downloaded file is valid
        valid_exts = (".mp3",) if download_type == "audio" else (".mp4",)
        files = [f for f in os.listdir(local_path) if f.endswith(valid_exts)]
        if files:
            latest_file = os.path.join(
                local_path,
                max(files, key=lambda x: os.path.getctime(os.path.join(local_path, x))),
            )
            is_valid, message = validate_downloaded_file(latest_file)

            if is_valid:
                print(f"Generic download successful: {message}")
                return
            else:
                print(f"Generic download failed validation: {message}")
                print("Falling back to yt-dlp...")
        else:
            print("No file found after generic download, falling back to yt-dlp...")

    except Exception as e:
        print(f"Generic download failed: {str(e)}")
        print("Falling back to yt-dlp...")

    # Fallback to yt-dlp for generic sites that failed
    try:
        print("\nAttempting download with yt-dlp...")
        site_type = detect_protected_sites(url)
        download_protected_site_video(url, site_type, download_type)
    except Exception as e:
        print(f"All download methods failed. Final error: {str(e)}")
        print("Please check:")
        print("1. The URL is valid and accessible")
        print("2. Cookies are properly configured")
        print("3. Internet connection is stable")


def download_generic_video(url, download_type="video"):
    """Download from a generic URL. Uses yt-dlp for audio extraction if needed."""
    if download_type == "audio":
        print("\nAudio-only download from generic URL (via yt-dlp)...")
        local_path = get_download_path("generic_audio")

        # Snapshot existing files before download to detect new ones reliably
        before_files = set(os.listdir(local_path))

        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": os.path.join(local_path, "%(title)s.%(ext)s"),
            "ffmpeg_location": r"C:\ffmpeg\bin",
            "noplaylist": True,
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
        }
        try:
            start_time = time.time()
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if info is None:
                    raise Exception("Could not extract audio info.")
            elapsed = time.time() - start_time

            # Detect new files created during download
            after_files = set(os.listdir(local_path))
            new_files = after_files - before_files

            # Separate MP3s from residual source files (webm, m4a, etc.)
            new_mp3s = [f for f in new_files if f.lower().endswith(".mp3")]
            residual = [f for f in new_files if not f.lower().endswith(".mp3")]

            # Clean up residual source files left by FFmpegExtractAudio
            for leftover in residual:
                leftover_path = os.path.join(local_path, leftover)
                try:
                    os.remove(leftover_path)
                    print(f"Cleaned up source file: {leftover}")
                except Exception as cleanup_err:
                    print(f"Warning: could not remove {leftover}: {cleanup_err}")

            if new_mp3s:
                # Pick the most recently created MP3
                mp3_file = max(
                    new_mp3s,
                    key=lambda f: os.path.getctime(os.path.join(local_path, f)),
                )
                mp3_path = os.path.join(local_path, mp3_file)
                size_mb = os.path.getsize(mp3_path) / (1024 * 1024)

                print(f"\nTéléchargement terminé avec succès : {mp3_file}")
                print(f"Fichier enregistré dans: {mp3_path}")
                print(f"Taille : {size_mb:.2f} MB")
                print(f"Temps total : {elapsed:.2f} secondes")

                # Open Explorer with the file selected (same as YouTube behaviour)
                open_file_explorer(mp3_path)
            else:
                print("Warning: MP3 file not found after conversion.")
        except Exception as e:
            print(f"Audio download failed: {e}")
        return

    print("\nTéléchargement de la vidéo depuis une URL générique...")
    local_path = get_download_path("generic")
    # Note: get_download_path crée déjà le dossier s'il n'existe pas

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36"
        }

        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.content, "html.parser")

        title = soup.find("title")
        video_name = (title.text if title else "video") + ".mp4"
        video_name = re.sub(r'[<>:"/\\|?*]', "_", video_name)
        video_path = os.path.join(local_path, video_name)

        if os.path.exists(video_path):
            print(
                f"\nAttention: Le fichier '{video_name}' existe déjà dans '{local_path}'."
            )
            while True:
                choice = input("Voulez-vous remplacer ce fichier ? (o/n): ").lower()
                if choice in ["o", "oui", "y", "yes"]:
                    try:
                        os.remove(video_path)
                        print(f"Fichier existant supprimé: {video_name}")
                        break
                    except Exception as e:
                        print(f"Impossible de supprimer le fichier existant: {e}")
                        return
                elif choice in ["n", "non", "no"]:
                    print("Téléchargement annulé.")
                    return
                else:
                    print("Veuillez répondre par 'o' (oui) ou 'n' (non).")

        # Chercher toutes les sources vidéo possibles
        video_sources = []

        # Chercher dans les balises JSON-LD
        script_tags = soup.find_all("script", type="application/ld+json")
        for script in script_tags:
            try:
                if script.string:
                    json_content = json.loads(script.string)
                    if isinstance(json_content, dict):
                        if "contentUrl" in json_content:
                            video_sources.append(
                                {
                                    "url": json_content["contentUrl"],
                                    "quality": "unknown",
                                }
                            )
                        if "encodingFormat" in json_content:
                            for format_info in json_content.get("encodingFormat", []):
                                if isinstance(format_info, dict):
                                    url = format_info.get("contentUrl")
                                    quality = format_info.get("quality", "unknown")
                                    if url:
                                        video_sources.append(
                                            {"url": url, "quality": quality}
                                        )
            except Exception:
                continue

        # Chercher dans les balises vidéo et source
        video_tag = soup.find("video")
        if video_tag:
            if hasattr(video_tag, "get"):
                src = video_tag.get("src")
                if src:
                    video_sources.append({"url": src, "quality": "unknown"})

                source_tags = video_tag.find_all("source")
                for source in source_tags:
                    if hasattr(source, "get"):
                        src = source.get("src")
                        if src:
                            quality = source.get("size", "unknown")
                            video_sources.append({"url": src, "quality": quality})

        if not video_sources:
            print("Aucune source vidéo trouvée dans la page.")
            return

        # Sélectionner la meilleure qualité disponible
        preferred_qualities = ["1080", "720", "480"]
        selected_url = None
        selected_quality = None

        for preferred_quality in preferred_qualities:
            for source in video_sources:
                if str(preferred_quality) in str(source["quality"]):
                    selected_url = source["url"]
                    selected_quality = preferred_quality
                    break
            if selected_url:
                break

        if not selected_url:
            selected_url = video_sources[0]["url"]
            selected_quality = "meilleure disponible"

        print(f"Téléchargement en qualité {selected_quality}...")

        response = requests.get(selected_url, headers=headers, stream=True)
        total_size = int(response.headers.get("content-length", 0))

        block_size = 1024 * 1024  # 1 MB

        with open(video_path, "wb") as f:
            try:
                with tqdm(
                    total=total_size, unit="B", unit_scale=True, desc=video_name
                ) as pbar:
                    start_time = time.time()
                    bytes_downloaded = 0

                    for data in response.iter_content(block_size):
                        if not data:
                            break
                        f.write(data)
                        bytes_downloaded += len(data)
                        pbar.update(len(data))

                        elapsed_time = time.time() - start_time
                        if elapsed_time > 0:
                            speed = bytes_downloaded / (
                                1024 * 1024 * elapsed_time
                            )  # MB/s
                            pbar.set_postfix(speed=f"{speed:.2f} MB/s")

                print(f"\nTéléchargement terminé avec succès : {video_name}")
                print(f"Fichier enregistré dans: {video_path}")
                print(f"Taille : {total_size / (1024 * 1024):.2f} MB")
                print(f"Temps total : {time.time() - start_time:.2f} secondes")
                # NOTE: Not opening explorer here to avoid opening folders with temporary files
                # The fallback method will open explorer only if the final download succeeds

            except Exception as e:
                print(f"Erreur pendant le téléchargement : {e}")
                # Supprime le fichier partiellement téléchargé en cas d'erreur
                if os.path.exists(video_path):
                    os.remove(video_path)
                raise

    except Exception as e:
        print(f"Erreur lors du téléchargement générique : {str(e)}")
        # Nettoyer en cas d'erreur
        if "video_path" in locals() and os.path.exists(video_path):
            os.remove(video_path)


def main():
    print("\n===== Début du processus =====\n")

    # Auto-update yt-dlp at startup
    update_yt_dlp()

    # Verify/export cookies if needed
    check_and_export_cookies()

    result = get_url_from_clipboard()
    if not result:
        return

    type_url, url = result
    print(f"\nTraitement de la vidéo depuis l'URL : {url}")

    try:
        if type_url == "youtube":
            download_youtube_video(url)
        elif type_url == "instagram":
            download_instagram_video(url)
        elif type_url == "local":
            download_local_audio(url)
        else:
            # Vérifier d'abord si c'est un site KVS
            if detect_kvs_sites(url):
                download_kvs_video(url)
            else:
                # Use the new fallback method for generic URLs
                download_generic_video_with_fallback(url)
    except Exception as e:
        print(f"Erreur lors du traitement : {e}")

    print("\n===== Processus terminé =====")


if __name__ == "__main__":
    main()
