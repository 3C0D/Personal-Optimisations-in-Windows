"""
File utility functions: validation, cleanup, filename sanitization, explorer.
"""

import os
import re
import subprocess

from core.config import FFMPEG_EXE, MIN_VALID_FILE_SIZE_MB


def open_file_explorer(path):
    """
    Open Windows file explorer at specified location.
    If path is a file, opens its containing folder and selects it.
    """
    normalized = os.path.normpath(path)
    try:
        if os.path.isfile(normalized):
            subprocess.Popen(f'explorer /select,"{normalized}"', shell=True)
        else:
            subprocess.Popen(f'explorer "{normalized}"', shell=True)
    except Exception as e:
        print(f"Note: Unable to automatically open file explorer: {e}")
        print(f"File path: {normalized}")


def clean_filename(name):
    """
    Sanitize a string for use as a filename on Windows.
    Removes characters that are illegal in Windows filenames.
    """
    return re.sub(r'[<>:"/\\|?*]', "_", name)


def find_latest_file(directory, extensions):
    """
    Find the most recently created file in directory matching given extensions.

    Args:
        directory: Directory to search in
        extensions: Tuple of extensions (e.g. ('.mp4', '.mkv'))

    Returns:
        str or None: Full path to the latest file, or None
    """
    if not os.path.exists(directory):
        return None

    matching = [
        os.path.join(directory, f)
        for f in os.listdir(directory)
        if f.lower().endswith(extensions)
    ]

    if not matching:
        return None

    return max(matching, key=os.path.getctime)


def validate_downloaded_file(filepath, min_size_mb=MIN_VALID_FILE_SIZE_MB):
    """
    Validate that a downloaded file exists and is not corrupted.

    Returns:
        tuple: (is_valid: bool, message: str)
    """
    if not os.path.exists(filepath):
        return False, "File does not exist"

    file_size_mb = os.path.getsize(filepath) / (1024 * 1024)

    if file_size_mb < min_size_mb:
        return (
            False,
            f"File too small: {file_size_mb:.2f} MB (minimum: {min_size_mb} MB)",
        )

    # Check first bytes to detect obvious corruption
    try:
        with open(filepath, "rb") as f:
            header = f.read(100)
            if b"<html" in header.lower() or b"<!doctype" in header.lower():
                return False, "File appears to be HTML (likely error page)"
    except Exception as e:
        return False, f"Error validating file: {e}"

    return True, f"File validation successful: {file_size_mb:.2f} MB"


def check_file_exists(directory, title, extension):
    """
    Check if a file with the given title already exists in directory.
    Handles fuzzy matching for titles with special quotes/characters.

    Args:
        directory: Directory to check
        title: Video title
        extension: Expected file extension (e.g. '.mp4')

    Returns:
        str or None: Full path to existing file, or None
    """
    if not title or not os.path.exists(directory):
        return None

    filename = clean_filename(title) + extension
    filepath = os.path.join(directory, filename)

    # Direct check
    if os.path.exists(filepath):
        return filepath

    # Fuzzy check: normalize quotes and compare
    def normalize(s):
        return (
            s.replace('"', "")
            .replace("\u201c", "")
            .replace("\u201d", "")
            .replace("\uff07", "")
            .replace("'", "")
        )

    normalized_title = normalize(title)

    for file in os.listdir(directory):
        name_no_ext = os.path.splitext(file)[0]
        if normalize(name_no_ext) == normalized_title:
            return os.path.join(directory, file)

    return None


def extract_audio_from_file(video_path, output_path=None, bitrate="192"):
    """
    Extract audio from a video file using ffmpeg.

    Args:
        video_path: Path to the source video file
        output_path: Path for the output MP3 (auto-generated if None)
        bitrate: Audio bitrate in kbps

    Returns:
        str or None: Path to the extracted audio file, or None on failure
    """
    if not os.path.exists(video_path):
        print("Le fichier source n'existe pas.")
        return None

    if output_path is None:
        name = os.path.splitext(os.path.basename(video_path))[0]
        output_path = os.path.join(os.path.dirname(video_path), name + ".mp3")

    cmd = [
        FFMPEG_EXE,
        "-i", video_path,
        "-vn",
        "-acodec", "mp3",
        "-ab", f"{bitrate}k",
        "-y",  # Overwrite output
        output_path,
    ]

    try:
        print("Extraction audio en cours...")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            size_mb = os.path.getsize(output_path) / (1024 * 1024)
            print(f"Extraction terminée: {os.path.basename(output_path)} ({size_mb:.2f} MB)")
            return output_path
        else:
            print(f"Échec de l'extraction audio: {result.stderr[:200]}")
            return None
    except Exception as e:
        print(f"Erreur lors de l'extraction: {e}")
        return None