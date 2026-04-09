# TubeArchivist Offline Import Prep

This guide explains how to download YouTube videos on a host that has access to YouTube, then prepare those files for later import into TubeArchivist on a host where YouTube is unavailable.

As of April 9, 2026, the latest stable `yt-dlp` release shown in the official repository is `2025.12.08`. The project also documents `nightly` and `master` channels; `stable` is the default, and `nightly` is the recommended channel for regular users who want newer fixes.

## Goal

Prepare a file set that TubeArchivist can import reliably:

- video in `.mp4`
- metadata in `.info.json`
- comments stored inside `.info.json`
- thumbnail in `.jpg`
- subtitles in `.vtt` when available
- filename containing the YouTube ID in square brackets

Expected result:

```text
Some_Title_[dQw4w9WgXcQ].mp4
Some_Title_[dQw4w9WgXcQ].info.json
Some_Title_[dQw4w9WgXcQ].jpg
Some_Title_[dQw4w9WgXcQ].en.vtt
```

## Why This Format

TubeArchivist manual import matches related files by basename and looks for the YouTube ID in the filename first, then in the JSON metadata file.

The most useful set for import is:

- `.mp4`
- `.info.json`
- `.jpg`
- `.vtt`

When `--write-comments` is enabled, comments are stored inside the `.info.json` file.

## Script

Use the helper script:

[`tools/prepare_tubearchivist_import.sh`](/Users/bronin/my/tubearchivist/tools/prepare_tubearchivist_import.sh)

Make it executable once:

```bash
chmod +x tools/prepare_tubearchivist_import.sh
```

Single video:

```bash
tools/prepare_tubearchivist_import.sh \
  'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
```

Multiple URLs:

```bash
tools/prepare_tubearchivist_import.sh \
  -o ./ta-export \
  'https://www.youtube.com/watch?v=VIDEO_ID_1' \
  'https://www.youtube.com/watch?v=VIDEO_ID_2'
```

## What The Script Does

The script runs `yt-dlp` with these important options:

- saves output as `%(title)s [%(id)s].%(ext)s`
- keeps original Unicode titles, including Cyrillic
- defaults to an `mp4`-friendly result capped at `480p`
- writes `.info.json`
- writes comments into `.info.json`
- writes a thumbnail and converts it to `.jpg`
- writes subtitles and converts them to `.vtt`
- reformats each `.info.json` with indentation for easier reading

Equivalent `yt-dlp` command:

```bash
yt-dlp \
  --paths "home:./ta-export" \
  --windows-filenames \
  --no-overwrites \
  --format 'bv*[height<=480][ext=mp4]+ba[ext=m4a]/b[height<=480][ext=mp4]/b[height<=480]/b' \
  --merge-output-format mp4 \
  --write-info-json \
  --write-comments \
  --write-thumbnail \
  --convert-thumbnails jpg \
  --write-subs \
  --sub-langs 'all,-live_chat' \
  --convert-subs vtt \
  --output '%(title)s [%(id)s].%(ext)s' \
  'https://www.youtube.com/watch?v=VIDEO_ID'
```

If you want a different quality, pass your own `-f/--format` value to the helper script.

After download, the helper script also reformats all `*.info.json` files with `jq .`, so they are easier to inspect manually.

## Update yt-dlp

Official repo links:

- Repository: https://github.com/yt-dlp/yt-dlp
- Release channel docs: https://github.com/yt-dlp/yt-dlp

If you use the release binary:

```bash
yt-dlp -U
```

If you want the newer `nightly` channel:

```bash
yt-dlp --update-to nightly
```

If you installed with `pip`:

```bash
python -m pip install -U "yt-dlp[default]"
```

## Import Into TubeArchivist

After download:

1. Copy the generated files into TubeArchivist's import directory.
2. Trigger manual import:

```bash
curl -X POST http://HOST/api/appsettings/manual-import/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"ignore_error": false, "prefer_local": false}'
```

If you already have TubeArchivist-embedded metadata inside the `.mp4`, use:

```json
{
  "ignore_error": false,
  "prefer_local": true
}
```

## Recommended Settings For Offline Environments

If the destination host has no YouTube access, disable features that trigger external requests:

- comments download
- SponsorBlock
- Return YouTube Dislike

This reduces delays and failed network attempts during or after import.

## Important Limitation

An ordinary `yt-dlp` download plus `.info.json` improves import reliability, and comments can be preserved inside that `.info.json`, but it does not guarantee a fully offline import path. TubeArchivist may still attempt external lookups in some flows.

The most reliable offline workflow is:

1. Download with `yt-dlp` on an online host.
2. Import into TubeArchivist on an online host.
3. Let TubeArchivist embed its own metadata into the `.mp4`.
4. Move that `.mp4` into the offline environment.
5. Import with `prefer_local=true`.
