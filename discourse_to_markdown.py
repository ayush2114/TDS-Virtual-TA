import json
import os
from tqdm import tqdm
from bs4 import BeautifulSoup
from typing import Dict
import re
from google import genai
from google.genai import types
import requests
from dotenv import load_dotenv
import mimetypes
from llms import OpenAI

openai_client = OpenAI()

def get_mime_type(url):
    mime, _ = mimetypes.guess_type(url)
    return mime or "image/jpeg"

def is_avatar_image(url: str) -> bool:
    return "user_avatar" in url or "/avatar" in url

def extract_image_urls(html: str) -> list:
    return re.findall(r'<img[^>]+src="([^"]+)"', html)

# Load environment variables from .env file
load_dotenv()
GEMENI_API_KEY = os.getenv("GEMENI_API_KEY")
client = genai.Client(api_key=GEMENI_API_KEY)

CACHE_FILE = "image_description_cache.json"
if os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, "r") as f:
        IMAGE_DESC_CACHE = json.load(f)
else:
    IMAGE_DESC_CACHE = {}

def save_image_cache():
    with open(CACHE_FILE, "w") as f:
        json.dump(IMAGE_DESC_CACHE, f, indent=2)

def get_image_description(image_url: str) -> str:
    print(f"DEBUG: Getting image description for: {image_url}")
    try:
        # Download image bytes
        # print(f"DEBUG: Downloading image from: {image_url}")
        image_bytes = requests.get(image_url, timeout=10).content
        # print(f"DEBUG: Downloaded {len(image_bytes)} bytes")

        mime_type = get_mime_type(image_url)
        # print(f"DEBUG: Detected mime type: {mime_type}")
        image = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)

        # Ask Gemini for a description
        # print(f"DEBUG: Requesting description from Gemini...")
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=["Briefly describe this image", image],
        )
        
        description = response.text.strip()
        # print(f"DEBUG: Received description: {description}")
        return description
    except Exception as e:
        print(f"DEBUG: Error getting image description: {str(e)}")
        return f"Error getting image description: {str(e)}"

def clean_html(text):
    return BeautifulSoup(text, "html.parser").get_text().strip()

BASE_URL =  "https://discourse.onlinedegree.iitm.ac.in"
def thread_to_markdown(topic: Dict, posts_data: Dict) -> str:
    title = topic.get("topic_title", "No Title")
    url = topic.get("url", "")
    if not url.startswith("http"):
        url = BASE_URL + url
    posts = posts_data["post_stream"]["posts"]

    md = f"## [{title}]({url})\n\n"
    md += f"**Source URL:** {url}\n"
    md += "---\n\n"

    for i, post in enumerate(posts, start=1):
        name = post.get("name", "Unknown User")
        post_url = post.get("post_url", "")
        if not post_url.startswith("http"):
            post_url = BASE_URL + post_url
        raw_html = post.get("cooked", "")
        post_content = clean_html(raw_html)
        md += f"### {'🟩' if i == 1 else '🟦'} Post #{i} by {name}\n"
    
        md += f"> {post_content}\n\n"
        md += f"**Post URL:** {post_url}\n\n"
        
        if i in [1, 2]:
            image_urls = extract_image_urls(raw_html)
            
            for img_url in image_urls:
                if re.search(r'_\d{1,3}x\d{1,3}\.png$', img_url):
                    continue
                if is_avatar_image(img_url):
                    continue
                if "europe1.discourse-cdn.com" not in img_url:
                    continue
                if img_url in IMAGE_DESC_CACHE:
                    print(f"DEBUG: Using cached description for {img_url}")
                    img_desc = IMAGE_DESC_CACHE[img_url]
                else:
                    img_desc = get_image_description(img_url)
                    IMAGE_DESC_CACHE[img_url] = img_desc
                    save_image_cache()
                    print(f"DEBUG: Getting image description for: {img_url}")
                md += f"**Description of the image attached:** {img_desc}\n"
            md += "---\n\n"

    return md


if __name__ == "__main__":
    output_dir = "discourse_md"
    os.makedirs(output_dir, exist_ok=True)
    posts_dir = "discourse_json"

    with open("discourse_posts.json", "r", encoding="utf-8") as f:
        topics = json.load(f)

    for topic in tqdm(topics, desc="Processing topics"):
        topic_id = topic["topic_id"]
        posts_file = os.path.join(posts_dir, f"topic_{topic_id}.json")
        output_file = os.path.join(output_dir, f"{topic_id}.md")

        if os.path.exists(output_file):
            continue

        if not os.path.exists(posts_file):
            print(f"DEBUG: File {posts_file} does not exist, skipping...")
            continue

        try:
            with open(posts_file, "r", encoding="utf-8") as pf:
                posts_data = json.load(pf)

            md_content = thread_to_markdown(topic, posts_data)

            with open(output_file, "w", encoding="utf-8") as outf:
                outf.write(md_content)

        except Exception as e:
            print(f"❌ Error processing topic {topic_id}: {e}")   