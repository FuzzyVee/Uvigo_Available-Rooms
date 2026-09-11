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
        "tutoring_url": "",
        "subjects": []
    }

    try:
        res = requests.get(profile_url, headers=HEADERS, timeout=10)
        if res.status_code != 200:
            return info

        soup = BeautifulSoup(res.content, "html.parser")
        page_text = soup.get_text()

        # 1. Office (Despacho)
        extracted_office = extract_field_by_label(soup, r"Despacho")
        if extracted_office:
            info["office"] = extracted_office
        else:
            office_match = re.search(r"Despacho[:\s]+([A-Za-z0-9\.\-]+)", page_text, re.IGNORECASE)
            if office_match:
                info["office"] = office_match.group(1).strip()

        # 2. Phone (Teléfono)
        extracted_phone = extract_field_by_label(soup, r"Teléfono|Telefono")
        if extracted_phone:
            info["phone"] = extracted_phone
        else:
            phone_match = re.search(r"(?:Teléfono|Telefono)[:\s]+(\d[\d\s]{8,})", page_text, re.IGNORECASE)
            if phone_match:
                info["phone"] = clean_text(phone_match.group(1))

        # 3. Email
        email_match = re.search(r"[\w\.-]+@uvigo\.(?:es|gal)", page_text)
        if email_match:
            info["email"] = email_match.group(0)

        # 4. UVigo / Tutoring URL (The UVigo PDI link serves as tutoring page)
        tutorias_link = soup.find("a", href=re.compile(r"uvigo\.gal/.*pdi"))
        if tutorias_link:
            url_found = tutorias_link.get("href")
            info["uvigo_url"] = url_found
            info["tutoring_url"] = url_found

        # 5. Virtual Office
        virtual_link = soup.find("a", href=re.compile(r"campusremotouvigo"))
        if virtual_link:
            info["virtual_office"] = virtual_link.get("href")

        # 6. Clean Subject Extraction (only within docencia sections)
        docencia_section = soup.find(
            lambda tag: tag.name in ["div", "section"]
            and ("docencia" in tag.get("class", []) or "f-docencia" in tag.get("class", []))
        )
        
        if not docencia_section:
            docencia_section = soup.find(lambda tag: "Asignaturas" in tag.text)
            if docencia_section:
                docencia_section = docencia_section.parent

        if docencia_section:
            subjects_links = docencia_section.find_all("a")
            for sl in subjects_links:
                subj_name = clean_text(sl.text)
                href = sl.get("href", "")
                if (
                    subj_name 
                    and len(subj_name) > 3 
                    and not href.startswith("mailto:") 
                    and "uvigo.gal" not in href
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
            "tutoring_url": extra_info["tutoring_url"],
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