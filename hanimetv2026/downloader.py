#from multiprocessing.util import debug
import glob
import shutil
import re
from numpy import rint
import requests
import subprocess
import time
import os
import yt_dlp
from urllib.parse import urlparse
from datetime import datetime

from hanimetv2026.colors import bcolors
from .api import Video, parse_hanime_url # search

#######################################################
#Helper functions:

def check_is_on_List(slug,args):
    if getattr(args, 'save_urls_dir', None) and os.path.exists(args.save_urls_dir):
        try:
            with open(args.save_urls_dir, "r") as f:
                downloaded_urls = set(line.strip() for line in f)
                url = f"https://hanime.tv/videos/hentai/{slug}"
                if url in downloaded_urls:
                    if args.verbose:
                        print(f"{bcolors.OKGREEN}[Verbose:] Checked if video URL exists for slug {slug} in {args.save_urls_dir} and found. Skipping Download.{bcolors.ENDC}")
                    return True
        except Exception as e:
            raise Exception(f"{bcolors.FAIL}[Hanimetv2026 Error33:] Error occurred while reading {args.save_urls_dir}: {e}{bcolors.ENDC}")
    if getattr(args, 'save_urls_dir', None) and os.path.exists(args.save_urls_dir) and args.verbose:
        print(f"{bcolors.WARNING}[Verbose:] Checked if video URL exists for slug {slug} in {args.save_urls_dir} and not found.{bcolors.ENDC}")

    if getattr(args, 'save_slugs_dir', None) and os.path.exists(args.save_slugs_dir):
        try:
            with open(args.save_slugs_dir, "r") as f:
                downloaded_slugs = set(line.strip() for line in f)
                if slug in downloaded_slugs:
                    if args.verbose:
                        print(f"{bcolors.OKGREEN}[Verbose:] Checked if video slug exists in {args.save_slugs_dir} and found. Skipping Download.{bcolors.ENDC}")
                return True
        except Exception as e:
            raise Exception(f"{bcolors.FAIL}[Hanimetv2026 Error34:] Error occurred while reading {args.save_slugs_dir}: {e}{bcolors.ENDC}")
    if getattr(args, 'save_slugs_dir', None) and os.path.exists(args.save_slugs_dir) and args.verbose:
        print(f"{bcolors.WARNING}[Verbose:] Checked if video slug exists in {args.save_slugs_dir} and not found.{bcolors.ENDC}")
    return False
            
def check_if_exists(slug,args):
    # If not found in logs, check if file exists in output directory as a fallback
    if not args.only_posters:
        if not args.title_as_filename:
            file_name = slug
        else:
            video = Video.from_slug(slug, args)
            file_name = video.title
        expected_filename = os.path.join(args.output_dir, f"{file_name}.mp4")

        if os.path.exists(expected_filename):
            mark_as_downloaded(slug, args)
            if args.verbose:
                print(f"{bcolors.OKGREEN}[Verbose:] Checked if video file exists for slug {slug} and found. Skipping Download.{bcolors.ENDC}")
            return True
        else:
            if args.verbose:
                print(f"{bcolors.OKCYAN}[Verbose:] Checked if video file exists for slug {slug}, not found. Proceeding with download.{bcolors.ENDC}")
    else:
        expected_filename = os.path.join(args.output_dir, f"{file_name}.jpg")
        if os.path.exists(expected_filename):
            mark_as_downloaded(slug, args)
            if args.verbose:
                print(f"{bcolors.OKGREEN}[Verbose:] Checked if poster file exists for slug {slug} and found. Skipping Download.{bcolors.ENDC}")
            return True
        else:
            if args.verbose:
                print(f"{bcolors.OKCYAN}[Verbose:] Checked if poster file exists for slug {slug}, not found. Proceeding with download.{bcolors.ENDC}")
    return False

def check_if_downloaded(slug, args):
    #Check if video is already downloaded
        if check_is_on_List(slug, args):
            return True
        if check_if_exists(slug, args):
            return True
        else:
            return False

def mark_as_downloaded(slug, args):
    if args.save_urls_dir:
        url = f"https://hanime.tv/videos/hentai/{slug}"
        with open(args.save_urls_dir, "a") as f:
            f.write(url + "\n")
    if args.save_slugs_dir:
        with open(args.save_slugs_dir, "a") as f:
            f.write(slug + "\n")

    if args.verbose and args.save_slugs_dir:
        print(f"{bcolors.OKGREEN}[Verbose:] Marked slug {slug} as downloaded.{bcolors.ENDC}")
    if args.verbose and args.save_urls_dir:
        url = f"https://hanime.tv/videos/hentai/{slug}"
        print(f"{bcolors.OKGREEN}[Verbose:] Marked URL for slug {url} as downloaded.{bcolors.ENDC}")

