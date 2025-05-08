import os
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from selenium import webdriver
from selenium.webdriver.common.by import By
from slugify import slugify

# List of NCI Support Hub categories to scrape
urls_to_scrape = [
    'https://ncisupporthub.ncirl.ie/hc/en-ie/categories/4403640877842-Exams',
    'https://ncisupporthub.ncirl.ie/hc/en-ie/categories/360002531399-IT',
    'https://ncisupporthub.ncirl.ie/hc/en-ie/categories/6261334725276-Getting-Started',
    'https://ncisupporthub.ncirl.ie/hc/en-ie/categories/4403839059090-Student-Services',
    'https://ncisupporthub.ncirl.ie/hc/en-ie/categories/5100315593884-International',
    'https://ncisupporthub.ncirl.ie/hc/en-ie/categories/4416152689810-Policies-Procedures',
    'https://ncisupporthub.ncirl.ie/hc/en-ie/categories/6566916013724-Library',
    'https://ncisupporthub.ncirl.ie/hc/en-ie/categories/4619661151004-Central-Timetable-Office',
    'https://ncisupporthub.ncirl.ie/hc/en-ie/categories/6648647876380-Quality-and-Institutional-Effectiveness',
    'https://ncisupporthub.ncirl.ie/hc/en-ie/categories/4403640947218-Student-Experience-Sport'
]

BASE_DOMAIN = "https://ncisupporthub.ncirl.ie"
STATIC_DIR = "static"
TEMPLATE_DIR = "templates"

# Create folders
os.makedirs(f"{STATIC_DIR}/css", exist_ok=True)
os.makedirs(f"{STATIC_DIR}/js", exist_ok=True)
os.makedirs(f"{STATIC_DIR}/img", exist_ok=True)
os.makedirs(TEMPLATE_DIR, exist_ok=True)

# Start headless browser
options = webdriver.ChromeOptions()
options.add_argument("headless=new")
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
driver = webdriver.Chrome(options=options)

def download_asset(url, folder):
    try:
        if not url or "<%" in url:
            raise ValueError("Skipping template or empty URL")

        if url.startswith("//"):
            url = "https:" + url
        elif url.startswith("/"):
            url = BASE_DOMAIN + url

        filename = os.path.basename(urlparse(url).path)
        if not filename:
            raise ValueError("Invalid filename")

        local_path = f"{STATIC_DIR}/{folder}/{filename}"
        flask_path = f"/static/{folder}/{filename}"

        if os.path.exists(local_path):
            return flask_path

        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers)

        if r.status_code == 403:
            print(f"[SKIPPED] 403 Forbidden: {url}")
            return url  # keep original URL in HTML

        r.raise_for_status()
        with open(local_path, "wb") as f:
            f.write(r.content)

        return flask_path
    except Exception as e:
        print(f"[ERROR] Could not download {url}: {e}")
        return url

def save_full_page(driver, title):
    soup = BeautifulSoup(driver.page_source, "html.parser")

    for tag in soup.find_all("link", href=True):
        if "stylesheet" in tag.get("rel", []):
            tag["href"] = download_asset(tag["href"], "css")

    for tag in soup.find_all("script", src=True):
        tag["src"] = download_asset(tag["src"], "js")

    for tag in soup.find_all("img", src=True):
        tag["src"] = download_asset(tag["src"], "img")

    filename = slugify(title) + ".html"
    filepath = os.path.join(TEMPLATE_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(soup.prettify())

    print(f"Saved: templates/{filename}")

def scrape_category(category_url):
    print(f"Scraping category: {category_url}")
    driver.get(category_url)
    time.sleep(3)

    # Collect top-level articles
    h2_links = driver.find_elements(By.CSS_SELECTOR, 'h2.h3 a')
    article_links = [link.get_attribute("href") for link in h2_links if link.get_attribute("href")]

    # Collect any /sections/... links
    section_links = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/hc/en-ie/sections/"]')
    section_urls = list(set(link.get_attribute("href") for link in section_links if link.get_attribute("href")))

    # From each section, collect additional articles
    for section_url in section_urls:
        print(f"Scanning section: {section_url}")
        driver.get(section_url)
        time.sleep(2)

        nested_links = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/hc/en-ie/articles/"]')
        nested_articles = [link.get_attribute("href") for link in nested_links if link.get_attribute("href")]
        article_links.extend(nested_articles)

    # Deduplicate all article links
    article_links = list(set(article_links))

    # Only save new articles
    for article_url in article_links:
        title_slug = slugify(article_url.split("/")[-1])
        filepath = os.path.join(TEMPLATE_DIR, title_slug + ".html")
        if os.path.exists(filepath):
            print(f"[SKIPPED] Already saved: {title_slug}")
            continue

        print(f"Scraping article: {article_url}")
        driver.get(article_url)
        time.sleep(3)
        title = driver.title
        save_full_page(driver, title)

# Start scraping all categories
for url in urls_to_scrape:
    scrape_category(url)

driver.quit()
print("Done. All articles and assets saved.")
