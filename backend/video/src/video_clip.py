"""
Functionality:
- build Elasticsearch document for a video clip
- index clip and manage its lifecycle
"""

import hashlib
import os
import shutil
from datetime import datetime

from common.src.env_settings import EnvironmentSettings
from common.src.es_connect import ElasticWrap
from common.src.helper import get_duration_sec, get_duration_str
from playlist.src.index import YoutubePlaylist
from video.src.media_streams import MediaStreamExtractor
from video.src.video_cut import VideoClipper

CLIPS_PLAYLIST_ID = "TA_playlist_clips"
CLIPS_PLAYLIST_NAME = "Clips"


class YoutubeClip:
    """build and index a video clip derived from an archived video"""

    index_name = "ta_video"

    def __init__(
        self,
        source_doc: dict,
        segments: list[tuple[float, float]],
        title: str = "",
    ):
        self.source_doc = source_doc
        self.segments = segments
        self.title = title
        self.clip_id = self._build_clip_id()
        self.json_data: dict = {}

    def _build_clip_id(self) -> str:
        """build a stable clip id from source id and segment timecodes"""
        source_id = self.source_doc["youtube_id"]
        segments_key = ",".join(f"{s:.3f}-{e:.3f}" for s, e in self.segments)
        digest = hashlib.md5(
            f"{source_id}:{segments_key}".encode()
        ).hexdigest()[:8]
        return f"{source_id}_clip_{digest}"

    def _build_title(self) -> str:
        """build clip title"""
        if self.title:
            return self.title
        source_title = self.source_doc.get("title", self.clip_id)
        return f"{source_title} [clip]"

    def build_json(self, media_path: str) -> dict:
        """build ES document for the clip"""
        source = self.source_doc
        last_refresh = int(datetime.now().timestamp())
        total_duration = sum(end - start for start, end in self.segments)
        duration_sec = get_duration_sec(media_path)
        if not duration_sec:
            duration_sec = int(total_duration)

        media = MediaStreamExtractor(media_path)
        channel_id = source["channel"]["channel_id"]
        clip_segments = [
            {"start_time": s, "end_time": e} for s, e in self.segments
        ]

        self.json_data = {
            "active": True,
            "category": source.get("category", []),
            "channel": source["channel"],
            "clip_parent": source["youtube_id"],
            "clip_segments": clip_segments,
            "date_downloaded": last_refresh,
            "description": source.get("description", ""),
            "media_size": media.get_file_size(),
            "media_url": os.path.join(channel_id, f"{self.clip_id}.mp4"),
            "player": {
                "duration": duration_sec,
                "duration_str": get_duration_str(duration_sec),
                "watched": False,
            },
            "playlist": [],
            "published": source.get("published", ""),
            "stats": source.get("stats", {}),
            "streams": media.extract_metadata(),
            "subtitles": [],
            "tags": source.get("tags", []),
            "title": self._build_title(),
            "vid_last_refresh": last_refresh,
            "vid_thumb_url": source.get("vid_thumb_url", ""),
            "vid_type": source.get("vid_type", "videos"),
            "youtube_id": self.clip_id,
        }
        return self.json_data

    @property
    def es_path(self) -> str:
        """es document path"""
        return f"{self.index_name}/_doc/{self.clip_id}"

    def upload_to_es(self) -> None:
        """index the clip document"""
        ElasticWrap(self.es_path).put(self.json_data, refresh=True)

    def get_media_dest(self) -> str:
        """get final media file destination"""
        channel_id = self.source_doc["channel"]["channel_id"]
        return os.path.join(
            EnvironmentSettings.MEDIA_DIR,
            channel_id,
            f"{self.clip_id}.mp4",
        )

    @staticmethod
    def get_cache_path(clip_id: str) -> str:
        """temporary output path in cache"""
        return os.path.join(
            EnvironmentSettings.CACHE_DIR,
            "cut",
            f"{clip_id}.mp4",
        )

    def move_to_archive(self, cache_path: str) -> str:
        """move clip from cache to archive, return final path"""
        dest = self.get_media_dest()
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.move(cache_path, dest)
        return dest

    def _ensure_clip_thumbnail(self) -> None:
        """copy source thumbnail to clip thumbnail path so playlist art works"""
        from download.src.thumbnails import ThumbManager

        source_id = self.source_doc["youtube_id"]
        source_thumb = ThumbManager(source_id).vid_thumb_path(absolute=True)
        clip_thumb = ThumbManager(self.clip_id).vid_thumb_path(
            absolute=True, create_folder=True
        )
        if os.path.exists(source_thumb) and not os.path.exists(clip_thumb):
            shutil.copy2(source_thumb, clip_thumb)

    def _add_to_clips_playlist(self) -> None:
        """add this clip to the 'Clips' custom playlist, creating it if needed"""
        self._ensure_clip_thumbnail()
        playlist = YoutubePlaylist(CLIPS_PLAYLIST_ID)
        playlist.get_from_es()
        if not playlist.json_data:
            print(f"[clip] creating '{CLIPS_PLAYLIST_NAME}' playlist")
            playlist.create(CLIPS_PLAYLIST_NAME)
        playlist.add_video_to_playlist(self.clip_id)

    def cut_and_index(self, source_media_path: str) -> str:
        """cut source video, move to archive, index in ES"""
        cache_path = self.get_cache_path(self.clip_id)
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)

        print(f"[clip] cutting {self.clip_id} from {source_media_path}")
        VideoClipper(source_media_path, cache_path).cut(self.segments)

        self.build_json(cache_path)
        final_path = self.move_to_archive(cache_path)
        self.upload_to_es()
        self._add_to_clips_playlist()
        return final_path