def mark_as_failed(slug, args):
    url = f"https://hanime.tv/videos/hentai/{slug}"
    with open(args.errors_dir, "a") as f:
        f.write(url + "\n")
    print(f"{bcolors.FAIL}[Hanimetv2026 Error1:] Marked URL {url} as failed.{bcolors.ENDC}")

def cleanup_temp_download_files(video, args):
    # Remove yt-dlp partial download files when a download fails.
    path = video.work_path_filename if args.working_dir and video.work_path_filename else video.output_path_filename
    if not path:
        return

    base = os.path.splitext(path)[0]
    patterns = [f"{base}*.part", f"{base}*.ytdl", f"{base}*.temp"]
    for pattern in patterns:
        for temp_file in glob.glob(pattern):
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    if args.verbose:
                        print(f"{bcolors.OKBLUE}[Verbose:] Removed temp file: {temp_file}{bcolors.ENDC}")
            except Exception as e:
                print(f"{bcolors.FAIL}[Hanimetv2026 Error2:] Failed to remove temp file {temp_file}: {e}{bcolors.ENDC}")

def download_picture(picture_file_path, URL, slug, args, video):
    if URL is None:
        print(f"{bcolors.FAIL}[Hanimetv2026 Error3:] No picture URL found for video {slug}. Skipping picture download.{bcolors.ENDC}")
        return None
    
    try:
        if args.verbose and args.verbose_ffmpeg:
            print(f"{bcolors.OKBLUE}[Verbose:] Downloading thumbnail from: {URL}{bcolors.ENDC}")
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://hanime.tv/"
        }
        response = requests.get(URL, timeout=10, headers=headers)
        if response.status_code == 200:
            with open(picture_file_path, 'wb') as f:
                f.write(response.content)
            if args.verbose and args.verbose_ffmpeg:
                print(f"{bcolors.OKGREEN}[Verbose:] Downloaded picture successfully: {os.path.basename(picture_file_path)} ({len(response.content)} bytes){bcolors.ENDC}")
        else:
            print(f"{bcolors.FAIL}[Hanimetv2026 Error4:] Failed to download picture: HTTP {response.status_code}{bcolors.ENDC}")
            return None
    except Exception as e:
        if args.verbose:
            print(f"{bcolors.FAIL}[Hanimetv2026 Error5:] Failed to download picture: {e}{bcolors.ENDC}")
        return None

    # Convert picture to JPG format for MP4 compatibility
    jpg_picture_path = os.path.splitext(picture_file_path)[0] + "_converted.jpg"
    convert_cmd = ["ffmpeg", "-y", "-i", picture_file_path, "-c:v", "mjpeg", "-f", "image2", jpg_picture_path]
    if args.verbose and args.verbose_ffmpeg:
        print(f"{bcolors.OKBLUE}[Verbose:] FFmpeg conversion command: {' '.join(convert_cmd)}{bcolors.ENDC}")
    convert_result = subprocess.run(convert_cmd, capture_output=True, encoding="utf-8", text=True)

    if convert_result.returncode != 0:
        print(f"{bcolors.FAIL}[Hanimetv2026 Error6:] ffmpeg conversion failed with return code {convert_result.returncode}{bcolors.ENDC}")
        if args.verbose and args.verbose_ffmpeg:
            print(f"{bcolors.FAIL}[STDERR:] {convert_result.stderr}{bcolors.ENDC}")
            print(f"{bcolors.FAIL}[STDOUT:] {convert_result.stdout}{bcolors.ENDC}")
    if convert_result.returncode == 0 and os.path.exists(jpg_picture_path):
        if args.verbose:
            print(f"{bcolors.OKGREEN}[Verbose:] Picture converted successfully{bcolors.ENDC}")
        return jpg_picture_path 
    else:
        print(f"{bcolors.FAIL}[Hanimetv2026 Error7:] ffmpeg conversion failed with return code {convert_result.returncode}{bcolors.ENDC}")
        return None

