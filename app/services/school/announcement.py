import time
import requests
from bs4 import BeautifulSoup

from app.services.school.constants import BASE_URL, ANNOUNCEMENT_URL


def get_latest_announcement_node_id():
    """Lấy node_id thông báo mới nhất từ MongoDB.

    Returns:
        node_id của thông báo được lưu gần đây nhất,
        hoặc None nếu DB trống.
    """
    try:
        from app.core.db import announcement_collection
        doc = announcement_collection.find_one(
            {}, {"node_id": 1}, sort=[("date", -1)]
        )
        return doc["node_id"] if doc else None
    except Exception as e:
        print(f"Error getting latest node_id: {e}")
        return None


def get_all_announcements(max_pages=10):
    results = []
    # Lấy node_id mới nhất từ DB để dừng sớm
    latest_node_id = get_latest_announcement_node_id()
    if latest_node_id:
        print(f"Latest known announcement node_id: {latest_node_id} — will stop when encountered")

    for page in range(max_pages):
        url = ANNOUNCEMENT_URL + str(page)

        try:
            res = requests.get(url, timeout=10)
            if res.status_code != 200:
                break

            soup = BeautifulSoup(res.text, "html.parser")
            articles = soup.find_all("article")

            if not articles:
                break

            for article in articles:
                data = parse_article(article)
                if data:
                    results.append(data)
                    # Dừng sớm: nếu thông báo này đã có trong DB,
                    # mọi thông báo sau nó trên trang này và các trang sau đều cũ
                    if latest_node_id and data["node_id"] == latest_node_id:
                        print(f"Reached known announcement {data['node_id']} — stopping early")
                        return results

            # tam dung tranh block
            time.sleep(0.5)

        except Exception as e:
            print(f"Error page {page}: {e}")
            continue

    return results


def parse_article(article):
    try:
        node_id = article.get("id", "").replace("node-", "")

        header = article.find("h2")
        if not header:
            return None

        a_tag = header.find("a")
        title = header.get_text(strip=True)

        link = ""
        if a_tag and a_tag.get("href"):
            link = BASE_URL + a_tag["href"]

        date_val = ""
        submitted_span = article.select_one(".submitted span")
        if submitted_span and submitted_span.has_attr("content"):
            date_val = submitted_span["content"]

        content_text = ""
        content_div = article.find(class_="content")
        if content_div:
            content_text = content_div.get_text(separator="\n", strip=True)

        return {
            "node_id": node_id,
            "title": title,
            "preview": content_text,
            "date": date_val,
            "link": link
        }

    except Exception as e:
        print("Parse error:", e)
        return None


def parse_content_element(element) -> str:
    result = []

    for child in element.children:
        if isinstance(child, str):
            text = child.strip()
            if text:
                result.append(text)
            continue

        tag = child.name

        if tag == "table":
            result.append(parse_table(child))

        elif tag in ("p", "div", "h1", "h2", "h3", "h4", "li"):
            inner = child.get_text(separator=" ", strip=True)
            if inner:
                result.append(inner)

        elif tag in ("ul", "ol"):
            for li in child.find_all("li", recursive=False):
                result.append("- " + li.get_text(separator=" ", strip=True))

        elif tag == "br":
            result.append("")

        else:
            # du phong lay text
            inner = child.get_text(separator=" ", strip=True)
            if inner:
                result.append(inner)

    return "\n".join(result)


def parse_table(table) -> str:
    rows = table.find_all("tr")
    if not rows:
        return ""

    table_data = []
    for row in rows:
        cells = row.find_all(["td", "th"])
        table_data.append([cell.get_text(separator=" ", strip=True) for cell in cells])

    if not table_data:
        return ""

    # chuan hoa so cot
    col_count = max(len(row) for row in table_data)
    for row in table_data:
        while len(row) < col_count:
            row.append("")

    # tinh chieu rong cot
    col_widths = [
        max(len(row[i]) for row in table_data)
        for i in range(col_count)
    ]

    lines = []
    for i, row in enumerate(table_data):
        padded = [row[j].ljust(col_widths[j]) for j in range(col_count)]
        lines.append("| " + " | ".join(padded) + " |")
        if i == 0:  # dòng phân cách header
            lines.append("| " + " | ".join("-" * col_widths[j] for j in range(col_count)) + " |")

    return "\n".join(lines)


def fetch_article_content(article_summary: dict) -> dict:
    try:
        res = requests.get(article_summary["link"], timeout=10)
        if res.status_code != 200:
            return None

        soup = BeautifulSoup(res.text, "html.parser")
        article = soup.find("article")
        if not article:
            return None

        content_div = article.select_one(".field-name-body .field-item")
        full_content = parse_content_element(content_div) if content_div else ""

        related = []
        for a in soup.select("#block-views-contents-block-1 .view-content a"):
            href = a.get("href", "")
            related.append({
                "title": a.get_text(strip=True),
                "link": BASE_URL + href if href.startswith("/") else href
            })

        return {
            "node_id": article_summary["node_id"],
            "title": article_summary["title"],
            "date": article_summary["date"],
            "link": article_summary["link"],
            "details": {
                "content": full_content,
                "related": related
            }
        }

    except Exception as e:
        print(f"Error fetching {article_summary.get('link')}: {e}")
        return None


def get_all_announcements_full(max_pages=10) -> list:
    summaries = get_all_announcements(max_pages)
    if not summaries:
        print("No summaries fetched — scraping failed or site blocked.")
        return []

    results = []
    for i, summary in enumerate(summaries):
        print(f"Fetching [{i+1}/{len(summaries)}]: {summary['title'][:60]}...")
        try:
            full = fetch_article_content(summary)
            if full:
                full["preview"] = summary.get("preview", "")
                results.append(full)
            else:
                print(f"  ⚠ fetch_article_content returned None for: {summary['link']}")
        except Exception as e:
            print(f"  ✗ Exception on {summary['link']}: {e}")
        time.sleep(0.5)

    print(f"Successfully fetched: {len(results)}/{len(summaries)}")
    return results