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

def clean_office(raw_office_text):
    if not raw_office_text:
        return "No especificado"
    
    cleaned = raw_office_text.strip()
    if len(cleaned) <= 20:
        return cleaned

    match = re.search(r'(?:Despacho\s*)?([A-Za-z0-9\.\-]{1,8})', cleaned, re.IGNORECASE)
    if match:
        return match.group(0).strip()
        
    return "No especificado"
    
def clean_text(text):
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def extract_value_after_label(soup, label_text):
    """Busca etiquetas como 'Despacho:', 'Correo electrónico:', etc."""
    label = soup.find(lambda tag: tag.name in ["td", "th", "strong", "span", "p", "div"] and label_text.lower() in tag.text.lower())
    if not label:
        return ""
    
    next_el = label.find_next_sibling()
    if next_el and next_el.text.strip():
        return clean_text(next_el.text)

    parent = label.parent
    if parent:
        text = parent.text.replace(label.text, "")
        return clean_text(text)
        
    return ""


def extract_teacher_info(profile_url):
    info = {
        "office": "No especificado",
        "email": "",
        "virtual_office": "",
        "tutoring_url": "",
        "subjects": []
    }

    try:
        res = requests.get(profile_url, headers=HEADERS, timeout=10)
        if res.status_code != 200:
            return info

        soup = BeautifulSoup(res.content, "html.parser")
        page_text = soup.get_text()

        email_match = re.search(r"[\w\.-]+@uvigo\.(?:es|gal)", page_text)
        if email_match:
            info["email"] = email_match.group(0)

        tutorias_link = soup.find("a", href=re.compile(r"uvigo\.gal/.*pdi"))
        if tutorias_link:
            info["tutoring_url"] = tutorias_link.get("href")

        virtual_link = soup.find("a", href=re.compile(r"campusremotouvigo"))
        if virtual_link:
            info["virtual_office"] = virtual_link.get("href")

        subj_section = soup.find(lambda tag: "Asignaturas" in tag.text or "Asignaturas:" in tag.text)
        if subj_section and subj_section.parent:
            subjects_links = subj_section.parent.find_all("a")
            for sl in subjects_links:
                subj_name = clean_text(sl.text)
                if subj_name and subj_name not in info["subjects"]:
                    info["subjects"].append(subj_name)

    except Exception as e:
        print(f"   Error parseando {profile_url}: {e}")

    return info


def scrape_all_teachers():
    print(f"🔍 Conectando a {TEACHERS_LIST_URL}...")
    res = requests.get(TEACHERS_LIST_URL, headers=HEADERS, timeout=15)
    
    if res.status_code != 200:
        print(f" Error HTTP {res.status_code}")
        return

    soup = BeautifulSoup(res.content, "html.parser")
    teachers_data = []

    # Obtener todos los enlaces a perfiles de profesor
    links = soup.select("a[href*='/docencia/profesorado/profesor/']")
    visited_urls = set()

    for idx, link in enumerate(links, start=1):
        name = clean_text(link.text)
        url = link.get("href")

        if not url or url in visited_urls:
            continue

        if not url.startswith("http"):
            url = BASE_URL + url

        visited_urls.add(url)
        print(f"[{len(visited_urls)}] Extrayendo: {name}")

        extra_info = extract_teacher_info(url)

        teachers_data.append({
            "id": f"p-{idx}",
            "name": name,
            "office": extra_info["office"],
            "email": extra_info["email"],
            "virtual_office": extra_info["virtual_office"],
            "tutoring_url": extra_info["tutoring_url"],
            "subjects": extra_info["subjects"],
            "url": url
        })

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "teachers": teachers_data
    }

    with open("teachers.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n ¡Guardados {len(teachers_data)} profesores en 'teachers.json'!")


if __name__ == "__main__":
    scrape_all_teachers()