def download_poster(video, slug, args):
    poster_path = video.work_path_poster if args.working_dir else video.output_path_poster
    poster_url = video.metadata.cover if hasattr(video.metadata, "cover") else None

    download_success = download_picture(poster_path, poster_url, slug, args, video)

    if not download_success:
        print(f"{bcolors.FAIL}[Hanimetv2026 Error8:] Poster download failed{bcolors.ENDC}")
        return
    else:
        # Cleanup temp converted files only (not the original poster, which needs to be moved later)
        jpg_poster_path = os.path.splitext(poster_path)[0] + "_converted.jpg"
        try:
            if os.path.exists(jpg_poster_path):
                os.remove(jpg_poster_path)
        except Exception as e:
                print(f"{bcolors.FAIL}[Hanimetv2026 Error9:] Cleanup of temp poster file failed. Warning: {e}{bcolors.ENDC}")
        if args.verbose:
            print(f"{bcolors.OKGREEN}[Verbose:] temp poster file cleaned up successfully{bcolors.ENDC}")

def add_embedded_thumbnail(video, slug, args):
    thumbnail_path = video.work_path_thumbnail if args.working_dir else video.output_path_thumbnail
    thumbnail_url = video.metadata.thumbnail if hasattr(video.metadata, "thumbnail") else None

    thumb_to_use = download_picture(thumbnail_path, thumbnail_url, slug, args, video)
    
    if thumb_to_use is None:
        print(f"{bcolors.FAIL}[Hanimetv2026 Error10:] Thumbnail download failed. Skipping thumbnail embedding.{bcolors.ENDC}")
        return
    
    # Get the video path (the actual MP4 file to embed thumbnail into)
    video_path = video.work_path_filename if args.working_dir else video.output_path_filename
    temp_path2 = os.path.split(thumbnail_path)[0] + ".tmp2"
    if args.verbose:
        print(f"{bcolors.OKBLUE}[Verbose:] Embedding video thumbnail into MP4...{bcolors.ENDC}")
    
    cmd_embeding_thumbnail = [
        "ffmpeg", "-y", "-i", video_path, "-i", thumb_to_use,
        "-map", "0", "-map", "1",
        "-c:v", "copy", "-c:a", "copy",
        "-disposition:v:1", "attached_pic",
        "-f", "mp4", temp_path2
    ]

    if any([args.verbose, args.verbose_ffmpeg]):
        print(f"{bcolors.OKBLUE}[Verbose:] FFmpeg thumbnail command: {' '.join(cmd_embeding_thumbnail)}{bcolors.ENDC}")
    result2 = subprocess.run(cmd_embeding_thumbnail, capture_output=True, encoding="utf-8", text=True)

    if result2.returncode == 0:
        os.replace(temp_path2, video_path)
        if args.verbose:
            print(f"{bcolors.OKGREEN}[Verbose:] Thumbnail embedded successfully{bcolors.ENDC}")
    else:
        err_msg = result2.stderr or ""
        print(f"{bcolors.FAIL}[Hanimetv2026 Error11:] ffmpeg thumbnail failed with return code {result2.returncode}{bcolors.ENDC}")
        if any([args.verbose, args.verbose_ffmpeg]):
            print(f"{bcolors.FAIL}[STDERR:] {result2.stderr}{bcolors.ENDC}")
            print(f"{bcolors.FAIL}[STDOUT:] {result2.stdout}{bcolors.ENDC}")

        if "CBC boundary" in err_msg or "CBC boundary" in (result2.stdout or ""):
            print(f"{bcolors.WARNING}[Hanimetv2026 Warning:] CBC boundary warning from ffmpeg during thumbnail embedding; skipping embedding and continuing.{bcolors.ENDC}")
        else:
            if args.verbose and args.verbose_ffmpeg:
                print(f"{bcolors.FAIL}[Hanimetv2026 Error12:] Thumbnail embedding failed with non-CBC error; leaving source intact.{bcolors.ENDC}")

    # Cleanup temp files: converted thumbnail and original downloaded thumbnail (embedded into the video)
    jpg_thumbnail_path = os.path.splitext(thumbnail_path)[0] + "_converted.jpg"
    try:
        if os.path.exists(jpg_thumbnail_path):
            os.remove(jpg_thumbnail_path)
        if os.path.exists(thumbnail_path):
            os.remove(thumbnail_path)
    except Exception as e:
        if args.verbose:
            print(f"{bcolors.FAIL}[Hanimetv2026 Error13:] Cleanup of temp thumbnail file failed. Warning: {e}{bcolors.ENDC}")
    if args.verbose:
        print(f"{bcolors.OKGREEN}[Verbose:] temp thumbnail file cleaned up successfully{bcolors.ENDC}")


