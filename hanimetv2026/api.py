#API wrapper for hanime.tv, providing video metadata functionality, 
import requests
import json
import re
import os
import time
from urllib.parse import urlparse

from hanimetv2026.colors import bcolors

#Creates an Video object from the hanime.tv API response, extracting relevant metadata 
#and constructing file paths for output and working directories based on user arguments.
class Video:
    def __init__(self, json_enc, args):
        video_data = json_enc.get("video", {})
        franchise_data = json_enc.get("franchise", {})

        self.title = video_data["name"] #The title of the video, as displayed on the website and used in search results
        self.slug = video_data["slug"] #slug is the unique identifier for a video, used in URLs and API calls
        self.sources = {} #A dictionary mapping source names (e.g. "server1-1080") to their corresponding video URLs, extracted from the "videos_manifest" section of the API response.
        metadata = {}

        file_name = self.title if args.title_as_filename else self.slug

        self.output_path_filename = os.path.join(args.output_dir, f"{file_name}.mp4")
        self.output_path_poster = os.path.join(args.output_dir, f"{file_name}.jpg") if (args.poster_download or args.only_posters) else None
        self.output_path_thumbnail = os.path.join(args.output_dir, f"{file_name}_thumbnail.jpg") if not args.no_thumbnail else None

        self.work_path_filename = os.path.join(args.working_dir, f"{file_name}.mp4") if args.working_dir else None
        self.work_path_poster = os.path.join(args.working_dir, f"{file_name}.jpg") if args.working_dir and (args.poster_download or args.only_posters) else None
        self.work_path_thumbnail = os.path.join(args.working_dir, f"{file_name}_thumbnail.jpg") if args.working_dir and not args.no_thumbnail else None

        metadata["brand"] = video_data["brand"]
        metadata["likes"] = video_data["likes"]
        metadata["dislikes"] = video_data["dislikes"]
        metadata["views"] = video_data["views"]
        metadata["tags"] = video_data["tags"]
        metadata["thumbnail"] = video_data["poster_url"]
        metadata["cover"] = video_data["cover_url"]
        metadata["downloads"] = video_data["downloads"]
        metadata["monthly_rank"] = video_data["monthly_rank"]
        metadata["description"] = re.compile(r'<[^>]+>').sub("", video_data["description"])
        metadata["released_at"] = video_data.get("released_at")
        metadata["created_at"] = video_data.get("created_at")
        # The new API endpoint does not expose Unix timestamp fields.
        metadata["released_at_unix"] = 0
        metadata["created_at_unix"] = 0
        metadata["franchise_slug"] = franchise_data.get("slug")
        metadata["franchise_title"] = franchise_data.get("title")
        metadata["franchise_videos"] = [vid["slug"] for vid in franchise_data.get("videos", [])]
        self.metadata = type("Metadata", (), metadata)()
    
    @staticmethod
    def from_slug(slug, args):
        #Load video metadata from the new Hanime scraper API endpoint.
        #And return a Video object constructed from the API response.
        max_retries = args.retrys
        for attempt in range(max_retries):
            try:
                resp = requests.get(
                    f"https://hanime-scraper.sapis.workers.dev/api/video/{slug}",
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                        "Accept": "application/json",
                        "Referer": "https://hanime.tv/",
                    },
                    timeout=15,
                )
                resp.raise_for_status()
                api_data = resp.json()

                if "video" not in api_data:
                    if attempt == max_retries - 1:
                        raise Exception(f"{bcolors.FAIL}[Hanimetv2026 Error:] No video object could be created for slug. Stopped download of {slug}{bcolors.ENDC}")
                    print(f"{bcolors.WARNING}[API Warning:] No video metadata found for slug {slug}. Retrying...{bcolors.ENDC}")
                    time.sleep(args.sleep_time)
                else:
                    return Video(api_data, args)
            
            except requests.exceptions.HTTPError as e:
                if attempt == max_retries - 1:
                    raise Exception(f"{bcolors.FAIL}[Hanimetv2026 Error:] Rate limit hit on metadata retrieval attempt {slug} after {max_retries} attempts. Stopped download of {slug}. Error: {e}{bcolors.ENDC}")
                if resp.status_code == 429:  # Rate limit
                    print(f"{bcolors.WARNING}[Hanimetv2026 Warning:] Rate limit hit on metadata retrieval attempt {attempt + 1} for slug {slug}. Waiting 3 minutes...{bcolors.ENDC}")
                    time.sleep(180)  # 3 minutes
                    continue
                print(f"{bcolors.WARNING}[Hanimetv2026 Warning:] Attempt {attempt + 1} failed to retrieve metadata for slug {slug}: {e}. Retrying...{bcolors.ENDC}")
                time.sleep(args.sleep_time)

            except Exception as e:
                if attempt == max_retries - 1:
                    raise Exception(f"{bcolors.FAIL}[Hanimetv2026 Error:] Failed to retrieve metadata for slug {slug} after {max_retries} attempts. Stopped download of {slug}. Error: {e}{bcolors.ENDC}")
                print(f"{bcolors.WARNING}[Hanimetv2026 Warning:] Attempt {attempt + 1} failed to retrieve metadata for slug {slug}: {e}. Retrying...{bcolors.ENDC}")
                time.sleep(args.sleep_time)
    
def parse_hanime_url(url):
    if not url:
        return None
    if "hanime.tv" in url:
        return url.split("/hentai/")[1].strip("/ ")
    if "freeanimehentai.net" in url:
        return url.split("/hentai/")[1].strip("/ ")
    return None