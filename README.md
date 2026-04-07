# hanimetv2026
This CLI uses yt-dlp with a plugin for downloading videos from hanime.tv and the API for adding metadata to the files.

### Python Packages Installation
Install the required Python packages using pip:

```bash
pip install hanimetv2026
pip install yt-dlp 
pip install ffmpeg
pip install --user hanime-plugin
```
For `hanime-plugin` you also need to install java Script (deno worked for me):
```bash
irm https://deno.land/install.ps1 | iex
```
## Features

- **Batch downloading**: Download multiple videos at once from a text file
- **Search functionality**: Search and download videos by tag or brand
- **All videos mode**: Download all videos from hanime.tv (by tags censored and uncensored)
- **Metadata support**: Includes metadata and thumbnails by default
- **Poster download**: Option to download posters separately
- **Download archive**: Track, save and skip downloaded videos with `--save-urls-dir` or `--save-slugs-dir` as a txt file
- **Update function**: Check for recent updates to already downloaded videos (only with download-archiv)

## CLI Usage

### Basic Modes

| Command | Description |
|---------|-------------|
| `hanimetv2026 --video <URL>` | Download a single video |
| `hanimetv2026 --batch-file <FILE>` | Download all URLs from a text file |
| `hanimetv2026 --search [--tag TAGS] [--brand BRANDS]` | Search and download videos by tag or brand |
| `hanimetv2026 --all` | Download all videos (censored and uncensored) |
| `hanimetv2026 --update <MODE>` | Check for updates to already downloaded videos |

### Advanced Options

```bash
usage: hanimetv2026 [-h] [--resolution RESOLUTION] [--retrys RETRYS]
                    [--sleep-time SLEEP_TIME]
                    [--downloader-args DOWNLOADER_ARGS [DOWNLOADER_ARGS ...]]
                    [--verbose] [--verbose-ffmpeg] [--poster-download]
                    [--no-thumbnail] [--no-metadata] [--no-merged-description]
                    [--title-as-filename] [--skip-unavailable-fragments]
                    [--output-dir OUTPUT_DIR] [--working-dir WORKING_DIR]
                    [--save-urls-dir SAVE_URLS_DIR]
                    [--save-slugs-dir SAVE_SLUGS_DIR] [--errors-dir ERRORS_DIR]
                    [--download-archive DOWNLOAD_ARCHIVE] [--video VIDEO]
                    [--all] [--batch-file BATCH_FILE] [--search] [--update]
                    [--only-posters] [--add-only-metadata]
                    [--continue-from-page CONTINUE_FROM_PAGE]
                    [--tags TAGS [TAGS ...]] [--brand BRAND [BRAND ...]]
```

#### Option Details

| Option | Description |
|--------|-------------|
| `--resolution`, `-R` | Resolution of download (default: 1080) |
| `--retrys`, `-r` | Number of retry attempts for failed downloads (default: 2) |
| `--sleep-time`, `-s` | Sleep time between retries |
| `--downloader-args` | Additional arguments to pass to yt-dlp |
| `--verbose`, `-v` | Enable verbose logging for video download |
| `--poster-download` | Download poster image separately |
| `--no-thumbnail` | Skip downloading thumbnail images |
| `--no-metadata` | Skip downloading embedded metadata |
| `--output-dir`, `-o` | Output directory for downloads |
| `--working-dir`, `-w` | Downloads and modifys videos in Working directory, then moves it to output-dir|
| `--save-urls-dir` | Path to log file for download URLs |
| `--errors-dir` | Path to text file for failed downloads |

## Plex Library Integration

### Step-by-Step Guide

1. **Download all videos with posters**:
   ```bash
   hanimetv2026 --all --poster-download \
     --save-urls-dir "C:\Users\UserName\Downloads\downloaded_urls.txt" \
     --working-dir "Path to fast/ SSD folder" \
     --output-dir "Path to HDD, NAS, or preferred storage" \
     --errors-dir "C:\Users\UserName\Downloads\errors.txt" \
     --verbose --retrys 1 --sleep-time 20
   ```

2. **Install the Plex scanner plugin**:
   - Download from [Pheromir's GitHub](https://github.com/Pheromir/HanimeTV.bundle/tree/main)
   - Note: This scanner only works in Movie media type

3. **Add a new movie library in Plex**:
   - Select source folder (import all videos at once!)
   - Set Scanner to "Plex Movie" and Agent to "Plex Movie"
   - Disable:
     - Prefer local assets
     - Prefer local metadata
     - Thumbnail generation
   This step is necessary to load the posters.

4. **Unmatch matched videos**
5. **Change Settings**  
    - Set Scanner to "Plex Movie Scanner" and Agent to "HanimeTV"
    - Disable:
      - Trailer
      - Thumbnail generation
6. **Update all metadata** 
    - Tags and Description will be added
7. **Split apart Duplicats**

### Notes for Adding New Videos
- Later imports may have incorrect posters that need manual adjustment.
- Posters must be selected manually but will appear automatically.


## FAQ

### General Questions

**Q: Can this download 1080p videos without Premium?**
A: No, only 720p is available without a premium account.

**Q: Does the hanime-plugin work in PowerShell?**
A: The plugin alone may not work naturally in PowerShell and cannot get metadata. You can fix the error by changing the enviroment before:
```bash
$env:PYTHONUTF8 = "1"; $env:PYTHONIOENCODING="utf-8"    
```

### Troubleshooting

**Q: What should I do if downloads fail?**
A: Check the errors directory for failed URLs. You can retry specific videos or adjust the retry settings with `--retrys` and `--sleep-time`. You can also rerun only the failed downloads by running the error.txt with --bath-file again

**Q: How can I update already downloaded videos?**
A: Use the `--update` mode along with either `--save-urls-dir` or `--save-slugs-dir`.


## Examples

### Basic Video Download
Download a single video with default settings:
```bash
hanimetv2026 --video "https://hanime.tv/videos/hentai/slug"
hanimetv2026 --video "https://hanime.tv/videos/hentai/slug" --output-dir "C:\downloads" --poster-download
```

### Batch Download from File
Download multiple videos listed in a text file:
```bash
hanimetv2026 --batch-file "C:\downloads\urls.txt" \
  --output-dir "D:\Hentai Collection" \
  --errors-dir "C:\downloads\errors.txt"

hanimetv2026 --batch-file "C:\downloads\errors.txt" \
  --output-dir "D:\Hentai Collection" \
  --errors-dir "C:\downloads\errors2.txt" 
```

### Search and Download by Tag
Download all videos with specific tags:
```bash
hanimetv2026 --search --tags "bondage" "cosplay" \
  --working-dir "C:fastFolder" \
  --output-dir "D:\Hentai\bondage-and-cosplay \
  --continue-from-page 5 \
  --save-urls-dir "C:\downloads\bondage-and-cosplay.txt"
```

### Update Existing Collection
Check for new videos in an existing collection:
```bash
hanimetv2026 --update -all \
  --save-slugs-dir "C:\downloads\downlaoded_videos.txt" \
  --errors-dir "C:\downloads\errors2.txt" \
  --working-dir "C:fastFolder" \
  --output-dir "D:\Hentai\" \
  ```
