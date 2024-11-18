from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium import webdriver
import csv
import feedparser
import datetime
import datetime
from dateutil import parser

import re
from bs4 import BeautifulSoup
from dateutil.tz import tzlocal
import os

from selenium_stealth import stealth

keywords = ["wild", "zero day", "0 day", "zero-day", "under active attack"]


def fetch_html(url):
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    stealth(driver,
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
            )
    try:
        driver.get(url)
        html = driver.page_source
    finally:
        driver.quit()
    return html


def find_cves(html):
    # Regex pattern to find CVE IDs
    cve_pattern = r'CVE-\d{4}-\d{4,7}'
    return re.findall(cve_pattern, html)


def scrape_cves(posts):
    results = []
    for post in posts:
        html = fetch_html(post["link"])
        if html:
            soup = BeautifulSoup(html, 'html.parser')
            text = soup.get_text()
            cves = find_cves(text)
            if len(cves) > 0:
                results.append(
                    {"cveID": cves, "vulnerabilityName": post["title"], "shortDescription": post["summary"], "url": post["link"]})

    return results


def read_feed(link, last_days):
    feed = feedparser.parse(link)
    events = set()

    # Get the current time in local timezone
    now = datetime.datetime.now(tzlocal())

    # Calculate the from_time based on last_days
    from_time = now - datetime.timedelta(days=last_days)

    for event in feed.entries:
        event_time = parser.parse(event["published"])

        # Compare times and check for keywords
        if from_time < event_time < now and any(keyword in event["title"].lower() for keyword in keywords):
            events.add(event)

    return events if events else None


def fetch_feed_metadata(filename):
    with open(filename, 'r') as f:
        feeds_in_dict = [line for line in csv.DictReader(f)]
    return feeds_in_dict


def fetch_from_feeds(feeds_dict, last_days):
    post_data = list()
    for feed in feeds_dict:
        if feed["source"].startswith("#"):
            continue
        else:
            events = read_feed(feed["source"], last_days)
            if events is not None:
                for event in events:
                    event["org"] = feed["title"]
                    post_data.append(event)
    return post_data


def workflow(last_days=1):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, 'feeds.csv')
    feeds = fetch_feed_metadata(file_path)
    posts = fetch_from_feeds(feeds, last_days)
    posts = scrape_cves(posts)
    return posts


if __name__ == '__main__':
    print(workflow())