def add_emmbeded_metadata_with_ffmpeg(video, args):

    #Get metadata from video object

    temp_video_file_path =  os.path.split(video.work_path_filename)[0] + ".tmp" if args.working_dir else os.path.split(video.output_path_filename)[0] + ".tmp"
    # Escape metadata values for ffmpeg
    title = video.title.replace('"', '\\"')
    brand = video.metadata.brand.replace('"', '\\"')
    description = video.metadata.description.replace('"', '\\"')
    if not args.no_merged_description: #By default False, so description is merged with stats.
        description = description + "\n\n" + f"Likes: {video.metadata.likes} | Dislikes: {video.metadata.dislikes} | Monthly_Rank: {video.metadata.monthly_rank}"
    tags = ','.join(video.metadata.tags).replace('"', '\\"')
    release_date = ""

    try:
        if getattr(video.metadata, "released_at_unix", 0):
            release_date = datetime.fromtimestamp(video.metadata.released_at_unix).strftime("%Y-%m-%d")
        elif getattr(video.metadata, "created_at_unix", 0):
            release_date = datetime.fromtimestamp(video.metadata.created_at_unix).strftime("%Y-%m-%d")
    except Exception:
        pass

    #Embed metadata with ffmpeg

    if args.verbose:
        print(f"{bcolors.OKBLUE}[Verbose:] Adding metadata with ffmpeg...{bcolors.ENDC}")
    
    cmd = [
        "ffmpeg", "-y", "-i", video.work_path_filename if video.work_path_filename else video.output_path_filename,
        "-c:v", "copy", "-c:a", "copy",
        "-metadata", f"title={title}",
        "-metadata", f"artist={brand}",
        "-metadata", f"comment={description}",
        "-metadata", f"genre={tags}",
        "-metadata", f"date={release_date}",
        "-f", "mp4", temp_video_file_path
    ]
    
    if args.verbose and args.verbose_ffmpeg:
        print(f"{bcolors.OKBLUE}[Hanimetv2026 info:] FFmpeg command: {' '.join(cmd)}{bcolors.ENDC}")
    
    result = subprocess.run(cmd, capture_output=True, encoding='utf-8', text=True)
    if result.returncode == 0:
        os.replace(temp_video_file_path, video.work_path_filename if video.work_path_filename else video.output_path_filename)
        if args.verbose and args.verbose_ffmpeg:
            print(f"{bcolors.OKGREEN}[Hanimetv2026 info:] Metadata added successfully{bcolors.ENDC}")
    else:
        err_msg = result.stderr or ""
        print(f"{bcolors.FAIL}[Hanimetv2026 Error14:] ffmpeg metadata failed with return code {result.returncode}{bcolors.ENDC}")
        if any([args.verbose, args.verbose_ffmpeg]):
            print(f"STDERR: {result.stderr}")
            print(f"STDOUT: {result.stdout}")

        if "CBC boundary" in err_msg or "CBC boundary" in (result.stdout or ""):
            if args.verbose:
                print(f"{bcolors.WARNING}[Hanimetv2026 Warning:] CBC boundary warning from ffmpeg during metadata embedding; skipping metadata update and continuing.{bcolors.ENDC}")
        else:
            if args.verbose:
                print(f"{bcolors.FAIL}[Hanimetv2026 Error15:] Metadata embedding failed with non-CBC error; leaving source intact.{bcolors.ENDC}")

        # Remove temp file created by ffmpeg on failure
        try:
            if os.path.exists(temp_video_file_path):
                os.remove(temp_video_file_path)
        except Exception as e:
            if args.verbose:
                print(f"{bcolors.FAIL}[Hanimetv2026 Error16:] Cleanup of temp file failed. Warning: {e}{bcolors.ENDC}")


def move_file_to_output(video, args):
    try:
        shutil.move(video.work_path_filename, video.output_path_filename)
    except Exception as e:
        print(f"{bcolors.WARNING}[Hanimetv2026 Warning:] Video move across volumes failed, falling back to copy: {e}{bcolors.ENDC}")
        shutil.copy2(video.work_path_filename, video.output_path_filename)
        os.remove(video.work_path_filename)

    if args.poster_download:
        try:
            shutil.move(video.work_path_poster, video.output_path_poster)
        except Exception as e:
            print(f"{bcolors.WARNING}[Hanimetv2026 Warning:] Poster move across volumes failed, falling back to copy: {e}{bcolors.ENDC}")
            shutil.copy2(video.work_path_poster, video.output_path_poster)
            os.remove(video.work_path_poster)

def save_slug(slug, args):
    with open(args.save_slugs_dir, "a") as f:
        f.write(slug + "\n")

