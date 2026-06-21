import asyncio
import re
import sys
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import httpx

# Add workspace path to sys.path
sys.path.append("/workspace")
from app.config_rss import BASE_RSS_INDEXES

def clean_name(name, site):
    name = re.sub(r'\s+', ' ', name).strip()
    name = name.replace("RSS", "").replace("rss", "")
    name = name.replace(site, "").strip("- ").strip()
    # Strip any embedded URL (e.g. - https://baoxaydung.vn/...)
    name = re.sub(r'\s*-\s*https?://\S+', '', name)
    name = re.sub(r'\s*https?://\S+', '', name)
    name = name.strip("- .")
    return name

async def get_feeds(site, url, client: httpx.AsyncClient):
    feeds = []
    
    # Early return for simple RSS feeds, except baoxaydung.vn/index.rss which is actually an HTML page listing feeds!
    if (url.endswith('.rss') or url.endswith('.xml')) and not 'RssPage' in url and not 'index.rss' in url:
        feeds.append({
            "name": f"{site} - Trang chủ",
            "url": url,
            "source_type": "RSS"
        })
        return feeds
        
    try:
        res = await client.get(url, timeout=15.0)
        
        # Lao Dong JS cookie challenge bypass
        if 'document.cookie="D1N=' in res.text:
            match = re.search(r'document\.cookie="D1N=([^"]+)"', res.text)
            if match:
                cookie_val = match.group(1)
                client.cookies.set("D1N", cookie_val)
                res = await client.get(url, timeout=15.0)
                
        html = res.text
        soup = BeautifulSoup(html, 'html.parser')
        seen_urls = set()
        
        for a in soup.find_all('a', href=True):
            href = a['href'].strip()
            is_rss = False
            if href.endswith('.rss') or '/rss/' in href or 'rss' in href.lower():
                is_rss = True
            elif site == "Báo Quân đội Nhân dân" and '/tin-tuc/' in href:
                is_rss = True
                
            if is_rss:
                absolute_url = urljoin(url, href)
                if absolute_url in seen_urls:
                    continue
                seen_urls.add(absolute_url)
                
                name = a.text.strip()
                if not name and a.parent:
                    name = a.parent.text.strip()
                
                name = clean_name(name, site)
                if not name:
                    name = absolute_url.split('/')[-1].replace('.rss', '').replace('-', ' ').title()
                
                feeds.append({
                    "name": f"{site} - {name}",
                    "url": absolute_url,
                    "source_type": "RSS"
                })
        print(f"Scraped {len(feeds)} feeds from {site}")
    except Exception as e:
        print(f"Error scraping {site} from {url}: {e}")
        
    return feeds

async def main():
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=30.0) as client:
        tasks = [get_feeds(site, url, client) for site, url in BASE_RSS_INDEXES.items()]
        results = await asyncio.gather(*tasks)
        
    all_feeds = []
    for r in results:
        all_feeds.extend(r)
        
    # Remove duplicates and format them
    seen = set()
    unique_sources = []
    
    # Add default WEB/special search sources
    unique_sources.append({"name": "VnExpress Tag - Sân bay Long Thành", "url": "https://vnexpress.net/tag/san-bay-long-thanh-216912", "source_type": "WEB"})
    unique_sources.append({"name": "Tuổi Trẻ Chủ đề - Sân bay Long Thành", "url": "https://tuoitre.vn/chu-de/san-bay-long-thanh.html", "source_type": "WEB"})
    unique_sources.append({"name": "Báo Giao thông - Tìm kiếm Long Thành", "url": "https://www.baogiaothong.vn/tim-kiem.html?q=s%C3%A2n+bay+Long+Th%C3%A0nh", "source_type": "WEB"})
    unique_sources.append({"name": "VietnamNet Tag - Sân bay Long Thành", "url": "https://vietnamnet.vn/san-bay-long-thanh-tag8279442006764491745.html", "source_type": "WEB"})
    
    # Add scraped RSS sources
    for s in unique_sources:
        seen.add(s["url"])
        
    for feed in all_feeds:
        u = feed["url"].replace('\n', '').replace(' ', '')
        if u in seen:
            continue
        seen.add(u)
        unique_sources.append({
            "name": feed["name"],
            "url": u,
            "source_type": "RSS"
        })
        
    print(f"Total unique sources to seed: {len(unique_sources)}")
    
    # Read seed.py
    seed_path = "/workspace/seed.py"
    with open(seed_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    # Find start and end of DEFAULT_SOURCES
    start_match = re.search(r'DEFAULT_SOURCES\s*=\s*\[', content)
    if not start_match:
        print("Could not find DEFAULT_SOURCES = [ in seed.py")
        sys.exit(1)
        
    start_idx = start_match.start()
    
    # Find end of DEFAULT_SOURCES by searching for DEFAULT_ALERT_RULES = [
    end_match = re.search(r'DEFAULT_ALERT_RULES\s*=\s*\[', content)
    if not end_match:
        print("Could not find DEFAULT_ALERT_RULES = [ in seed.py")
        sys.exit(1)
        
    end_idx = end_match.start()
    
    # We find the closing bracket before DEFAULT_ALERT_RULES
    subcontent = content[start_idx:end_idx]
    # Find the last closing bracket in subcontent
    last_bracket = subcontent.rfind(']')
    if last_bracket == -1:
        print("Could not find closing bracket for DEFAULT_SOURCES")
        sys.exit(1)
        
    bracket_global_idx = start_idx + last_bracket
    
    # Format the new list of sources
    formatted_sources = "DEFAULT_SOURCES = [\n"
    for src in unique_sources:
        formatted_sources += f'    {{"name": "{src["name"]}", "url": "{src["url"]}", "source_type": "{src["source_type"]}"}},\n'
    formatted_sources += "]\n"
    
    # Replace in content
    new_content = content[:start_idx] + formatted_sources + content[bracket_global_idx + 1:]
    
    with open(seed_path, "w", encoding="utf-8") as f:
        f.write(new_content)
        
    print("Successfully updated seed.py with new scraped sources list!")

if __name__ == "__main__":
    asyncio.run(main())
