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

        # Aislar el contenedor principal para evitar menús y pies de página
        content = soup.select_one(".entry-content, .pf-profile, article, .post-inner")
        if not content:
            content = soup

        # 1. Extracción de Tutorías (etiqueta "Tutorías:" o enlace PDI) y se asigna a office
        tutorias_tag = content.find(lambda tag: tag.name in ["strong", "b", "p", "div"] and "tutorías" in tag.text.lower())
        if tutorias_tag:
            # Buscar el enlace dentro del mismo bloque o en el siguiente hermano
            link_el = tutorias_tag.find_next("a", href=True)
            if link_el:
                url = link_el["href"].strip()
                info["uvigo_url"] = url
                info["office"] = url

        # Fallback si no encuentra la etiqueta por texto pero sí el enlace PDI
        if info["office"] == "No especificado":
            uvigo_link = content.select_one("a[href*='/pdi/'], a[href*='uvigo.gal'][href*='administracion-persoal']")
            if uvigo_link:
                url = uvigo_link["href"].strip()
                info["uvigo_url"] = url
                info["office"] = url

        # 2. Extracción de Email
        email_link = content.select_one("a[href^='mailto:']")
        if email_link:
            info["email"] = email_link["href"].replace("mailto:", "").strip()

        # 3. Extracción de Teléfono
        for node in content.find_all(["p", "td", "li", "div"]):
            text = clean_text(node.text)
            if not info["phone"] and re.search(r"teléfono|telefono", text, re.IGNORECASE):
                match = re.search(r"(?:teléfono|telefono)[:\s]+(\+?\d[\d\s]{7,})", text, re.IGNORECASE)
                if match:
                    info["phone"] = clean_text(match.group(1))

        # 4. Extracción limpia de Asignaturas (basado en la sección de la imagen)
        asig_heading = content.find(lambda tag: tag.name in ["strong", "b", "p", "div", "h3", "h4"] and "asignaturas" in tag.text.lower())
        if asig_heading:
            # Recorremos los siguientes elementos hasta encontrar otra sección principal o fin de bloque
            parent_block = asig_heading.find_parent(["div", "p", "section"]) or asig_heading.parent
            if parent_block:
                # Extraer texto o enlaces de asignaturas
                text_block = parent_block.get_text(separator="\n")
                lines = [clean_text(l) for l in text_block.split("\n") if clean_text(l)]
                
                # Filtrar la línea de la etiqueta "Asignaturas:" y nombres de grados (ej. "Grao en Enxeñaría Informática")
                capture = False
                for line in lines:
                    if "asignaturas:" in line.lower():
                        capture = True
                        continue
                    if capture:
                        # Si llegamos a otra sección como "Datos de contacto", paramos
                        if any(term in line.lower() for term in ["datos de contacto", "despacho:", "teléfono:", "correo electrónico:", "tutorías:"]):
                            break
                        # Omitir nombres genéricos de grados si aparecen solos
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