import json
import re
from datetime import datetime, timezone
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://esei.uvigo.es"
TEACHERS_LIST_URL = f"{BASE_URL}/docencia/profesorado/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def clean_text(text):
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def extract_field_by_label(soup, label_pattern):
    """
    Finds text following a label in tables, definition lists, or paragraph rows.
    Example: searches for 'Despacho:' or 'Teléfono:' and returns the adjacent text.
    """
    element = soup.find(
        lambda tag: tag.name in ["td", "th", "strong", "span", "div", "p"]
        and re.search(label_pattern, tag.text, re.IGNORECASE)
    )
    if not element:
        return ""

    # Check next sibling element (common in tables or flex containers)
    next_el = element.find_next_sibling()
    if next_el and next_el.text.strip():
        return clean_text(next_el.text)

    # Check parent container text with label removed
    parent = element.parent
    if parent:
        text = parent.text.replace(element.text, "")
        return clean_text(text)

    return ""


def extract_teacher_info(profile_url):
    info = {
        "office": "No especificado",
        "phone": "",
        "email": "",
        "virtual_office": "",
        "uvigo_url": "",
        "subjects": []
    }

    try:
        res = requests.get(profile_url, headers=HEADERS, timeout=10)
        if res.status_code != 200:
            return info

        soup = BeautifulSoup(res.content, "html.parser")

        # 1. Isolate the main profile content wrapper
        content = soup.select_one(".entry-content, .pf-profile, article, .post-inner")
        if not content:
            content = soup # fallback if structure varies slightly

        # 2. Extract Email (mailto link)
        email_link = content.select_one("a[href^='mailto:']")
        if email_link:
            info["email"] = email_link["href"].replace("mailto:", "").strip()

        # 3. Extract Virtual Office (campusremotouvigo)
        virtual_link = content.select_one("a[href*='campusremotouvigo']")
        if virtual_link:
            info["virtual_office"] = virtual_link["href"].strip()

        # 4. Extract UVigo PDI / Profile Link
        uvigo_link = content.select_one("a[href*='uvigo.gal'][href*='/pdi/'], a[href*='uvigo.es'][href*='/pdi/']")
        if uvigo_link:
            info["uvigo_url"] = uvigo_link["href"].strip()

        # 5. Extract Despacho (Office) & Teléfono (Phone) directly from text rows/cells
        # Look specifically for labels followed by text
        text_nodes = content.find_all(["p", "td", "li", "div", "span"])
        for node in text_nodes:
            text = clean_text(node.text)

            # Look for "Despacho:" or "Oficina:"
            if info["office"] == "No especificado" and re.search(r"despacho", text, re.IGNORECASE):
                # Grab just the number/code right after "Despacho"
                match = re.search(r"despacho[:\s]+([A-Za-z0-9\.\-]+)", text, re.IGNORECASE)
                if match:
                    info["office"] = match.group(1).strip()

            # Look for "Teléfono:" or "Telefono:"
            if not info["phone"] and re.search(r"teléfono|telefono", text, re.IGNORECASE):
                match = re.search(r"(?:teléfono|telefono)[:\s]+(\+?\d[\d\s]{7,})", text, re.IGNORECASE)
                if match:
                    info["phone"] = clean_text(match.group(1))

        # 6. Extract Subjects (Docencia) from the site's native .field structure
        fields = content.select(".field")
        for field in fields:
            label_el = field.select_one(".field_label")
            item_el = field.select_one(".field_item")
            if label_el and item_el and re.search(r"asignaturas|docencia", label_el.text, re.IGNORECASE):
                # Try finding links first
                links = item_el.find_all("a", href=True)
                if links:
                    for a in links:
                        subj_name = clean_text(a.text)
                        if subj_name and len(subj_name) > 2 and subj_name not in info["subjects"]:
                            info["subjects"].append(subj_name)
                else:
                    # Fallback to reading text blocks/lines inside the field item
                    for line in item_el.stripped_strings:
                        if line and len(line) > 2 and line not in info["subjects"]:
                            info["subjects"].append(line)

        # Fallback to old heading method if nothing found via .field
        if not info["subjects"]:
            docencia_heading = content.find(
                lambda tag: tag.name in ["h2", "h3", "h4", "h5", "strong"] 
                and ("docencia" in tag.text.lower() or "asignaturas" in tag.text.lower())
            )
            if docencia_heading:
                parent_container = docencia_heading.find_parent(["div", "section"]) or docencia_heading.parent
                if parent_container:
                    for a in parent_container.find_all("a", href=True):
                        subj_name = clean_text(a.text)
                        href = a["href"]
                        if (
                            subj_name
                            and len(subj_name) > 3
                            and not href.startswith("mailto:")
                            and "uvigo.gal" not in href
                            and "campusremotouvigo" not in href
                            and "/profesorado/" not in href
                            and subj_name not in info["subjects"]
                        ):
                            info["subjects"].append(subj_name)

    except Exception as e:
        print(f"Error parsing {profile_url}: {e}")

    return info

def scrape_all_teachers():
    print(f"Connecting to {TEACHERS_LIST_URL}...")
    res = requests.get(TEACHERS_LIST_URL, headers=HEADERS, timeout=15)

    if res.status_code != 200:
        print(f"Error HTTP {res.status_code}")
        return

    soup = BeautifulSoup(res.content, "html.parser")
    teachers_data = []

    links = soup.select("a[href*='/docencia/profesorado/profesor/']")
    visited_urls = set()

    for idx, link in enumerate(links, start=1):
        name = clean_text(link.text)
        esei_url = link.get("href")

        if not esei_url or esei_url in visited_urls:
            continue

        if not esei_url.startswith("http"):
            esei_url = BASE_URL + esei_url

        visited_urls.add(esei_url)
        print(f"[{len(visited_urls)}] Fetching: {name}")

        extra_info = extract_teacher_info(esei_url)

        teachers_data.append({
            "id": f"p-{idx}",
            "name": name,
            "office": extra_info["office"],
            "phone": extra_info["phone"],
            "email": extra_info["email"],
            "virtual_office": extra_info["virtual_office"],
            "esei_url": esei_url,
            "uvigo_url": extra_info["uvigo_url"],
            "subjects": extra_info["subjects"]
        })

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(teachers_data),
        "teachers": teachers_data
    }

    with open("teachers.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nSaved {len(teachers_data)} teachers to 'teachers.json'")


if __name__ == "__main__":
    scrape_all_teachers()