def save_url(slug, args):
    url = f"https://hanime.tv/videos/hentai/{slug}"
    with open(args.save_urls_dir, "a") as f:
        f.write(url + "\n")

def web_scrape_ALL_videos_by_search(cmd, args, search_term):
    page = args.continue_from_page
    
    while True:
        if not args.brand:
            url = f"https://hanime.tv/browse/tags/{search_term}?page={page}"
        else:
            url = f"https://hanime.tv/browse/brands/{search_term}?page={page}"

        print("")
        print("--------------------------------------------------")
        print("--------------------------------------------------")
        print(f"{bcolors.INFO}[Hanimetv2026 Info:] Start scraping {url}...{bcolors.ENDC}")

        matches = []
        #Retry logic for scraping one page
        for attempt in range(args.retrys):
            try:
                response = requests.get(url, timeout=10)
                if not response.ok:
                    if attempt == args.retrys - 1:
                        print(f"{bcolors.FAIL}[Hanimetv2026 Error17:] Max retries reached while scraping page {page} for {search_term}: {e}{bcolors.ENDC}")
                        return
                    print(f"{bcolors.WARNING}[Hanimetv2026 Warning:] Error scraping hanimetv page {page}. Response: {response.status_code}: {response.reason}{bcolors.ENDC}")
                    print(f"{bcolors.WARNING}[Hanimetv2026 Warning:] Retrying...{bcolors.ENDC}")
                else:
                    response.raise_for_status()
                    html = response.text
                    matches = re.findall(r'/videos/hentai/([^\'"&\s]+)', html)
                    if not matches:
                        print(f"{bcolors.INFO}[Hanimetv2026 Info:] No more pages for {search_term}. Stopping Search.{bcolors.ENDC}")
                        return
            except Exception as e:
                if attempt == args.retrys - 1:
                    print(f"{bcolors.FAIL}[Hanimetv2026 Error18:] Max retries reached while scraping page {page} for {search_term}: {e}{bcolors.ENDC}")
                    return
                print(f"{bcolors.WARNING}[Hanimetv2026 Warning:] Attempt {attempt + 1} failed to scrape page {page} for {search_term}. Error: {e}.{bcolors.ENDC}")
                print(f"{bcolors.WARNING}[Hanimetv2026 Warning:] Retrying...{bcolors.ENDC}")
                time.sleep(args.sleep_time)

        unique_slugs = list(dict.fromkeys(matches))
        """  Legacy-code maybe removed in future versions.  
        if not unique_slugs:
            print(f"{bcolors.INFO}[Hanimetv2026 Info:] No more unique slugs for {search_term}. Stopping Search.{bcolors.ENDC}")
            break
        """

        print("")
        print("--------------------------------------------------")
        print(f"{bcolors.INFO}[Hanimetv2026 Info:] Found {len(unique_slugs)} unique slugs on page {page} for {search_term}.{bcolors.ENDC}")

        # Download each video on this page
        for slug in unique_slugs:

            try:
                video = Video.from_slug(slug, args)
            except Exception as e:
                print(e)
                print(f"{bcolors.FAIL}[Hanimetv2026 Error19:] Marking as failed and continuing...{bcolors.ENDC}")
                mark_as_failed(slug, args)
                continue

            if check_if_downloaded(slug, args):
                print(f"{bcolors.OKCYAN}[Hanimetv2026 Info:] Checked if video {slug} is already downloaded. Skipping download.{bcolors.ENDC}")
                continue
            
            try:
                download(video, slug, cmd, args)
            except Exception as e:
                print(f"{bcolors.FAIL}[Hanimetv2026 Error20:] Failed to download video {slug}: {e}{bcolors.ENDC}")

        page += 1
        time.sleep(args.sleep_time)  # Sleep between page requests

