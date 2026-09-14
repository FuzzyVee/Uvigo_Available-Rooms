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
        "uvigo_url": "",
        "subjects": []
    }

    try:
        res = requests.get(profile_url, headers=HEADERS, timeout=10)
        if res.status_code != 200:
            return info

        soup = BeautifulSoup(res.content, "html.parser")
        content = soup.select_one(".entry-content, .pf-profile, article, .post-inner")
        if not content:
            content = soup

        # 1. Extracción de Despacho físico (ej: Despacho: 209 o D2)
        text_nodes = content.find_all(["p", "td", "li", "div", "span"])
        for node in text_nodes:
            text = clean_text(node.text)
            
            # Buscar Despacho
            if info["office"] == "No especificado" and re.search(r"despacho", text, re.IGNORECASE):
                match = re.search(r"despacho[:\s]+([A-Za-z0-9\.\-]+)", text, re.IGNORECASE)
                if match:
                    val = match.group(1).strip()
                    if val and val.lower() != "despacho":
                        info["office"] = val

            # Buscar Teléfono
            if not info["phone"] and re.search(r"teléfono|telefono", text, re.IGNORECASE):
                match = re.search(r"(?:teléfono|telefono)[:\s]+(\+?\d[\d\s]{7,})", text, re.IGNORECASE)
                if match:
                    info["phone"] = clean_text(match.group(1))

        # 2. Extracción de Tutorías / URL UVigo (si el despacho sigue sin especificar, o para el campo uvigo_url)
        tutorias_tag = content.find(lambda tag: tag.name in ["strong", "b", "p", "div"] and "tutorías" in tag.text.lower())
        if tutorias_tag:
            link_el = tutorias_tag.find_next("a", href=True)
            if link_el:
                info["uvigo_url"] = link_el["href"].strip()

        if not info["uvigo_url"]:
            uvigo_link = content.select_one("a[href*='/pdi/'], a[href*='uvigo.gal'][href*='administracion-persoal']")
            if uvigo_link:
                info["uvigo_url"] = uvigo_link["href"].strip()

        # Si no hay despacho físico pero sí hay enlace de tutorías/PDI, opcionalmente asignarlo o dejar despacho limpio
        # (Si prefieres que office tenga la URL solo cuando no hay despacho físico, descomenta la siguiente línea):
        # if info["office"] == "No especificado" and info["uvigo_url"]:
        #     info["office"] = info["uvigo_url"]

        # 3. Extracción de Email
        email_link = content.select_one("a[href^='mailto:']")
        if email_link:
            info["email"] = email_link["href"].replace("mailto:", "").strip()

        # 4. Extracción limpia de Asignaturas
        asig_heading = content.find(lambda tag: tag.name in ["strong", "b", "p", "div", "h3", "h4"] and "asignaturas" in tag.text.lower())
        if asig_heading:
            parent_block = asig_heading.find_parent(["div", "p", "section"]) or asig_heading.parent
            if parent_block:
                text_block = parent_block.get_text(separator="\n")
                lines = [clean_text(l) for l in text_block.split("\n") if clean_text(l)]
                
                capture = False
                for line in lines:
                    if "asignaturas:" in line.lower():
                        capture = True
                        continue
                    if capture:
                        if any(term in line.lower() for term in ["datos de contacto", "despacho:", "teléfono:", "correo electrónico:", "tutorías:"]):
                            break
                        if "grao en" in line.lower() or "máster" in line.lower():
                            continue
                        if len(line) > 2 and line not in info["subjects"]:
                            info["subjects"].append(line)

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