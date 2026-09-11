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

        # 1. Extracción de enlaces directos (Email, Campus Remoto, Tutorías UVigo)
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            
            if href.startswith("mailto:") and not info["email"]:
                info["email"] = href.replace("mailto:", "").strip()
            elif "campusremotouvigo" in href and not info["virtual_office"]:
                info["virtual_office"] = href
            elif ("uvigo.gal" in href or "uvigo.es" in href) and ("/pdi/" in href or "docente" in href):
                if not info["uvigo_url"]:
                    info["uvigo_url"] = href

        # Asignar la URL de tutorías/PDI al campo office tal como pediste
        if info["uvigo_url"]:
            info["office"] = info["uvigo_url"]

        # 2. Extracción limpia de teléfono buscando celdas de tabla o filas específicas
        for tr in soup.find_all(["tr", "li", "div"]):
            text = clean_text(tr.text)
            if re.search(r"teléfono|telefono", text, re.IGNORECASE) and not info["phone"]:
                match = re.search(r"(?:teléfono|telefono)[:\s]+(\+?\d[\d\s]{7,})", text, re.IGNORECASE)
                if match:
                    info["phone"] = clean_text(match.group(1))

        # 3. Extracción estricta de Asignaturas (solo dentro de bloques de docencia reales)
        docencia_section = soup.find(
            lambda tag: tag.name in ["div", "section", "ul"] 
            and ("docencia" in "".join(tag.get("class", [])).lower() or "f-docencia" in "".join(tag.get("class", [])).lower())
        )

        if not docencia_section:
            # Búsqueda alternativa por encabezado de asignaturas
            heading = soup.find(lambda tag: tag.name in ["h2", "h3", "h4"] and "docencia" in tag.text.lower())
            if heading:
                docencia_section = heading.find_next_sibling()

        if docencia_section:
            for a in docencia_section.find_all("a", href=True):
                subj_name = clean_text(a.text)
                href = a["href"]
                if (
                    subj_name 
                    and len(subj_name) > 3 
                    and not href.startswith("mailto:") 
                    and "uvigo" not in href 
                    and "/profesorado/" not in href
                    and subj_name not in info["subjects"]
                ):
                    info["subjects"].append(subj_name)

    except Exception as e:
        print(f"Error parsing {profile_url}: {e}")

    return info


def scrape_all_teachers():
    print(f"Conectando a {TEACHERS_LIST_URL}...")
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
        print(f"[{len(visited_urls)}] Procesando: {name}")

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

    print(f"\nGuardados {len(teachers_data)} profesores en 'teachers.json'")


if __name__ == "__main__":
    scrape_all_teachers()