def web_scrape_NEW_videos_by_search(cmd, args, search_term):
    page = args.continue_from_page

    #Get all unique slugs for the search term, page by page, until no more pages are found
    #Then downloading them in reverse order to avoid downloading the same video twice if the script is stopped or restarted
    
    matches = []
    page_scrapping_done = False
    while page_scrapping_done is False:
        if not args.brand:
            url = f"https://hanime.tv/browse/tags/{search_term}?page={page}"
        else:
            url = f"https://hanime.tv/browse/brands/{search_term}?page={page}"

        print("")
        print("--------------------------------------------------")
        print("--------------------------------------------------")
        print(f"{bcolors.INFO}[Hanimetv2026 Info:] Start scraping {url}...{bcolors.ENDC}")

        #Retry logic for scraping one page
        for attempt in range(args.retrys):
            try:
                response = requests.get(url, timeout=10)
                if not response.ok:
                    if attempt == args.retrys - 1:
                        raise Exception(f"Response: {response.status_code}: {response.reason}")
                    print(f"{bcolors.WARNING}[Hanimetv2026 Warning:] Error scraping hanimetv page {page}. Response: {response.status_code}: {response.reason}{bcolors.ENDC}")
                    print(f"{bcolors.WARNING}[Hanimetv2026 Warning:] Retrying... attempt {attempt + 1}/{args.retrys}{bcolors.ENDC}")
                else:
                    response.raise_for_status()
                    html = response.text
                    new_matches = re.findall(r'/videos/hentai/([^\'"&\s]+)', html)
                    if args.verbose:
                        print(f"{bcolors.OKBLUE}[Verbose:] Found {len(new_matches)} slugs on page {page} for {search_term}.{bcolors.ENDC}")
                    unique_new_matches = list(new_matches) #copy List
                    for slug in new_matches:
                        if check_if_downloaded(slug, args):
                            if page_scrapping_done is False:
                                print(f"{bcolors.OKCYAN}[Hanimetv2026 Info:] Checked: video {slug} is already downloaded. Stop scraping.{bcolors.ENDC}")
                                page_scrapping_done = True  # Stop searching for new pages if a downloaded video is found
                            unique_new_matches.remove(slug)
                        else:
                            matches.extend([slug])  # Add only new slugs to the matches list
                            if args.verbose:
                                print(f"{bcolors.OKCYAN}[Verbose:] added video {slug} to download queue.{bcolors.ENDC}")

                    if not unique_new_matches:
                        print(f"{bcolors.INFO}[Hanimetv2026 Info:] No more pages for {search_term}. Stopping Search.{bcolors.ENDC}")
                        page_scrapping_done = True
                        break
                    else:
                        print("Verbose Test: exiting retry loop after successful scrape.")
                        break  # Exit the retry loop if successful
            except Exception as e:
                if attempt == args.retrys - 1:
                    raise Exception(f"{bcolors.FAIL}[Hanimetv2026 Error21:] Max retries reached while scraping page {page} for {search_term}: {e}{bcolors.ENDC}")
                print(f"{bcolors.WARNING}[Hanimetv2026 Warning:] Attempt {attempt + 1} failed to scrape page {page} for {search_term}. Error: {e}.{bcolors.ENDC}")
                print(f"{bcolors.WARNING}[Hanimetv2026 Warning:] Retrying...{bcolors.ENDC}")
            time.sleep(args.sleep_time)
        if not page_scrapping_done:
            print("Verbose Test: wait for next page request.")
            page += 1
            time.sleep(args.sleep_time)  # Sleep between page requests
     
    unique_slugs = list(dict.fromkeys(matches))
    """  
    Legacy-code maybe removed in future versions.
    if not unique_slugs:
        print(f"{bcolors.INFO}[Hanimetv2026 Info:] No more unique slugs for {search_term}. Stopping Search.{bcolors.ENDC}")
        break
    """      
    
    print("--------------------------------------------------")
    print(f"{bcolors.INFO}[Hanimetv2026 Info:] Scraping Done. Start Download{bcolors.ENDC}")
    print(f"{bcolors.INFO}[Hanimetv2026 Info:] Found {len(unique_slugs)} unique slugs for {search_term} in updating mode.{bcolors.ENDC}")

    #reverse the list of slugs to download the latest videos first
    unique_slugs.reverse()

    # Download each video in matches
    for slug in unique_slugs:

        try:
            video = Video.from_slug(slug, args)
        except Exception as e:
            print(e)
            print(f"{bcolors.FAIL}[Hanimetv2026 Error22:] Marking as failed and continuing...{bcolors.ENDC}")
            mark_as_failed(slug, args)
            continue

        if check_if_downloaded(slug, args):
            print(f"{bcolors.OKCYAN}[Hanimetv2026 Info:] Checked if video {slug} is already downloaded. Skipping download.{bcolors.ENDC}")
            continue
        
        try:
            download(video, slug, cmd, args)
        except Exception as e:
            print(f"{bcolors.FAIL}[Hanimetv2026 Error23:] Failed to download video {slug}: {e}{bcolors.ENDC}")

        time.sleep(args.sleep_time)  # Sleep between video downloads

    


#######################################################
#######################################################
#Main functions:

