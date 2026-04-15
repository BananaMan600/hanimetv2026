from html import parser
import os
import sys

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

def parse_hanime_url(url):
    if "hanime.tv" in url:
        return url.split("/hentai/")[1]
    if "freeanimehentai.net" in url:
        return url.split("/hentai/")[1]
    return None   

def main():
    parser = argparse.ArgumentParser()
    #Download options
    parser.add_argument("--resolution", "-R", help="Resolution of download, default 1080", default=1080, type=int)
    parser.add_argument("--retrys", "-r", help="How often to retry failed downloads. (Default=2)", type=int, default=2)
    parser.add_argument("--sleep-time", "-s", dest="sleep_time", help="Sleep time between retries", type=int, default=30)
    parser.add_argument("--downloader-args", help="Additional arguments to pass to yt-dlp when downloading videos, e.g. --download-archive archive.txt", action="store", nargs="+", default=None)
    parser.add_argument("--verbose", "-v", help="Enable verbose logging for video download", action="store_true", default=False)
    parser.add_argument("--verbose-ffmpeg", help="Enable verbose logging for ffmpeg processing steps", action="store_true", default=False)
    parser.add_argument("--poster-download", help="Download poster image for videos as seperate file", action="store_true", default=False)
    parser.add_argument("--no-thumbnail", help="Do not download thumbnail image for videos", action="store_true", default=False)
    parser.add_argument("--no-metadata", help="Do not download embedded metadata", action="store_true", default=False)
    parser.add_argument("--no-merged-description", help="Do not merge description text file in the video metadata", action="store_true", default=False)
    parser.add_argument("--title-as-filename", help="Use video title as filename instead of slug", action="store_true", default=False)
    parser.add_argument("--skip-unavailable-fragments", help="Skip unavailable video fragments after retrying 1 time", action="store_true", default=False)

    #Path options
    parser.add_argument("--output-dir", "-o", help="Output directory for downloads", type=str, default=r".\\")
    parser.add_argument("--working-dir", "-w", help="Working directory for downloads", type=str, default=None)
    parser.add_argument("--save-urls-dir", dest="save_urls_dir", help="Path to log file for download URLs", type=str, default=None)
    parser.add_argument("--save-slugs-dir", dest="save_slugs_dir", help="Path to .txt file for slugs of downloaded videos", type=str, default=None)
    parser.add_argument("--errors-dir", dest="errors_dir", help="Path to .txt file for failed downloads", type=str, default=None)
    parser.add_argument("--download-archive", help="Path to yt-dlp download archive file", type=str, default=None)  

    #Modes
    parser.add_argument("--video", help="Video URL", type=str, default=None)
    parser.add_argument("--all", "-a", help="Download all videos", action="store_true", default=False)
    parser.add_argument("--batch-file", "-b", help="Path to .txt file containing video URLs or search terms, one per line", type=str, default=None)
    parser.add_argument("--search", help="Mode to use for search and download videos with other arguments", action="store_true", default=False)
    parser.add_argument("--update", help="Check for updates to videos already downloaded (only with --search)", action="store_true", default=False)
    parser.add_argument("--only-posters", help="Only download posters for videos", action="store_true", default=False)
    parser.add_argument("--add-only-metadata", help="Adds metadata and thumbnail to already downloaded videos in batch file", action="store_true", default=False)

    #Search arguments /Search via API broken, at this time search is only supported with tags
    parser.add_argument("--continue-from-page", help="Continue downloading from a specific page number (for --all or --search)", type=int, default=0)
    parser.add_argument("--tags", "-t", help="Tags to search for (used with --search)", action="store", nargs="+", default=["uncensored","censored"]) #Default to uncensored tag to avoid downloading censored videos by default
    parser.add_argument("--brand", "-c", help="Companies/brands to filter by (used with --search)", action="store", nargs="+", default=None)


    args = parser.parse_args()

    if len(sys.argv) == 1: #No arguments provided, show help message and exit
        parser.print_help()
        exit(1)

    # Check if more than one mutually exclusive mode is provided
    mode_args = [args.video, args.batch_file, args.all, args.search]
    if sum(arg is not None and arg != False for arg in mode_args) > 1:
        print("Only one of the mode arguments --video, --all, --batch-file and --search can be chosen at a time")
        exit(1)
    
    #check if update and other mode other than search is provided
    if args.update:
        mode_args = [args.batch_file, args.video, args.all]
        if not args.search:
            print("Update must be used with --search")
            return
        if sum(arg is not None and arg != False for arg in mode_args) > 0:
            print("Update can only be used with --search")
            return
        elif args.verbose:
            print("Update commands seem right.")

    start_video_download(args)


if __name__ == "__main__":
    main()
