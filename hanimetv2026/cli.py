from html import parser
import os
import sys

from hanimetv2026.colors import bcolors

# Ensure package root is on sys.path when running cli.py directly
package_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if package_root not in sys.path:
    sys.path.insert(0, package_root)

from hanimetv2026.api import Video # search
from hanimetv2026.downloader import start_video_download
import argparse

class Args:
    def __init__(self, args):
        self.args = args

def main():
    parser = argparse.ArgumentParser()

    download_group = parser.add_argument_group("Download options")
    download_group.add_argument("--resolution", "-R", help="Resolution of download, default 1080", default=1080, type=int)
    download_group.add_argument("--retrys", "-r", help="How often to retry failed downloads. (Default=2)", type=int, default=2)
    download_group.add_argument("--sleep-time", "-s", dest="sleep_time", help="Sleep time between retries (Default=10)", type=int, default=10)
    download_group.add_argument("--downloader-args", help="Additional arguments to pass to yt-dlp when downloading videos, e.g. --download-archive archive.txt", action="store", nargs="+", default=None)
    download_group.add_argument("--verbose", "-v", help="Enable verbose logging for video download", action="store_true", default=False)
    download_group.add_argument("--verbose-ffmpeg", help="Enable verbose logging for ffmpeg processing steps", action="store_true", default=False)
    download_group.add_argument("--poster-download", help="Download poster image for videos as seperate file", action="store_true", default=False)
    download_group.add_argument("--no-thumbnail", help="Do not download thumbnail image for videos", action="store_true", default=False)
    download_group.add_argument("--no-metadata", help="Do not download embedded metadata", action="store_true", default=False)
    download_group.add_argument("--add-only-metadata", help="Adds metadata and thumbnail to already downloaded videos in batch file", action="store_true", default=False)
    download_group.add_argument("--no-merged-description", help="Do not merge description text file in the video metadata", action="store_true", default=False)
    download_group.add_argument("--title-as-filename", help="Use video title as filename instead of slug", action="store_true", default=False)
    download_group.add_argument("--skip-unavailable-fragments", help="Skip unavailable video fragments after retrying 1 time", action="store_true", default=False)

    path_group = parser.add_argument_group("Path options")
    path_group.add_argument("--output-dir", "-o", help="Output directory for downloads", type=str, default=r".\\")
    path_group.add_argument("--working-dir", "-w", help="Working directory for downloads", type=str, default=None)
    path_group.add_argument("--save-urls-dir", dest="save_urls_dir", help="Path to log file for download URLs", type=str, default=None)
    path_group.add_argument("--save-slugs-dir", dest="save_slugs_dir", help="Path to .txt file for slugs of downloaded videos", type=str, default=None)
    path_group.add_argument("--errors-dir", dest="errors_dir", help="Path to .txt file for failed URL downloads", type=str, default=None)
    path_group.add_argument("--download-archive", help="Path to yt-dlp download archive file", type=str, default=None)

    mode_group = parser.add_argument_group("Modes")
    mode_group.add_argument("--video", help="Download a single video by URL", type=str, default=None)
    mode_group.add_argument("--all", "-a", help="Download all videos from hanimeTV", action="store_true", default=False)
    mode_group.add_argument("--batch-file", "-b", help="Path to .txt file containing video URLs or search terms, one per line", type=str, default=None)
    mode_group.add_argument("--search", help="Mode to use for search and download videos with other arguments", action="store_true", default=False)
    mode_group.add_argument("--only-posters", help="Only download posters for videos", action="store_true", default=False)

    search_group = parser.add_argument_group("Search options")
    search_group.add_argument("--update", help="search only for new videos, then stop", action="store_true", default=False)
    search_group.add_argument("--continue-from-page", help="Continue downloading from a specific page number (for --all or --search)", type=int, default=1)
    search_group.add_argument("--tags", "-t", help="Tags to search for (used with --search)", action="store", nargs="+", default=["uncensored", "censored"])  # Default to uncensored tag to avoid downloading censored videos by default
    search_group.add_argument("--brand", "-c", help="Companies/brands to filter by (used with --search)", action="store", nargs="+", default=None)

    args = parser.parse_args()

    if len(sys.argv) == 1: #No arguments provided, show help message and exit
        parser.print_help()
        exit(1)

    # Check if more than one mutually exclusive mode is provided
    mode_args = [args.video, args.batch_file, args.all, args.search]
    if sum(arg is not None and arg != False for arg in mode_args) > 1:
        print(bcolors.WARNING + "[Hanimetv2026 info:] Only one of the mode arguments --video, --all, --batch-file and --search can be chosen at a time" + bcolors.ENDC)
        exit(1)

    try:
        start_video_download(args)
        print(f"{bcolors.OKGREEN}[Hanimetv2026 Info:] Program completed successfully.{bcolors.ENDC}")
    except Exception as e:
        print(e)
        exit(1)


if __name__ == "__main__":
    main()
