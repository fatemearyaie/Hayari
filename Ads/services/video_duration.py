import json
import subprocess
import tempfile


class VideoDurationError(Exception):
    pass


def get_video_duration_seconds(uploaded_file) -> float:
    """
    Duration from UploadedFile (TemporaryUploadedFile or InMemoryUploadedFile)
    """
    # file already on disk
    if hasattr(uploaded_file, "temporary_file_path"):
        return get_video_duration_seconds_from_path(uploaded_file.temporary_file_path())

    # file in memory -> write to temp then probe
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=True) as tmp:
        for chunk in uploaded_file.chunks():
            tmp.write(chunk)
        tmp.flush()
        return get_video_duration_seconds_from_path(tmp.name)


def get_video_duration_seconds_from_path(path: str) -> float:
    """
    Duration from a local file path (e.g., instance.video.path)
    """
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "json",
        path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0 or not result.stdout:
        raise VideoDurationError("امکان تشخیص مدت زمان ویدیو نیست.")

    try:
        data = json.loads(result.stdout)
        return float(data["format"]["duration"])
    except Exception:
        raise VideoDurationError("مدت زمان ویدیو قابل خواندن نیست.")


def get_duration_bucket(seconds: float, tolerance: float = 1.5) -> int:
    """
    Convert seconds into 30 / 60 / 90 / 120 bucket
    """
    if seconds <= 30 + tolerance:
        return 30
    if seconds <= 60 + tolerance:
        return 60
    if seconds <= 90 + tolerance:
        return 90
    if seconds <= 120 + tolerance:
        return 120

    raise VideoDurationError("ویدیو بیشتر از 120 ثانیه است.")