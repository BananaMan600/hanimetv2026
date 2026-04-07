#API wrapper for hanime.tv, providing  video metadata functionality, 
import requests
import json
import re
import os
import time
from urllib.parse import urlparse


class SearchResult:
    def __init__(self, slug, title):
        self.title = title
        self.slug = slug
    
    @property
    def video(self):
        return Video.from_slug(self.slug)
    
    def __str__(self):
        return f"<Result {self.slug}: {self.title}>"
    
    __repr__ = __str__
   
    def __str__(self):
        return f'<Video {self.slug}: "{self.title}">'
    
    __repr__ = __str__

class Video:
    def __init__(self, json_enc, args):
        self.title = json_enc["hentai_video"]["name"] #The title of the video, as displayed on the website and used in search results
        self.slug = json_enc["hentai_video"]["slug"] #slug is the unique identifier for a video, used in URLs and API calls
        self.sources = {} #A dictionary mapping source names (e.g. "server1-1080") to their corresponding video URLs, extracted from the "videos_manifest" section of the API response.
        metadata = {}

        file_name = self.title if args.title_as_filename else self.slug

        self.output_path_filename = os.path.join(args.output_dir, f"{file_name}.mp4")
        self.output_path_poster = os.path.join(args.output_dir, f"{file_name}.jpg") if (args.poster_download or args.only_posters) else None
        self.output_path_thumbnail = os.path.join(args.output_dir, f"{file_name}_thumbnail.jpg") if not args.no_thumbnail else None

        self.work_path_filename = os.path.join(args.working_dir, f"{file_name}.mp4") if args.working_dir else None
        self.work_path_poster = os.path.join(args.working_dir, f"{file_name}.jpg") if args.working_dir and (args.poster_download or args.only_posters) else None
        self.work_path_thumbnail = os.path.join(args.working_dir, f"{file_name}_thumbnail.jpg") if args.working_dir and not args.no_thumbnail else None

        metadata["brand"] = json_enc["hentai_video"]["brand"]
        metadata["likes"] = json_enc["hentai_video"]["likes"]
        metadata["dislikes"] = json_enc["hentai_video"]["dislikes"]
        metadata["views"] = json_enc["hentai_video"]["views"]
        metadata["tags"] = list(map(lambda i: i["text"], json_enc["hentai_video"]["hentai_tags"]))
        metadata["thumbnail"] = json_enc["hentai_video"]["poster_url"]
        metadata["cover"] = json_enc["hentai_video"]["cover_url"]
        metadata["downloads"] = json_enc["hentai_video"]["downloads"]
        metadata["monthly_rank"] = json_enc["hentai_video"]["monthly_rank"]
        metadata["description"] = re.compile(r'<[^>]+>').sub("", json_enc["hentai_video"]["description"])
        metadata["released_at"] = json_enc["hentai_video"].get("released_at")
        metadata["created_at"] = json_enc["hentai_video"].get("created_at")
        metadata["released_at_unix"] = json_enc["hentai_video"].get("released_at_unix", 0)
        metadata["created_at_unix"] = json_enc["hentai_video"].get("created_at_unix", 0)
        metadata["franchise_slug"] = json_enc["hentai_franchise"]["slug"]
        metadata["franchise_title"] = json_enc["hentai_franchise"]["title"]
        metadata["franchise_videos"] = [vid["slug"] for vid in json_enc["hentai_franchise_hentai_videos"]]
        self.metadata = type("Metadata", (), metadata)()
    
    @staticmethod
    def from_slug(slug, args):
        #Load video metadata from hanime.tv API only (no yt-dlp fallback).
        max_retries = 3
        for attempt in range(max_retries):
            try:
                resp = requests.get(
                    f"https://hanime.tv/api/v8/video?id={slug}",
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36",
                        "Accept": "application/json",
                    },
                    timeout=15,
                )
                resp.raise_for_status()
                api_data = resp.json()

                if "hentai_video" not in api_data:
                    raise ValueError(f"No video metadata found for slug {slug}")

                return Video(api_data, args)
            except requests.exceptions.HTTPError as e:
                if resp.status_code == 429:  # Rate limit
                    print(f"Rate limit hit on metadata retrieval attempt {attempt + 1} for slug {slug}. Waiting 3 minutes...")
                    time.sleep(180)  # 3 minutes
                    continue
                else:
                    if attempt == max_retries - 1:
                        raise
                    if args and args.verbose:
                        print(f"Attempt {attempt + 1} failed to retrieve metadata for slug {slug}: {e}. Retrying...")
                    time.sleep(args.sleep_time if args and args.sleep_time else 5)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                if args and args.verbose:
                    print(f"Attempt {attempt + 1} failed to retrieve metadata for slug {slug}: {e}. Retrying...")
                time.sleep(args.sleep_time if args and args.sleep_time else 5)
    
def parse_hanime_url(url):
    if not url:
        return None
    if "hanime.tv" in url:
        return url.split("/hentai/")[1].strip("/ ")
    if "freeanimehentai.net" in url:
        return url.split("/hentai/")[1].strip("/ ")
    return url.strip("/ ")



