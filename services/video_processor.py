"""
Video Processor — ffmpeg-based pre-processing before YouTube upload.

prepend_thumbnail(video_path, thumb_path, duration) → output_path
  Prepends a 2-second still image clip to the video so YouTube picks
  that frame as the Short thumbnail.

  Safe margin: only prepend if original duration ≤ 178s so total ≤ 180s.
  If duration > 178s → returns original video_path unchanged.
"""

import asyncio
import os
import tempfile
from utils.logger import log

# Prepend duration in seconds
THUMB_DURATION = 2
# Max Short duration — only prepend if result stays ≤ this
SHORTS_MAX = 180


async def prepend_thumbnail(video_path: str, thumb_path: str, duration: int) -> str:
    """
    Prepend a THUMB_DURATION-second still of thumb_path to video_path.
    Returns path to the processed video (caller must delete it).
    Returns original video_path if prepend is unsafe or ffmpeg fails.
    """
    safe_to_prepend = duration <= (SHORTS_MAX - THUMB_DURATION)

    if not safe_to_prepend:
        log.info(f"prepend_thumbnail: skipping — duration {duration}s too close to {SHORTS_MAX}s limit")
        return video_path

    # Probe video dimensions so thumb clip matches exactly
    probe_cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "csv=p=0",
        video_path
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *probe_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await proc.communicate()
        dimensions = stdout.decode().strip()
        if "," in dimensions:
            width, height = dimensions.split(",")[:2]
            scale_filter = f"scale={width.strip()}:{height.strip()}"
        else:
            scale_filter = "scale=1080:1920"
    except Exception as e:
        log.warning(f"prepend_thumbnail: ffprobe failed ({e}), using default scale")
        scale_filter = "scale=1080:1920"

    # Temp files
    fd_clip, clip_path = tempfile.mkstemp(suffix="_thumb_clip.mp4")
    os.close(fd_clip)
    fd_out, out_path = tempfile.mkstemp(suffix="_with_thumb.mp4")
    os.close(fd_out)

    try:
        # Step 1: image → THUMB_DURATION-second video clip
        cmd_clip = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", thumb_path,
            "-t", str(THUMB_DURATION),
            "-vf", scale_filter,
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-an",          # no audio in thumb clip
            clip_path
        ]
        proc1 = await asyncio.create_subprocess_exec(
            *cmd_clip,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        _, stderr1 = await proc1.communicate()
        if proc1.returncode != 0:
            log.warning(f"prepend_thumbnail: thumb clip creation failed: {stderr1.decode()[-300:]}")
            return video_path

        # Step 2: concat thumb_clip + original video
        # Use concat demuxer for reliability
        fd_list, list_path = tempfile.mkstemp(suffix="_concat.txt")
        with os.fdopen(fd_list, "w") as f:
            f.write(f"file '{clip_path}'\n")
            f.write(f"file '{video_path}'\n")

        cmd_concat = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", list_path,
            "-c", "copy",
            out_path
        ]
        proc2 = await asyncio.create_subprocess_exec(
            *cmd_concat,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        _, stderr2 = await proc2.communicate()
        os.unlink(list_path)

        if proc2.returncode != 0:
            log.warning(f"prepend_thumbnail: concat failed: {stderr2.decode()[-300:]}")
            return video_path

        log.info(f"prepend_thumbnail: success → {out_path} (original {duration}s + {THUMB_DURATION}s thumb)")
        return out_path

    except Exception as e:
        log.error(f"prepend_thumbnail: unexpected error: {e}")
        return video_path
    finally:
        # Always clean up the intermediate thumb clip
        try:
            if os.path.exists(clip_path):
                os.remove(clip_path)
        except Exception:
            pass
