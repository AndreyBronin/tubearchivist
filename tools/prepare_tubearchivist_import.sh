#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
Prepare YouTube videos for later import into TubeArchivist.

Requirements:
  - yt-dlp
  - ffmpeg
  - jq

Usage:
  prepare_tubearchivist_import.sh [options] URL [URL ...]

Options:
  -o, --output-dir DIR   Directory for downloaded files. Default: ./ta-export
  -s, --subs LANGS       Subtitle languages for yt-dlp. Default: all,-live_chat
  -f, --format FORMAT    yt-dlp format selector.
                         Default: bv*[height<=480][ext=mp4]+ba[ext=m4a]/b[height<=480][ext=mp4]/b[height<=480]/b
  -h, --help             Show this help.

Examples:
  prepare_tubearchivist_import.sh 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
  prepare_tubearchivist_import.sh -o /tmp/ta-export URL1 URL2
EOF
}

OUTPUT_DIR="./ta-export"
SUB_LANGS="all,-live_chat"
FORMAT="bv*[height<=480][ext=mp4]+ba[ext=m4a]/b[height<=480][ext=mp4]/b[height<=480]/b"

URLS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    -o|--output-dir)
      OUTPUT_DIR="${2:-}"
      shift 2
      ;;
    -s|--subs)
      SUB_LANGS="${2:-}"
      shift 2
      ;;
    -f|--format)
      FORMAT="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --)
      shift
      while [[ $# -gt 0 ]]; do
        URLS+=("$1")
        shift
      done
      ;;
    -*)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
    *)
      URLS+=("$1")
      shift
      ;;
  esac
done

if [[ ${#URLS[@]} -eq 0 ]]; then
  echo "At least one URL is required." >&2
  usage >&2
  exit 1
fi

if ! command -v yt-dlp >/dev/null 2>&1; then
  echo "yt-dlp is required but not found in PATH." >&2
  exit 1
fi

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "ffmpeg is required but not found in PATH." >&2
  exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "jq is required but not found in PATH." >&2
  exit 1
fi

mkdir -p "$OUTPUT_DIR"

echo "Output directory: $OUTPUT_DIR"
echo "Preparing ${#URLS[@]} item(s) for TubeArchivist import..."

yt-dlp \
  --paths "home:${OUTPUT_DIR}" \
  --windows-filenames \
  --no-overwrites \
  --format "$FORMAT" \
  --merge-output-format mp4 \
  --write-info-json \
  --write-comments \
  --write-thumbnail \
  --convert-thumbnails jpg \
  --write-subs \
  --sub-langs "$SUB_LANGS" \
  --convert-subs vtt \
  --output '%(title)s [%(id)s].%(ext)s' \
  "${URLS[@]}"

while IFS= read -r -d '' info_json; do
  tmp_json="${info_json}.tmp"
  jq . "$info_json" > "$tmp_json"
  mv "$tmp_json" "$info_json"
done < <(find "$OUTPUT_DIR" -type f -name '*.info.json' -print0)

cat <<EOF

Done.

Generated files should look like:
  Some_Title_[dQw4w9WgXcQ].mp4
  Some_Title_[dQw4w9WgXcQ].info.json
  Some_Title_[dQw4w9WgXcQ].jpg
  Some_Title_[dQw4w9WgXcQ].en.vtt

Comments are also requested and stored inside:
  Some_Title_[dQw4w9WgXcQ].info.json

The .info.json files are reformatted with indentation for easier reading.

For TubeArchivist:
  1. Copy the prepared files into the app import directory.
  2. Call POST /api/appsettings/manual-import/
  3. Keep the .info.json next to the video file.
EOF
