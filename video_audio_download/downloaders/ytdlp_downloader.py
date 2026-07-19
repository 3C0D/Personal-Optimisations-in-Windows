"""
Universal yt-dlp downloader.
Single class that handles ALL sites (YouTube, Instagram, protected sites, generic).
yt-dlp natively supports 1800+ sites — we leverage that instead of reimplementing
per-site logic.
"""

import os
import re
import shutil
import sys
import tempfile
import subprocess
import json
import html

import requests
import yt_dlp

from core.config import (
    FFMPEG_PATH,
    MAX_VIDEO_HEIGHT,
    DEFAULT_AUDIO_BITRATE,
    SOCKET_TIMEOUT,
    EXTRACTOR_RETRIES,
    OUTPUT_DIR,
    PROTECTED_SITES,
    DEFAULT_HEADERS,
)
from core.cookies import get_cookies_file
from core.file_utils import (
    clean_filename,
    find_latest_file,
    validate_downloaded_file,
    open_file_explorer,
    check_file_exists,
    extract_audio_from_file,
)
from core.ui import ask_replace_file, ask_extract_audio_from_existing, ask_video_quality
from urllib.parse import urlparse, parse_qs


class YtdlpDownloader:
    """Universal downloader powered by yt-dlp."""

    def __init__(self):
        self.cookies_file = get_cookies_file()
        os.makedirs(OUTPUT_DIR, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def download(self, url, download_type="video"):
        """
        Download video or audio from any supported URL.

        Args:
            url: URL to download from
            download_type: "video" or "audio"

        Returns:
            str or None: Path to downloaded file, or None on failure
        """
        # Normalize URL to get direct link for BBC Reel playlist pages,
        # then get the expected id for verification
        url = self._normalize_url(url)
        expected_id = self._get_expected_video_id(url)
        site_type = self._detect_site_type(url)
        print(f"\nTraitement: {url}")
        if site_type != "generic":
            print(f"Site détecté: {site_type}")

        # Build yt-dlp options
        opts = self._build_options(url, download_type, site_type)

        # First pass: extract info without downloading
        info = self._extract_info(url, site_type)
        if info is None:
            print("Impossible d'extraire les informations de la vidéo.")
            print("Tentative de téléchargement direct...")
            return self._direct_download(url, download_type, opts)

        # Verify extracted video matches the expected ID (for BBC Reel playlist pages)
        if expected_id and info.get("id") != expected_id:
            print(
                f"\nATTENTION : la vidéo extraite (id={info.get('id')}) ne correspond pas "
                f"à celle demandée (id={expected_id})."
            )
            print(
                "Cette page contient un carrousel et yt-dlp a extrait la mauvaise vidéo. "
                "Ouvre la vidéo souhaitée directement dans le player BBC (clique dessus "
                "pour qu'elle devienne la vidéo principale) puis recopie l'URL affichée "
                "à ce moment-là, plutôt que l'URL de la page playlist."
            )
            return None

        title = info.get("title", "video")
        print(f"Vidéo détectée : {title}")
        ext = ".mp3" if download_type == "audio" else ".mp4"

        # Check if file already exists
        existing = check_file_exists(OUTPUT_DIR, title, ext)
        if existing:
            # If user wants audio and a video already exists, offer extraction
            if download_type == "audio":
                video_existing = check_file_exists(OUTPUT_DIR, title, ".mp4")
                if video_existing and ask_extract_audio_from_existing(video_existing):
                    result = extract_audio_from_file(video_existing)
                    if result:
                        open_file_explorer(result)
                        return result

            if not ask_replace_file(existing):
                print("Téléchargement annulé.")
                return None
            try:
                os.remove(existing)
                print("Fichier existant supprimé.")
            except Exception as e:
                print(f"Impossible de supprimer le fichier existant: {e}")
                return None
        else:
            # Even if downloading audio, check if a video version exists
            if download_type == "audio":
                video_existing = check_file_exists(OUTPUT_DIR, title, ".mp4")
                if video_existing and ask_extract_audio_from_existing(video_existing):
                    result = extract_audio_from_file(video_existing)
                    if result:
                        open_file_explorer(result)
                        return result

        # Select quality for video downloads (YouTube mainly)
        # Do NOT override format for French protected sites (m6, tf1, francetv)
        # as they require specific language constraints in the format string
        if download_type == "video" and info.get("formats") and site_type not in ("m6", "tf1", "francetv"):
            quality_opts = self._get_quality_options(info["formats"])
            if quality_opts:
                selected = ask_video_quality(quality_opts)
                if selected:
                    opts["format"] = selected["format_string"]
                    print(f"\nTéléchargement en {selected['display_name']}...")

        # Download
        return self._do_download(url, download_type, opts, site_type)

    # ------------------------------------------------------------------
    # Site detection
    # ------------------------------------------------------------------

    def _get_canonical_id_from_page(self, html_text, vpid):
        """
        BBC Reel embeds the full playlist state as HTML-escaped JSON inside
        <script id="initial-data" data-json="...">. Each item there has
        smpData.items[0].versionID (the VPID from the URL) and clipPID (the
        canonical id used in /reel/video/{id} URLs), in the same object. This
        replaces the previous regex-proximity guess, which could pick up an
        unrelated p0XXXXXXX id (e.g. a thumbnail image id) that happened to sit
        near the VPID in the raw HTML text instead of reading the real mapping.
        """
        match = re.search(
            r'<script[^>]*\bid="initial-data"[^>]*\bdata-json="([^"]*)"', html_text
        )
        if not match:
            return None

        raw_json = html.unescape(match.group(1))
        try:
            data = json.loads(raw_json)
        except json.JSONDecodeError:
            return None

        items = data.get("initData", {}).get("items", [])
        for item in items:
            smp_items = item.get("smpData", {}).get("items", [])
            if any(smp.get("versionID") == vpid for smp in smp_items):
                return item.get("clipPID")

        return None

    def _normalize_url(self, url):
        """
        BBC Reel playlist URLs carry a VPID (version id) in ?vpid=, but the
        site's carousel links use the clip's canonical PID instead, which is
        a different but related id (BBC's own PID/VPID distinction). Fetch
        the raw page and read the canonical PID from the embedded initial-data
        JSON, matched by field (versionID -> clipPID) rather than by text
        proximity, so we can build a working direct URL.
        """
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        if domain not in ("bbc.com", "www.bbc.com") or "/reel/playlist" not in parsed.path:
            return url

        vpid = parse_qs(parsed.query).get("vpid", [None])[0]
        if not vpid:
            return url

        try:
            response = requests.get(url, headers=DEFAULT_HEADERS, timeout=SOCKET_TIMEOUT)
            response.raise_for_status()

            canonical_id = self._get_canonical_id_from_page(response.text, vpid)
            if canonical_id:
                print(f"Playlist BBC Reel détectée, VPID {vpid} -> ID canonique {canonical_id}")
                return f"https://www.bbc.com/reel/video/{canonical_id}"

            print(f"Aucun ID canonique trouvé pour le VPID {vpid} dans les données de la page.")

        except Exception as e:
            print(f"Résolution BBC Reel échouée : {e}")

        return url

    def _get_expected_video_id(self, url):
        """
        Return the canonical PID from a BBC Reel URL for verification.
        For playlist URLs, extracts the canonical PID from the page.
        For direct URLs, returns the PID from the path.
        """
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        if domain not in ("bbc.com", "www.bbc.com"):
            return None

        # For direct video URLs, extract PID from path
        match = re.search(r"/reel/video/([a-z0-9]+)", parsed.path)
        if match:
            return match.group(1)

        # For playlist URLs, we need to resolve the canonical PID from VPID
        if "/reel/playlist" in parsed.path:
            vpid = parse_qs(parsed.query).get("vpid", [None])[0]
            if not vpid:
                return None
            try:
                response = requests.get(url, headers=DEFAULT_HEADERS, timeout=SOCKET_TIMEOUT)
                response.raise_for_status()
                return self._get_canonical_id_from_page(response.text, vpid)
            except Exception:
                return None

        return None

    def _detect_site_type(self, url):
        """Detect site type from URL domain."""
        domain = urlparse(url).netloc.lower()

        for site_domain, site_type in PROTECTED_SITES.items():
            if domain == site_domain or domain.endswith("." + site_domain):
                return site_type

        # YouTube detection
        if any(
            d in domain
            for d in ("youtube.com", "youtu.be", "youtube-nocookie.com")
        ):
            return "youtube"

        # Instagram detection
        if "instagram.com" in domain:
            return "instagram"

        return "generic"

    # ------------------------------------------------------------------
    # Options building
    # ------------------------------------------------------------------

    def _build_options(self, url, download_type, site_type):
        """Build yt-dlp options dict based on site type and download type."""
        opts = {
            "outtmpl": os.path.join(OUTPUT_DIR, "%(title)s.%(ext)s"),
            "ffmpeg_location": FFMPEG_PATH,
            "noplaylist": True,
            "nocheckcertificate": True,
            "no_color": True,
            "geo_bypass": True,
            "extractor_retries": EXTRACTOR_RETRIES,
            "socket_timeout": SOCKET_TIMEOUT,
            "http_headers": DEFAULT_HEADERS,
        }

        # Cookies
        if self.cookies_file:
            opts["cookiefile"] = self.cookies_file

        # Download type specifics
        if download_type == "audio":
            opts["format"] = "bestaudio/best"
            opts["postprocessors"] = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": DEFAULT_AUDIO_BITRATE,
                }
            ]
        else:
            opts["format"] = (
                f"bestvideo[height<={MAX_VIDEO_HEIGHT}]+bestaudio/"
                f"best[height<={MAX_VIDEO_HEIGHT}]/best"
            )
            opts["merge_output_format"] = "mp4"

        # Site-specific overrides
        self._apply_site_options(opts, site_type, download_type)

        return opts

    def _apply_site_options(self, opts, site_type, download_type):
        """Apply site-specific yt-dlp option overrides."""
        if site_type == "youtube":
            opts["extractor_args"] = {
                "youtube": {
                    "player_client": ["android", "web"],
                    "player_skip": ["js", "configs"],
                }
            }
            opts["geo_bypass_country"] = "US"

        elif site_type == "instagram":
            opts["age_limit"] = 99

        elif site_type == "rumble":
            opts["impersonate"] = "chrome"

        elif site_type in ("m6", "tf1", "francetv"):
            opts["geo_bypass_country"] = "FR"
            if download_type == "video":
                # Enhanced format selection for French DASH streams
                opts["format"] = (
                    "bv*[ext=mp4]+ba[language=fr]/bv*+ba[language=fr]/"
                    "bv*[ext=mp4]+ba/bv*+ba/"
                    "b[ext=mp4]/b/best"
                )
                opts["format_sort"] = ["res", "lang:fr", "proto:https"]
                opts["postprocessors"] = [
                    {"key": "FFmpegVideoConvertor", "preferedformat": "mp4"}
                ]
                opts["postprocessor_args"] = {
                    "ffmpeg": ["-c:v", "copy", "-c:a", "aac", "-b:a", "192k"]
                }

        elif site_type == "twitter":
            # Twitter/X works well with default options
            pass

    # ------------------------------------------------------------------
    # Info extraction
    # ------------------------------------------------------------------

    def _extract_info(self, url, site_type):
        """Extract video info without downloading."""
        info_opts = {
            "noplaylist": True,
            "nocheckcertificate": True,
            "ignoreerrors": True,
            "no_color": True,
            "geo_bypass": True,
            "extractor_retries": EXTRACTOR_RETRIES,
            "socket_timeout": SOCKET_TIMEOUT,
        }

        if self.cookies_file:
            info_opts["cookiefile"] = self.cookies_file

        # Site-specific info extraction options
        if site_type == "youtube":
            info_opts["extractor_args"] = {
                "youtube": {
                    "player_client": ["android", "web"],
                    "player_skip": ["js", "configs"],
                }
            }
        elif site_type == "instagram":
            info_opts["age_limit"] = 99

        try:
            with yt_dlp.YoutubeDL(info_opts) as ydl:
                print("Extraction des informations...")
                return ydl.extract_info(url, download=False)
        except Exception as e:
            print(f"Extraction des infos échouée: {e}")
            return None

    # ------------------------------------------------------------------
    # Quality selection
    # ------------------------------------------------------------------

    def _get_quality_options(self, formats):
        """Build quality option list from available formats (max 1080p)."""
        standard_res = [1080, 720, 480]

        video_formats = [f for f in formats if f.get("vcodec") != "none"]
        available_heights = {
            f.get("height", 0)
            for f in video_formats
            if 0 < f.get("height", 0) <= MAX_VIDEO_HEIGHT
        }

        if not available_heights:
            return []

        sorted_heights = sorted(available_heights, reverse=True)
        options = []

        for res in standard_res:
            closest = next((h for h in sorted_heights if h <= res), None)
            if closest is None:
                continue

            options.append(
                {
                    "format_string": (
                        f"bestvideo[height<={res}]+bestaudio/"
                        f"best[height<={res}]"
                    ),
                    "height": res,
                    "display_name": f"{res}p",
                }
            )
            if len(options) >= 3:
                break

        # Fallback: use the best available height
        if not options and sorted_heights:
            h = sorted_heights[0]
            options.append(
                {
                    "format_string": f"bestvideo[height<={h}]+bestaudio/best[height<={h}]",
                    "height": h,
                    "display_name": f"{h}p",
                }
            )

        return options

    # ------------------------------------------------------------------
    # Download execution
    # ------------------------------------------------------------------

    def _do_download(self, url, download_type, opts, site_type):
        """
        Execute the download with cascading fallbacks:
        1. yt-dlp Python API
        2. yt-dlp Python API with relaxed options
        3. yt-dlp CLI subprocess (different process = fresh state)
        """
        # Attempt 1: yt-dlp Python API with full options
        result = self._download_with_ytdlp(url, download_type, opts)
        if result:
            return result

        # Attempt 2: Relaxed options (simpler format, no special site config)
        print("\nPremière tentative échouée. Essai avec options simplifiées...")
        relaxed_opts = self._build_relaxed_options(download_type)
        result = self._download_with_ytdlp(url, download_type, relaxed_opts)
        if result:
            return result

        # Attempt 3: CLI subprocess (completely fresh yt-dlp process)
        print("\nDeuxième tentative échouée. Essai avec méthode CLI...")
        return self._download_with_cli(url, download_type)

    def _download_with_ytdlp(self, url, download_type, opts):
        """Download using yt-dlp Python API. Returns filepath or None."""
        # Use a temp dir for protected sites to avoid cache issues
        site_type = self._detect_site_type(url)
        use_temp = site_type in ("m6", "tf1", "francetv", "rumble")

        temp_dir = None
        try:
            if use_temp:
                temp_dir = tempfile.mkdtemp(prefix=f"ytdl_{site_type}_")
                opts = dict(opts)  # Copy to avoid mutating
                opts["outtmpl"] = os.path.join(temp_dir, "%(title)s.%(ext)s")

            with yt_dlp.YoutubeDL(opts) as ydl:
                print("\nTéléchargement en cours...")
                ydl.download([url])

            # Find the downloaded file
            search_dir = temp_dir if use_temp else OUTPUT_DIR
            ext = (".mp3",) if download_type == "audio" else (".mp4", ".mkv", ".webm")
            downloaded = find_latest_file(search_dir, ext)

            if not downloaded:
                print("Aucun fichier trouvé après le téléchargement.")
                return None

            # Validate
            is_valid, msg = validate_downloaded_file(downloaded)
            if not is_valid:
                # Accept small files too (some are legitimately small)
                size_mb = os.path.getsize(downloaded) / (1024 * 1024)
                if size_mb < 0.01:  # Less than 10KB = definitely failed
                    print(f"Fichier invalide: {msg}")
                    return None

            # Move from temp to output dir if needed
            if use_temp and temp_dir:
                filename = clean_filename(os.path.basename(downloaded))
                # Ensure correct extension
                expected_ext = ".mp3" if download_type == "audio" else ".mp4"
                if not filename.lower().endswith(expected_ext):
                    filename = os.path.splitext(filename)[0] + expected_ext
                final_path = os.path.join(OUTPUT_DIR, filename)

                if os.path.exists(final_path):
                    os.remove(final_path)
                shutil.move(downloaded, final_path)
                downloaded = final_path

            size_mb = os.path.getsize(downloaded) / (1024 * 1024)
            print("\nTéléchargement terminé avec succès.")
            print(f"Fichier: {downloaded}")
            print(f"Taille: {size_mb:.2f} MB")
            open_file_explorer(downloaded)
            return downloaded

        except Exception as e:
            print(f"Erreur yt-dlp: {e}")
            return None

        finally:
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except Exception:
                    pass

    def _build_relaxed_options(self, download_type):
        """Build simplified fallback options."""
        opts = {
            "outtmpl": os.path.join(OUTPUT_DIR, "%(title)s.%(ext)s"),
            "ffmpeg_location": FFMPEG_PATH,
            "noplaylist": True,
            "nocheckcertificate": True,
            "no_color": True,
            "geo_bypass": True,
            "socket_timeout": SOCKET_TIMEOUT,
        }

        if self.cookies_file:
            opts["cookiefile"] = self.cookies_file

        if download_type == "audio":
            opts["format"] = "bestaudio/best"
            opts["postprocessors"] = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": DEFAULT_AUDIO_BITRATE,
                }
            ]
        else:
            # Simple format: let yt-dlp decide
            opts["format"] = "best"
            opts["merge_output_format"] = "mp4"

        return opts

    def _download_with_cli(self, url, download_type):
        """Last resort: use yt-dlp as a CLI subprocess."""
        cmd = [
            sys.executable,
            "-m",
            "yt_dlp",
            "--output",
            os.path.join(OUTPUT_DIR, "%(title)s.%(ext)s"),
            "--ffmpeg-location",
            FFMPEG_PATH,
            "--no-playlist",
            "--no-check-certificate",
            "--geo-bypass",
        ]

        if self.cookies_file:
            cmd.extend(["--cookies", self.cookies_file])

        if download_type == "audio":
            cmd.extend([
                "--extract-audio",
                "--audio-format", "mp3",
                "--audio-quality", DEFAULT_AUDIO_BITRATE,
            ])
        else:
            cmd.extend([
                "--format",
                f"bestvideo[height<={MAX_VIDEO_HEIGHT}]+bestaudio/best",
                "--merge-output-format", "mp4",
            ])

        cmd.append(url)

        try:
            print("\nTéléchargement CLI en cours...")
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)

            if result.returncode != 0:
                stderr = result.stderr or ""
                print(f"Erreur CLI: {stderr[:300]}")
                return None

            # Find downloaded file
            ext = (".mp3",) if download_type == "audio" else (".mp4",)
            downloaded = find_latest_file(OUTPUT_DIR, ext)

            if downloaded:
                size_mb = os.path.getsize(downloaded) / (1024 * 1024)
                print("\nTéléchargement terminé avec succès.")
                print(f"Fichier: {downloaded}")
                print(f"Taille: {size_mb:.2f} MB")
                open_file_explorer(downloaded)
                return downloaded
            else:
                print("Aucun fichier trouvé après le téléchargement CLI.")
                return None

        except Exception as e:
            print(f"Erreur CLI: {e}")
            return None

    def _direct_download(self, url, download_type, opts):
        """Attempt download without prior info extraction."""
        return self._do_download(url, download_type, opts, "generic")