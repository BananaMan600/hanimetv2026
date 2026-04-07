#from multiprocessing.util import debug
import glob
import shutil
import re
import requests
import subprocess
import time
import os
import yt_dlp
from urllib.parse import urlparse
from datetime import datetime
from .api import Video, parse_hanime_url # search

#######################################################
#Helper functions:

def check_is_on_List(video, slug,args):
    if getattr(args, 'save_urls_dir', None) and os.path.exists(args.save_urls_dir):
        with open(args.save_urls_dir, "r") as f:
            downloaded_urls = set(line.strip() for line in f)
            url = f"https://hanime.tv/videos/hentai/{slug}"
            if url in downloaded_urls:
                return True

    if getattr(args, 'save_slugs_dir', None) and os.path.exists(args.save_slugs_dir):
        with open(args.save_slugs_dir, "r") as f:
            downloaded_slugs = set(line.strip() for line in f)
            if slug in downloaded_slugs:
                return True
            
def check_if_exists(video, slug,args):
    # If not found in logs, check if file exists in output directory as a fallback
    expected_filename = video.output_path_filename
    if os.path.exists(expected_filename):
        mark_as_downloaded(slug, args)
        if args.verbose:
            print(f"Checked if video file exists for slug {slug} and found.")
        return True
    
    if args.only_posters:
        expected_filename = video.output_path_poster
        if os.path.exists(expected_filename):
            mark_as_downloaded(slug, args)
            if args.verbose:
                print(f"Checked if poster file exists for slug {slug} and found.")
            return True
        
    if args.verbose:
        print(f"Checked if file exists for slug {slug}, not found. Proceeding with download.")
    return False

def check_if_downloaded(video, slug, args):
    #Check if video is already downloaded
    if check_is_on_List(video, slug, args):
        print(f"Video {slug} already downloaded (marked in archive), skipping.")
        return True
    if check_if_exists(video, slug, args):
        print(f"Video {slug} already downloaded (exists in output), skipping.")
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
    if args.verbose and args.save_urls_dir and args.save_slugs_dir:
        print(f"Marked slug {slug} as downloaded.")

def mark_as_failed(slug, args):
    with open(args.errors_dir, "a") as f:
        f.write(f"https://hanime.tv/videos/hentai/{slug}\n")


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
                    if getattr(args, 'verbose', False):
                        print(f"Removed temp file: {temp_file}")
            except Exception as e:
                if getattr(args, 'verbose', False):
                    print(f"Failed to remove temp file {temp_file}: {e}")


def download_picture(picture_file_path, URL, slug, args, video):
    if URL is None:
        if args.verbose:
            print(f"No thumbnail URL found for video {slug}. Skipping thumbnail download.")
        return None
    
    try:
        if args.verbose and args.verbose_ffmpeg:
            print(f"Downloading thumbnail from: {URL}")
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://hanime.tv/"
        }
        response = requests.get(URL, timeout=10, headers=headers)
        if response.status_code == 200:
            with open(picture_file_path, 'wb') as f:
                f.write(response.content)
            if args.verbose and args.verbose_ffmpeg:
                print(f"Downloaded picture: {os.path.basename(picture_file_path)} ({len(response.content)} bytes)")
        else:
            if args.verbose:
                print(f"Failed to download picture: HTTP {response.status_code}")
            return None
    except Exception as e:
        if args.verbose:
            print(f"Failed to download picture: {e}")
        return None

    # Convert picture to JPG format for MP4 compatibility
    jpg_picture_path = os.path.splitext(picture_file_path)[0] + "_converted.jpg"
    convert_cmd = ["ffmpeg", "-y", "-i", picture_file_path, "-c:v", "mjpeg", "-f", "image2", jpg_picture_path]
    convert_result = subprocess.run(convert_cmd, capture_output=True, text=True)
    if convert_result.returncode == 0 and os.path.exists(jpg_picture_path):
        if args.verbose:
            if(args.add_only_metadata):
                print(f"Thumbnail downloaded and converted successfully")
            elif os.path.exists(video.work_path_poster if args.working_dir else video.output_path_poster):
                print(f"Poster downloaded and converted successfully")
            else:
                print(f"Thumbnail downloaded and converted successfully")
        return jpg_picture_path 
    else:
        if args.verbose:
            print(f"ffmpeg conversion failed with return code {convert_result.returncode}")
        return None
    

