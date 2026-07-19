"""
Centralized configuration for the video/audio downloader.
All paths, constants and site-specific settings live here.
"""

import os

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Single output directory for all downloads
OUTPUT_DIR = os.path.join(os.path.expanduser("~"), "MyVidsAudios")

FFMPEG_PATH = r"C:\ffmpeg\bin"
FFMPEG_EXE = os.path.join(FFMPEG_PATH, "ffmpeg.exe")

COOKIES_FILE = os.path.join(SCRIPT_DIR, "cookies.txt")
LAST_UPDATE_FILE = os.path.join(SCRIPT_DIR, ".last_ytdlp_update")

# ---------------------------------------------------------------------------
# Download settings
# ---------------------------------------------------------------------------

# Maximum video resolution (height in pixels)
MAX_VIDEO_HEIGHT = 1080

# Default audio bitrate for MP3 conversion
DEFAULT_AUDIO_BITRATE = "192"

# Timeout for network operations (seconds)
SOCKET_TIMEOUT = 60

# Number of retries for extraction
EXTRACTOR_RETRIES = 10

# Minimum file size to consider a download valid (MB)
MIN_VALID_FILE_SIZE_MB = 1

# Update throttle: minimum seconds between yt-dlp updates (24 hours)
UPDATE_INTERVAL_SECONDS = 86400

# ---------------------------------------------------------------------------
# Site detection
# ---------------------------------------------------------------------------

# Sites requiring special yt-dlp handling
PROTECTED_SITES = {
    "m6.fr": "m6",
    "www.m6.fr": "m6",
    "m6plus.fr": "m6",
    "www.m6plus.fr": "m6",
    "6play.fr": "m6",
    "www.6play.fr": "m6",
    "tf1.fr": "tf1",
    "www.tf1.fr": "tf1",
    "lci.tf1.fr": "tf1",
    "tf1play.fr": "tf1",
    "www.tf1play.fr": "tf1",
    "france.tv": "francetv",
    "www.france.tv": "francetv",
    "francetvinfo.fr": "francetv",
    "www.francetvinfo.fr": "francetv",
    "pluzz.francetv.fr": "francetv",
    "rumble.com": "rumble",
    "www.rumble.com": "rumble",
    "twitter.com": "twitter",
    "www.twitter.com": "twitter",
    "x.com": "twitter",
    "www.x.com": "twitter",
}

# Sites using the KVS (Kernel Video Sharing) platform
KVS_SITES = [
    "pervarchive.com",
    "www.pervarchive.com",
    "pervertium.com",
    "www.pervertium.com",
    "tezfiles.com",
    "www.tezfiles.com",
    "www.analdin.com",
]

# Common HTTP headers for requests
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-us,en;q=0.5",
    "Sec-Fetch-Mode": "navigate",
}
