"""
Functionality:
- parse timecode strings into segment tuples
- cut and concatenate video segments using ffmpeg
"""

import os
import subprocess
import tempfile


class TimecodeParseError(ValueError):
    """raised when a timecode string cannot be parsed"""


class VideoClipper:
    """cut and concatenate video segments using ffmpeg"""

    def __init__(self, source_path: str, output_path: str):
        self.source_path = source_path
        self.output_path = output_path

    @staticmethod
    def parse_timecode(tc: str) -> float:
        """parse a timecode string into total seconds

        Formats accepted:
            SS          -> seconds only
            MM:SS       -> minutes:seconds
            MM:SS:ms    -> minutes:seconds:milliseconds (1-999)

        Note: HH:MM:SS format is not used. For videos longer than 59 minutes,
        use large minute values (e.g. '90:30' for 1h 30m 30s).
        """
        tc = tc.strip()
        parts = tc.split(":")

        try:
            if len(parts) == 1:
                return float(parts[0])
            if len(parts) == 2:
                return int(parts[0]) * 60 + float(parts[1])
            if len(parts) == 3:
                # MM:SS:ms  (milliseconds as third component)
                return int(parts[0]) * 60 + int(parts[1]) + float(parts[2]) / 1000.0
        except (ValueError, IndexError) as exc:
            raise TimecodeParseError(
                f"cannot parse timecode: {tc!r}"
            ) from exc

        raise TimecodeParseError(f"unsupported timecode format: {tc!r}")

    @staticmethod
    def parse_segments(segments_str: str) -> list[tuple[float, float]]:
        """parse '00:15-01:25,16:21-18:10' into [(15.0, 85.0), ...]

        Segment string format:
            <start>-<end>[,<start>-<end>...]
        """
        segments = []
        for part in segments_str.split(","):
            part = part.strip()
            if not part:
                continue
            if "-" not in part:
                raise TimecodeParseError(
                    f"segment missing '-' separator: {part!r}"
                )
            # split on the last '-' to handle negative or unusual inputs
            idx = part.rfind("-")
            start_str = part[:idx]
            end_str = part[idx + 1 :]
            start = VideoClipper.parse_timecode(start_str)
            end = VideoClipper.parse_timecode(end_str)
            if end <= start:
                raise TimecodeParseError(
                    f"end time {end} must be greater than start time {start}"
                )
            segments.append((start, end))

        if not segments:
            raise TimecodeParseError("no segments found in string")

        return segments

    def cut(self, segments: list[tuple[float, float]]) -> str:
        """cut and concatenate segments, return output_path"""
        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)

        if len(segments) == 1:
            self._cut_single(segments[0])
        else:
            self._cut_and_concat(segments)

        return self.output_path

    def _cut_single(self, segment: tuple[float, float]) -> None:
        """cut a single segment with ffmpeg -c copy"""
        start, end = segment
        cmd = [
            "ffmpeg",
            "-y",
            "-ss", str(start),
            "-to", str(end),
            "-i", self.source_path,
            "-c", "copy",
            "-avoid_negative_ts", "make_zero",
            self.output_path,
        ]
        self._run(cmd)

    def _cut_and_concat(self, segments: list[tuple[float, float]]) -> None:
        """cut each segment to a temp file then concatenate"""
        tmp_dir = tempfile.mkdtemp()
        segment_files = []

        try:
            for i, (start, end) in enumerate(segments):
                seg_path = os.path.join(tmp_dir, f"seg_{i:04d}.mp4")
                cmd = [
                    "ffmpeg",
                    "-y",
                    "-ss", str(start),
                    "-to", str(end),
                    "-i", self.source_path,
                    "-c", "copy",
                    "-avoid_negative_ts", "make_zero",
                    seg_path,
                ]
                self._run(cmd)
                segment_files.append(seg_path)

            concat_list = os.path.join(tmp_dir, "concat.txt")
            with open(concat_list, "w", encoding="utf-8") as f:
                for seg_path in segment_files:
                    f.write(f"file '{seg_path}'\n")

            concat_cmd = [
                "ffmpeg",
                "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", concat_list,
                "-c", "copy",
                self.output_path,
            ]
            self._run(concat_cmd)

        finally:
            import shutil
            if os.path.exists(tmp_dir):
                shutil.rmtree(tmp_dir, ignore_errors=True)

    @staticmethod
    def _run(cmd: list[str]) -> None:
        """run a ffmpeg command, raise on failure"""
        print(f"[video_cut] running: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            capture_output=True,
        )
        if result.returncode != 0:
            stderr = result.stderr.decode("utf-8", errors="replace")[-500:]
            raise RuntimeError(
                f"ffmpeg failed (rc={result.returncode}): {stderr}"
            )