def download_poster(video, slug, args):
    poster_path = video.work_path_poster if args.working_dir else video.output_path_poster
    poster_url = video.metadata.cover if hasattr(video.metadata, "cover") else None

    download_picture(poster_path, poster_url, slug, args, video)

    # Cleanup temp converted files only (not the original poster, which needs to be moved later)
    jpg_poster_path = os.path.splitext(poster_path)[0] + "_converted.jpg"
    try:
        if os.path.exists(jpg_poster_path):
            os.remove(jpg_poster_path)
    except Exception as e:
        if args.verbose:
            print(f"Cleanup warning: {e}")


def add_embedded_thumbnail(video, slug, args):
    thumbnail_path = video.work_path_thumbnail if args.working_dir else video.output_path_thumbnail
    thumbnail_url = video.metadata.thumbnail if hasattr(video.metadata, "thumbnail") else None

    thumb_to_use = download_picture(thumbnail_path, thumbnail_url, slug, args, video)
    
    if thumb_to_use is None:
        if args.verbose:
            print(f"Skipping thumbnail embedding due to download/conversion failure")
        return
    
    # Get the video path (the actual MP4 file to embed thumbnail into)
    video_path = video.work_path_filename if args.working_dir else video.output_path_filename
    temp_path2 = os.path.split(thumbnail_path)[0] + ".tmp2"
    if args.verbose:
        print(f"Embedding video thumbnail into MP4...")
    
    cmd_embeding_thumbnail = [
        "ffmpeg", "-y", "-i", video_path, "-i", thumb_to_use,
        "-map", "0", "-map", "1",
        "-c:v", "copy", "-c:a", "copy",
        "-disposition:v:1", "attached_pic",
        "-f", "mp4", temp_path2
    ]

    if any([args.verbose, args.verbose_ffmpeg]):
        print(f"FFmpeg thumbnail command: {' '.join(cmd_embeding_thumbnail)}")
    result2 = subprocess.run(cmd_embeding_thumbnail, capture_output=True, text=True)

    if result2.returncode == 0:
        os.replace(temp_path2, video_path)
        if args.verbose:
            print(f"Thumbnail embedded successfully")
    else:
        err_msg = result2.stderr or ""
        if args.verbose:
            print(f"ffmpeg thumbnail failed with return code {result2.returncode}")
            print(f"STDERR: {result2.stderr}")
            print(f"STDOUT: {result2.stdout}")

        if "CBC boundary" in err_msg or "CBC boundary" in (result2.stdout or ""):
            if args.verbose:
                print("CBC boundary warning from ffmpeg during thumbnail embedding; skipping embedding and continuing.")
        else:
            if args.verbose:
                print("Thumbnail embedding failed with non-CBC error; leaving source intact.")

    # Cleanup temp files: converted thumbnail and original downloaded thumbnail (embedded into the video)
    jpg_thumbnail_path = os.path.splitext(thumbnail_path)[0] + "_converted.jpg"
    try:
        if os.path.exists(jpg_thumbnail_path):
            os.remove(jpg_thumbnail_path)
        if os.path.exists(thumbnail_path):
            os.remove(thumbnail_path)
    except Exception as e:
        if args.verbose:
            print(f"Cleanup warning: {e}")


def add_emmbeded_metadata(video, args):
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

    if args.verbose and args.verbose_ffmpeg:
        print(f"Adding metadata with ffmpeg...")
    
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
        print(f"FFmpeg command: {' '.join(cmd)}")
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        os.replace(temp_video_file_path, video.work_path_filename if video.work_path_filename else video.output_path_filename)
        if args.verbose:
            print(f"Metadata added successfully")
    else:
        err_msg = result.stderr or ""
        if args.verbose:
            print(f"ffmpeg metadata failed with return code {result.returncode}")
            print(f"STDERR: {result.stderr}")
            print(f"STDOUT: {result.stdout}")

        if "CBC boundary" in err_msg or "CBC boundary" in (result.stdout or ""):
            if args.verbose:
                print("CBC boundary warning from ffmpeg during metadata embedding; skipping metadata update and continuing.")
        else:
            if args.verbose:
                print("Metadata embedding failed with non-CBC error; leaving source intact.")

        # Remove temp file created by ffmpeg on failure
        try:
            if os.path.exists(temp_video_file_path):
                os.remove(temp_video_file_path)
        except Exception as e:
            if args.verbose:
                print(f"Cleanup warning: {e}")