def start_video_download(args):
    os.makedirs(os.path.dirname(args.output_dir), exist_ok=True) #Ensure output directory exists
    if args.working_dir:
        os.makedirs(args.working_dir, exist_ok=True) #Ensure working directory exists if specified

    ### Combine all downloader args
    cmd = ["yt-dlp"]
    
    #Donwload options
    cmd.extend(["-f", f"bestvideo[height<={args.resolution}]+bestaudio/best[height<={args.resolution}]/best"])
    
    if args.downloader_args:
        cmd.extend(["--downloader-args", " ".join(args.downloader_args)])

    ###################################
    ### Mode switch
    #--video
    if args.video:
        slug = parse_hanime_url(args.video)
        if slug:
            video = Video.from_slug(slug, args)
            if not check_if_downloaded(slug, args):
                download(video, slug, cmd, args)
        else:
            raise Exception(f"{bcolors.FAIL}[Hanimetv2026 Error24:] Invalid video URL: {args.video}{bcolors.ENDC}")

    #--batch-file
    elif args.batch_file:
        with open(args.batch_file, 'r') as f:
            for line in f:
                url = line.strip()
                slug = parse_hanime_url(url)
                if not slug:
                    print(f"{bcolors.FAIL}[Hanimetv2026 Error25:] Invalid video URL in batch file: {url}. Marking as failed and continuing...{bcolors.ENDC}")
                    with open(args.errors_dir, "a") as f:
                            f.write(url + "\n")
                    continue
                try:
                    video = Video.from_slug(slug, args)
                except Exception as e:
                    print(e)
                    print(f"{bcolors.FAIL}[Hanimetv2026 Error26:] Marking as failed and continuing...{bcolors.ENDC}")
                    mark_as_failed(slug, args)
                    continue

                #special add_only_metadata: add metadata and poster to already downloaded videos in batch file, without re-downloading the video. 
                if args.add_only_metadata and os.path.exists(video.output_path_filename):
                    if args.no_metadata:
                        raise Exception(f"{bcolors.FAIL}[Hanimetv2026 Error27:] Error: --add-only-metadata cannot be used together with --no-metadata. Please choose one or the other.{bcolors.ENDC}")
                    add_emmbeded_metadata_with_ffmpeg(video, args)
                    if not args.no_thumbnail:
                        add_embedded_thumbnail(video, slug, args)
                    mark_as_downloaded(slug, args) #In case it was only marked as failed before
                    continue
                ################################
                if check_if_downloaded(slug, args):
                    continue
                try:
                    download(video, slug, cmd, args)
                except Exception as e:
                    print(e)
                    print(f"{bcolors.FAIL}[Hanimetv2026 Error28:] Marking as failed and continuing...{bcolors.ENDC}")
                time.sleep(args.sleep_time)
    
    #--all
    elif args.all:
        # Download all videos by searching for "uncensored" and "censored" tags
        tags = args.tags #By deault ["uncensored","censored"] 

        for tag in tags:
            web_scrape_ALL_videos_by_search(cmd, args, tag)
    
    # --search 
    elif args.search:
        #Check for incompatible arguments
        search_terms =""
        if args.tags and args.brand:
            return Exception(f"{bcolors.FAIL}[Hanimetv2026 Error29:] --tag and --brand cannot be used together with --search. Please choose one or the other.{bcolors.ENDC}")
        #Determine search term
        if args.tags:
            search_terms = args.tags #OR-Search! Will search each tag separately and combine results, currently only supports searching one tag
        elif args.brand:
            search_terms = args.brand #OR-Search! Will search each brand separately and combine results, currently only supports searching one brand
        else:
            return Exception(f"{bcolors.FAIL}[Hanimetv2026 Error30:] Error: --search requires either --tag or --brand to be specified.{bcolors.ENDC}")
        
        if len(search_terms) > 1:
            print(f"{bcolors.WARNING}[Hanimetv2026 Warning:] Searching for multiple terms: {search_terms}, separately. Results will be combined but duplicates may occur if videos have multiple matching tags/brands and no download archive is specified.{bcolors.ENDC}")
            #ask for conformation
            confirmation = input("Do you want to proceed? (y/n): ")
            if confirmation.lower() != 'y':
                raise Exception(f"{bcolors.FAIL}[Hanimetv2026 Error31:] User aborted search.{bcolors.ENDC}")

        #Update-modifaction
        if args.update:
            mode_args = [args.batch_file, args.video, args.all]
            if not args.search:
                print(bcolors.WARNING + "[Hanimetv2026 info:] Update must be used with --search" + bcolors.ENDC)
                exit(1)
            if sum(arg is not None and arg != False for arg in mode_args) > 0:
                print(bcolors.WARNING + "[Hanimetv2026 info:] Update can only be used with --search" + bcolors.ENDC)
                exit(1)
            elif args.verbose:
                print(bcolors.OKGREEN + "[Verbose:] Update commands seems right." + bcolors.ENDC)
                print()

            for search_term in search_terms:
                web_scrape_NEW_videos_by_search(cmd, args, search_term)
        else:
            for search_term in search_terms:
                web_scrape_ALL_videos_by_search(cmd, args, search_term)
    
    else:
        return Exception(f"{bcolors.FAIL}[Hanimetv2026 Error32:] No valid mode argument provided. Use --video, --all, --batch-file, --search.{bcolors.ENDC}")


