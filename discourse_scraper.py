"""
Simple Discourse forum scraper that downloads topics and posts as JSON files.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import requests


# Configuration - Change these values as needed
BASE_URL = "https://discourse.onlinedegree.iitm.ac.in/"
CATEGORY_SLUG = "courses/tds-kb"
CATEGORY_ID = 34
START_DATE = "2025-01-01"
END_DATE = "2025-04-15"
OUTPUT_DIR = "discourse_json"

# Your browser cookies (required for private forums)
COOKIES = """_ga=GA1.1.947601252.1728015122; _fbp=fb.2.1728015124125.76237322913001334; _gcl_au=1.1.1370871129.1744388159; _ga_5HTJMW67XK=GS2.1.s1749089869$o13$g0$t1749089881$j48$l0$h0; _ga_08NPRH5L4M=GS2.1.s1750156913$o328$g0$t1750158260$j60$l0$h0; _t=lSsZbjTEaA97e7TyL4Xsye8Yl8jwvHB7koQ5yn1M9N%2BnMbJvwfbnmoV5lnm1h0NtnEti3UdYceVGqFvtWJoaEGACojCH25xwtb0u8n3%2BAZ8%2BVCogPUK88fxs8Pa5jbRJUusQkua7qkkXD2RFBn709fyTUgavJYBIfhNYfnnZOqTisWd5hbjYJa1VMRVlON0OxdO7MNw17vg6W%2FZ%2B4Ch%2F5eKMRiCh4eLQlWRL4ZPhQM071syRn0d986krZ1kkoNw%2BaJC2zMHddw40JY6hSC6TFGCjR9ccuV57vC6yrW73Ie1HEd0LLAP9QerujuVYV2H9--%2FzaSvcF5e%2FrC3I5E--aMJpFVKaVlDNvS5sjGMl8w%3D%3D; _forum_session=YQ1r0Wtal3bbmbWlRLWpRCljb9RH6NY%2BLvRGA7byAd9Imv4HLjzKwnVLqTAMs1UhyIEPkYO6CdpjKuDA%2Bi%2BmN4SijTTyVefqhX2dYWnjawZhSvmUjOMtZAQbJnHs0aAHuaSmTzkCqOSUTeNYeCcPhdjpjpnKL84kx0%2FzeWtldZc%2FJYHO6kQhHWn52s2AS3xTmDx%2F2sdz0zTbrN4LFKBBFkn17W4pimijNbMEgweWeLMNdk74t4IWaKNIorprWchr9SVRFtcKR1nLz7Cs5kosUf1f65IPLQ%3D%3D--XacPBRhrG2tFhdIz--a12Pz9OalXRL43Ke5asQag%3D%3D"""


class DiscourseScraper:
    """Downloads forum topics and saves them as JSON files."""
    
    def __init__(self):
        """Set up the scraper."""
        # Parse cookies from the string above
        self.cookies = self._parse_cookies(COOKIES)
        
        # Create output folder
        Path(OUTPUT_DIR).mkdir(exist_ok=True)
        
        # Keep track of what we've downloaded
        self.downloaded_count = 0
        self.failed_topics = []
    
    def _parse_cookies(self, cookie_string: str) -> Dict[str, str]:
        """Turn cookie string into a dictionary for requests."""
        cookies = {}
        if not cookie_string.strip():
            print("Warning: No cookies provided - may fail for private forums")
            return cookies
        
        for part in cookie_string.strip().split(";"):
            if "=" in part:
                key, value = part.strip().split("=", 1)
                cookies[key] = value
        
        return cookies
    
    def _make_request(self, url: str, params: Dict = None) -> Optional[Dict]:
        """Make a request to the forum API and return JSON data."""
        try:
            response = requests.get(url, cookies=self.cookies, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Request failed for {url}: {e}")
            return None
    
    def _is_topic_in_date_range(self, topic: Dict) -> bool:
        """Check if topic was created within our date range."""
        created_at = topic.get("created_at")
        if not created_at:
            return False
        
        try:
            # Parse the date
            topic_date = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            
            # Parse our start/end dates
            start_date = datetime.fromisoformat(START_DATE + "T00:00:00+00:00")
            end_date = datetime.fromisoformat(END_DATE + "T23:59:59+00:00")
            
            return start_date <= topic_date <= end_date
        except ValueError:
            print(f"Couldn't parse date for topic {topic.get('id')}: {created_at}")
            return False
    
    def get_topic_ids(self) -> List[int]:
        """Find all topic IDs in our category and date range."""
        print(f"Looking for topics from {START_DATE} to {END_DATE}...")
        
        topic_ids = []
        page = 0
        pages_without_new_topics = 0
        
        while True:
            print(f"Checking page {page}...")
            
            # Get this page of topics
            url = f"{BASE_URL}c/{CATEGORY_SLUG}/{CATEGORY_ID}.json"
            data = self._make_request(url, {"page": page})
            
            if not data:
                print(f"Failed to get page {page}")
                break
            
            topics_on_page = data.get("topic_list", {}).get("topics", [])
            
            if not topics_on_page:
                print("No more topics found")
                break
            
            # Count topics before we add new ones
            old_count = len(topic_ids)
            
            # Check each topic's date
            for topic in topics_on_page:
                if self._is_topic_in_date_range(topic):
                    topic_ids.append(topic["id"])
            
            # Remove duplicates
            topic_ids = list(set(topic_ids))
            new_count = len(topic_ids)
            
            # If we didn't find any new topics, increment counter
            if new_count == old_count:
                pages_without_new_topics += 1
                print(f"No new topics on this page ({pages_without_new_topics} pages without new topics)")
            else:
                pages_without_new_topics = 0
                print(f"Found {new_count - old_count} new topics (total: {new_count})")
            
            # Stop if we've seen too many pages without new topics
            if pages_without_new_topics >= 5:
                print("Haven't found new topics in a while - stopping")
                break
            
            # Check if there are more pages
            if not data.get("topic_list", {}).get("more_topics_url"):
                print("Reached last page")
                break
            
            page += 1
        
        print(f"Found {len(topic_ids)} topics total")
        return topic_ids
    
    def get_all_posts_for_topic(self, topic_id: int) -> Optional[Dict]:
        """Download a complete topic with all its posts."""
        print(f"Downloading topic {topic_id}...")
        
        # Get basic topic info
        url = f"{BASE_URL}t/{topic_id}.json"
        topic_data = self._make_request(url)
        
        if not topic_data:
            return None
        
        # Check if we need to get more posts
        post_stream = topic_data.get("post_stream", {})
        all_post_ids = post_stream.get("stream", [])
        loaded_posts = post_stream.get("posts", [])
        loaded_post_ids = {post["id"] for post in loaded_posts}
        
        # Find missing posts
        missing_post_ids = [pid for pid in all_post_ids if pid not in loaded_post_ids]
        
        if missing_post_ids:
            print(f"  Need to get {len(missing_post_ids)} more posts...")
            
            # Get missing posts in batches of 50
            batch_size = 50
            additional_posts = []
            
            for i in range(0, len(missing_post_ids), batch_size):
                batch = missing_post_ids[i:i + batch_size]
                print(f"  Getting posts {batch[0]} to {batch[-1]}...")
                
                # Build the request
                post_url = f"{BASE_URL}t/{topic_id}/posts.json"
                params = [("post_ids[]", pid) for pid in batch]
                
                batch_data = self._make_request(post_url, dict(params))
                
                if batch_data:
                    # Handle different response formats
                    if isinstance(batch_data, list):
                        additional_posts.extend(batch_data)
                    elif "posts" in batch_data:
                        additional_posts.extend(batch_data["posts"])
                    elif "post_stream" in batch_data and "posts" in batch_data["post_stream"]:
                        additional_posts.extend(batch_data["post_stream"]["posts"])
            
            # Add the new posts to our topic data
            if additional_posts:
                print(f"  Got {len(additional_posts)} additional posts")
                
                # Combine all posts
                all_posts = {post["id"]: post for post in loaded_posts}
                for post in additional_posts:
                    all_posts[post["id"]] = post
                
                # Put posts in the right order
                ordered_posts = []
                for post_id in all_post_ids:
                    if post_id in all_posts:
                        ordered_posts.append(all_posts[post_id])
                
                topic_data["post_stream"]["posts"] = ordered_posts
        
        print(f"  Topic has {len(topic_data['post_stream']['posts'])} posts total")
        return topic_data
    
    def save_topic(self, topic_id: int, topic_data: Dict) -> bool:
        """Save topic data to a JSON file."""
        filename = f"topic_{topic_id}.json"
        filepath = Path(OUTPUT_DIR) / filename
        
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(topic_data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Failed to save topic {topic_id}: {e}")
            return False
    
    def run(self):
        """Download all topics in the date range."""
        print("Starting Discourse scraper...")
        print(f"Forum: {BASE_URL}")
        print(f"Category: {CATEGORY_SLUG} (ID: {CATEGORY_ID})")
        print(f"Date range: {START_DATE} to {END_DATE}")
        print(f"Output folder: {OUTPUT_DIR}")
        print()
        
        # Step 1: Find all topic IDs
        topic_ids = self.get_topic_ids()
        
        if not topic_ids:
            print("No topics found!")
            return
        
        print(f"\nStarting download of {len(topic_ids)} topics...\n")
        
        # Step 2: Download each topic
        for i, topic_id in enumerate(topic_ids, 1):
            print(f"[{i}/{len(topic_ids)}] Topic {topic_id}")
            
            # Get the complete topic data
            topic_data = self.get_all_posts_for_topic(topic_id)
            
            if topic_data and self.save_topic(topic_id, topic_data):
                self.downloaded_count += 1
                print(f"  ✓ Saved successfully")
            else:
                self.failed_topics.append(topic_id)
                print(f"  ✗ Failed")
            
            print()
        
        # Step 3: Show summary
        print("=" * 50)
        print("DOWNLOAD SUMMARY")
        print("=" * 50)
        print(f"Topics found: {len(topic_ids)}")
        print(f"Successfully downloaded: {self.downloaded_count}")
        print(f"Failed: {len(self.failed_topics)}")
        
        if self.failed_topics:
            print(f"Failed topic IDs: {self.failed_topics}")
        
        print(f"Files saved to: {Path(OUTPUT_DIR).absolute()}")
        print("Done!")


def main():
    """Run the scraper."""
    scraper = DiscourseScraper()
    scraper.run()


if __name__ == "__main__":
    main()