def move_file_to_output(video, args):
    try:
        shutil.move(video.work_path_filename, video.output_path_filename)
    except Exception as e:
        print(f"Warning: Video move across volumes failed, falling back to copy: {e}")
        shutil.copy2(video.work_path_filename, video.output_path_filename)
        os.remove(video.work_path_filename)

    if args.poster_download:
        try:
            shutil.move(video.work_path_poster, video.output_path_poster)
        except Exception as e:
            print(f"Warning: Poster move across volumes failed, falling back to copy: {e}")
            shutil.copy2(video.work_path_poster, video.output_path_poster)
            os.remove(video.work_path_poster)

def save_slug(slug, args):
    with open(args.save_slugs_dir, "a") as f:
        f.write(slug + "\n")

def save_url(slug, args):
    url = f"https://hanime.tv/videos/hentai/{slug}"
    with open(args.save_urls_dir, "a") as f:
        f.write(url + "\n")

def web_scrape_all_videos_by_search(cmd, args, search_term):
    page_retry_count = 0
    page = args.continue_from_page
    
    while True:
        if not args.brand:
            url = f"https://hanime.tv/browse/tags/{search_term}?page={page}"
        else:
            url = f"https://hanime.tv/browse/brands/{search_term}?page={page}"
        print(f"Scraping {url}...")
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            html = response.text
            matches = re.findall(r'/videos/hentai/([^\'"&\s]+)', html)
            if not matches:
                print(f"No more pages for {search_term}")
                break

            # Remove duplicates so page count matches processed slugs
            unique_slugs = list(dict.fromkeys(matches))
            if not unique_slugs:
                print(f"No more unique slugs for {search_term}")
                break

            print("--------------------------------------------------")
            print("--------------------------------------------------")
            print(f"Found {len(unique_slugs)} unique slugs on page {page} for {search_term}")

            # Download each video on this page
            for slug in unique_slugs:
                try:
                    video = Video.from_slug(slug, args)
                except Exception as e:
                    print(f"Skipping slug {slug} due to metadata error: {e}")
                    continue

                video = Video.from_slug(slug, args)
                if check_if_downloaded(video, slug, args):
                    if args.verbose and args.update:
                        print(f"Checked for recent videos on search_{search_term}. {slug}, already downloaded, stopping update.")
                        return
                    else:
                        print(f"Slug {slug} already downloaded, skipping.")
                    continue

                download(video, slug, cmd, args)
                

            page += 1
            time.sleep(args.sleep_time)  # Sleep between page requests
        except:
            print(f"Error scraping page {page} for {search_term}, retrying...")
            page_retry_count += 1
            sleep_time = args.sleep_time * page_retry_count * 2
            print(f"Sleeping for {sleep_time} seconds before retrying...")
            if page_retry_count >= args.retrys:
                print(f"Max retries reached for page {page} for {search_term}. Stop scraping this search term.")
                break












#######################################################
#Main functions:

def start_video_download(args):
    os.makedirs(os.path.dirname(args.output_dir), exist_ok=True) #Ensure output directory exists
    if args.working_dir:
        os.makedirs(args.working_dir, exist_ok=True) #Ensure working directory exists if specified

    ### Combine all downloader args
    cmd = ["yt-dlp"]
    
    #Donwload options
    if args.resolution:
        cmd.extend(["-f", f"bestvideo[height<={args.resolution}]+bestaudio/best[height<={args.resolution}]/best"])
    
    if args.downloader_args:
        cmd.extend(["--downloader-args", " ".join(args.downloader_args)])
    
    ### Mode switch
    #--video
    if args.video:
        slug = parse_hanime_url(args.video)
        if slug:
            video = Video.from_slug(slug, args)
            if not check_if_downloaded(video, slug, args):
                download(video, slug, cmd, args)
        else:
            print(f"Invalid video URL: {args.video}")

    #--batch-file
    elif args.batch_file:
        with open(args.batch_file, 'r') as f:
            for line in f:
                url = line.strip()
                slug = parse_hanime_url(url)
                video = Video.from_slug(slug, args)
                
                #special mode: add metadata and poster to already downloaded videos in batch file, without re-downloading the video. 
                if args.add_only_metadata and os.path.exists(video.output_path_filename):
                    if args.no_metadata:
                        return Exception("Error: --add-only-metadata cannot be used together with --no-metadata. Please choose one or the other.")
                    add_emmbeded_metadata(video, args)
                    if not args.no_thumbnail:
                        add_embedded_thumbnail(video, slug, args)
                    mark_as_downloaded(slug, args) #In case it was only marked as failed before
                    continue
                ################################
                if check_if_downloaded(video, slug, args):
                    continue
                if slug:
                    download(video, slug, cmd, args)
                else:
                    print(f"Invalid video URL: {url}")
                time.sleep(args.sleep_time)
    
    #--all
    elif args.all:
        # Download all videos by searching for "uncensored" and "censored" tags
        tags = args.tags #By deault ["uncensored","censored"] 

        for tag in tags:
            web_scrape_all_videos_by_search(cmd, args, tag)
    
    elif args.search:
        #Check for incompatible arguments
        search_terms =""
        if args.tag and args.brand:
            return Exception("Error: --tag and --brand cannot be used together with --search. Please choose one or the other.")
        #Determine search term
        if args.tag:
            search_terms = args.tag #OR-Search! Will search each tag separately and combine results, currently only supports searching one tag
        elif args.brand:
            search_terms = args.brand #OR-Search! Will search each brand separately and combine results, currently only supports searching one brand
        else:
            return Exception("Error: --search requires either --tag or --brand to be specified.")
        
        if len(search_terms) > 1:
            print(f"Warning: Searching for multiple terms: {search_terms}, separately. Results will be combined but duplicates may occur if videos have multiple matching tags/brands and no download archive is specified.")
        #Download
        for search_term in search_terms:
            web_scrape_all_videos_by_search(cmd, args, search_term)
    
    else:
        return Exception("No valid mode argument provided. Use --video, --all, --batch-file, --update or --search.")


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
        print(f"Starting download for: {video.title} (Slug: {slug})")
        #Download
        
        max_retries = max(1, getattr(args, 'retrys', 3))
        for video_site in sites_to_try:
            current_cmd = cmd + [video_site]
            for attempt in range(max_retries):
                try:
                    if not args.video:
                        print(f'Waiting {args.sleep_time} seconds before downloading')
                        print(f'slug {slug} from {video_site} (Attempt {attempt + 1}/{max_retries})...')
                        time.sleep(args.sleep_time) 
                    if args.verbose and getattr(args, 'verbose_ffmpeg', False):
                        print(f"Running yt-dlp command: {' '.join(current_cmd)}")

                    if args.skip_unavailable_fragments and args.verbose:
                        print(f"Skipping unavailable fragments.")
                        current_cmd = current_cmd + ["--skip-unavailable-fragments"] #"--downloader", "ffmpeg" can be used but it seem it also doesn't help with corrupted videos
                    
                    result = subprocess.run(
                        current_cmd,
                        capture_output=False,
                        text=True,
                        encoding="utf-8",
                        env=env,
                        timeout=300,
                    )

                    if result.returncode == 0:
                        success = True
                        break

                    #Sometimes yt-dlp packages misses or an error occurs, this tries to catch it and retry the download instead of failing immediately. 
                    error_output = (result.stderr or "") + "\n" + (result.stdout or "")
                    if args.verbose:
                        print(f"yt-dlp failed with return code {result.returncode}")
                        print(f"Error output: {error_output}")

                    attempt += 1
                except subprocess.TimeoutExpired:
                    if args.verbose:
                        print(f"Download timeout for {slug} on {video_site}, attempt {attempt+1}/{max_retries}")
                    continue

    if not success and not args.only_posters:
        cleanup_temp_download_files(video, args)
        if args.errors_dir:
            mark_as_failed(slug, args)
        return Exception(f"Failed to download video {slug} after trying all Sites")

    #Post-processing
    if not args.no_metadata and not args.only_posters:
        add_emmbeded_metadata(video, args)
    
    if not args.no_thumbnail and not args.only_posters:
        add_embedded_thumbnail(video, slug, args)
    
    if args.poster_download or args.only_posters:
        download_poster(video, slug, args)

    if args.working_dir:
        move_file_to_output(video, args)

    mark_as_downloaded(slug, args)
    
    return True
  