def download(video, slug, cmd, args):
    
    #Path options
    if args.output_dir and not args.working_dir:
        cmd.extend(["-o", video.output_path_filename])
    elif args.output_dir and args.working_dir:
        cmd.extend(["-o", video.work_path_filename])

    # Setup env for subprocess to ensure UTF-8 encoding
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"

    sites_to_try = [
        f"https://hanime.tv/videos/hentai/{slug}",
        # f"https://freeanimehentai.net/videos/hentai/{slug}", #Currently not working
    ]
    success = False
    if not args.only_posters:
        print("")
        print("--------------------------------------------------")
        print(f"{bcolors.OKBLUE}[Hanimetv2026 info:] Starting download for: {video.title} (Slug: {slug}){bcolors.ENDC}")
        #Download
        
        for video_site in sites_to_try:
            current_cmd = cmd + [video_site]
            for attempt in range(args.retrys):
                try:
                    if not args.video:
                        print(f'{bcolors.OKBLUE}[Hanimetv2026 info:] Waiting {args.sleep_time} seconds before downloading{bcolors.ENDC}')
                        print(f'{bcolors.OKBLUE}[Hanimetv2026 info:] slug {slug} from {video_site} (Attempt {attempt + 1}/{args.retrys})...{bcolors.ENDC}')
                        time.sleep(args.sleep_time) 

                    if args.verbose and args.verbose_ffmpeg:
                        print(f"{bcolors.OKBLUE}[Verbose:] Running yt-dlp command: {' '.join(current_cmd)}{bcolors.ENDC}")

                    if args.skip_unavailable_fragments and args.verbose:
                        print(f"{bcolors.OKBLUE}[Verbose:] Skipping unavailable fragments.{bcolors.ENDC}")
                        current_cmd = current_cmd + ["--skip-unavailable-fragments"]
                    
                    result = subprocess.run(
                        current_cmd,
                        capture_output=False,
                        text=True,
                        encoding="utf-8",
                        errors='replace',
                        env=env,
                        timeout=300,
                    )

                    if result.returncode == 0:
                        success = True
                        if args.verbose:
                            print(f"{bcolors.OKGREEN}[Verbose:] yt-dlp completed downloaded video successfully for slug {slug} from {video_site}.{bcolors.ENDC}")
                        break

                    #Sometimes yt-dlp packages misses or an error occurs, this tries to catch it and retry the download instead of failing immediately. 
                    error_output = (result.stderr or "") + "\n" + (result.stdout or "")
                    print(f"{bcolors.WARNING}[Hanimetv2026 Warning:] yt-dlp failed with return code {result.returncode}{bcolors.ENDC}")
                    if args.verbose:
                        print(f"{bcolors.WARNING}[Verbose:] Error output: {error_output}{bcolors.ENDC}")
                except Exception as e:
                    print(f"{bcolors.WARNING}[Hanimetv2026 Warning:] An error occurred while downloading {slug} from {video_site}: {e}{bcolors.ENDC}")
                if attempt < args.retrys - 1:
                    print(f"{bcolors.WARNING}[Hanimetv2026 Warning:] Retrying download for slug {slug} from {video_site}, attempt {attempt+1}/{args.retrys}.{bcolors.ENDC}")
                                


    if not success and not args.only_posters:
        cleanup_temp_download_files(video, args)
        if args.errors_dir:
            mark_as_failed(slug, args)
        return Exception(f"Failed to download video {slug} after trying all Sites")

    #Post-processing
    if not args.no_metadata and not args.only_posters:
        add_emmbeded_metadata_with_ffmpeg(video, args)
    
    if not args.no_thumbnail and not args.only_posters:
        add_embedded_thumbnail(video, slug, args)
    
    if args.poster_download or args.only_posters:
        download_poster(video, slug, args)

    if args.working_dir:
        move_file_to_output(video, args)

    mark_as_downloaded(slug, args)
    
    return True
  
