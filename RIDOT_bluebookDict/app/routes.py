# FULL FILE BEGINS HERE
import os, re, time, pickle
import fitz  # PyMuPDF
from flask import Blueprint, render_template, jsonify, send_from_directory, request

blueprint = Blueprint("main", __name__)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
PDF_FOLDER = os.path.join(BASE_DIR, "..", "pdfs")
CACHE_FOLDER = os.path.join(BASE_DIR, "..", "cache")
os.makedirs(CACHE_FOLDER, exist_ok=True)

CACHE_PATH = os.path.join(CACHE_FOLDER, "full_data_cache.pkl")
DISPLAY_NAMES_PATH = os.path.join(CACHE_FOLDER, "pdf_display_names.pkl")

PART_REGEX = re.compile(r'^Part [0-9A-Z]+')
SECTION_REGEX = re.compile(r'^SECTION')
SUBSECTION_SCAN_PATTERN = re.compile(r'\b[A-Z]?\d{1,3}\.\d{2}\b')

def extract_part(toc):
    return [{'title': item[1], 'page_number': item[2]} for item in toc if PART_REGEX.match(item[1])]

def contains_subsections(doc, toc, section_index):
    section_page = toc[section_index][2]
    end_page = doc.page_count
    if section_index + 1 < len(toc):
        for i in range(section_index + 1, len(toc)):
            if PART_REGEX.match(toc[i][1]) or SECTION_REGEX.match(toc[i][1]):
                end_page = toc[i][2] - 1
                break
    for page_num in range(section_page - 1, end_page):
        text = doc.load_page(page_num).get_text("text")
        if SUBSECTION_SCAN_PATTERN.search(text):
            return True, section_page, end_page
    return False, section_page, end_page

def extract_section(doc, toc, part_title):
    section_info = []
    for idx, item in enumerate(toc):
        if item[1] == part_title:
            end_index = idx + 1
            while end_index < len(toc) and not PART_REGEX.match(toc[end_index][1]):
                if SECTION_REGEX.match(toc[end_index][1]):
                    raw_title = toc[end_index][1]
                    has_subs, start_pg, end_pg = contains_subsections(doc, toc, end_index)
                    if has_subs:
                        section_info.append({
                            'title': raw_title,
                            'page_number': toc[end_index][2],
                            'range': (start_pg, end_pg)
                        })
                end_index += 1
            break
    return section_info

def extract_subsection(doc, section_number, start_pg, end_pg):
    subtopics = []
    seen = set()
    subsection_pattern = re.compile(rf'^{re.escape(section_number)}\.\d+\s+[A-Z].*$')

    for page_num in range(start_pg - 1, end_pg):
        lines = doc.load_page(page_num).get_text("text").split("\n")
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if re.match(rf'^{re.escape(section_number)}\.\d+$', line):
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if re.match(r'^[A-Z]', next_line):
                        line = f"{line} {next_line}"
                        i += 1
            if subsection_pattern.match(line) and line not in seen:
                subtopics.append({'title': line.rstrip('.'), 'page_number': page_num + 1})
                seen.add(line)
            i += 1
    return subtopics

def format_display_name(filename):
    try:
        year, month = filename.replace(".pdf", "").split("_")
        month_name = {
            "01": "January", "02": "February", "03": "March", "04": "April",
            "05": "May", "06": "June", "07": "July", "08": "August",
            "09": "September", "10": "October", "11": "November", "12": "December"
        }.get(month, "Unknown")
        return f"{month_name} {year}, RIDOT Bluebook"
    except:
        return filename

def build_cache():
    import json
    import urllib.request

    full_cache = {}
    display_names = {}
    start = time.time()
    print("[Cache] Building Bluebook cache...")

    # Ensure PDF folder exists
    os.makedirs(PDF_FOLDER, exist_ok=True)

    # === Load bluebooks.json ===
    json_path = os.path.join(BASE_DIR, "..", "bluebooks.json")
    if os.path.exists(json_path):
        with open(json_path, "r") as f:
            bluebook_data = json.load(f)
        urls = bluebook_data.get("urls", {})
    else:
        print("[!] bluebooks.json not found. Skipping PDF downloads.")
        urls = {}

    # === Download any missing PDFs ===
    for fname, url in urls.items():
        local_path = os.path.join(PDF_FOLDER, fname)
        if not os.path.exists(local_path):
            try:
                print(f"[↓] Downloading {fname}...")
                urllib.request.urlretrieve(url, local_path)
                print(f"[✓] Saved {fname}")
            except Exception as e:
                print(f"[✗] Failed to download {fname}: {e}")

    # Check if any PDFs exist
    pdf_files = [f for f in os.listdir(PDF_FOLDER) if f.endswith(".pdf")]
    if not pdf_files:
        print("[!] No PDF files found. Skipping cache build.")
        return {}, {}

    for fname in pdf_files:
        display_names[fname] = format_display_name(fname)
        pdf_path = os.path.join(PDF_FOLDER, fname)
        print(f"\n[→] Processing {fname}...")

        with fitz.open(pdf_path) as doc:
            toc = doc.get_toc(simple=True)
            structured = {"parts": [], "sections": {}}

            for part in extract_part(toc):
                print(f"  [•] Found part: {part['title']}")
                structured["parts"].append({"title": part["title"], "page": part["page_number"]})
                sections = extract_section(doc, toc, part["title"])
                structured["sections"][part["title"]] = []

                for sec in sections:
                    print(f"    └─ Section: {sec['title']} (page {sec['page_number']})")
                    sec_obj = {
                        "title": sec["title"],
                        "page": sec["page_number"],
                        "subsections": []
                    }
                    section_number = sec["title"].split()[1]
                    subsections = extract_subsection(doc, section_number, *sec["range"])
                    print(f"      └─ Found {len(subsections)} subsections")
                    sec_obj["subsections"] = subsections
                    structured["sections"][part["title"]].append(sec_obj)

                # === Hardcoded workaround for problematic sections ===
                if part["title"] == "Part M - Materials":
                    print("  [!] Hardcoding SECTION M19 and M20")
                    structured["sections"][part["title"]].append({
                        "title": "SECTION M19  — ANTI-GRAFFITI SYSTEMS",
                        "page": 872,
                        "subsections": [
                            {"title": "M19.01 APPROVED PRODUCTS.", "page_number": 873},
                            {"title": "M19.02 NON APPROVED PRODUCTS SUBMITTED FOR APPROVAL.", "page_number": 873}
                        ]
                    })
                    structured["sections"][part["title"]].append({
                        "title": "SECTION M20  — GEOTEXTILES",
                        "page": 874,
                        "subsections": [
                            {"title": "M20.01 GEOTEXTILE MATERIALS", "page_number": 874},
                            {"title": "M20.02 GEOTEXTILE INSTALLATION", "page_number": 874}
                        ]
                    })

            full_cache[fname] = structured

    # Save cache to disk
    with open(CACHE_PATH, "wb") as f:
        pickle.dump(full_cache, f)
    with open(DISPLAY_NAMES_PATH, "wb") as f:
        pickle.dump(display_names, f)

    print(f"\n[✓] Cache completed in {round(time.time() - start, 2)} seconds.")
    return full_cache, display_names


# === Load or Build Cache ===
if os.path.exists(CACHE_PATH) and os.path.exists(DISPLAY_NAMES_PATH):
    with open(CACHE_PATH, "rb") as f:
        full_data_cache = pickle.load(f)
    with open(DISPLAY_NAMES_PATH, "rb") as f:
        pdf_display_names = pickle.load(f)
else:
    full_data_cache, pdf_display_names = build_cache()

# === Routes ===
@blueprint.route("/")
def index():
    return render_template("index.html", pdf_list=list(pdf_display_names.keys()), pdf_display_names=pdf_display_names)

@blueprint.route("/get_cached_titles")
def get_cached_titles():
    return jsonify(full_data_cache)

@blueprint.route("/get_pdfs")
def get_pdfs():
    return jsonify([{"filename": k, "display": v} for k, v in pdf_display_names.items()])

@blueprint.route("/pdfs/<path:filename>")
def serve_pdf(filename):
    return send_from_directory(PDF_FOLDER, filename)

@blueprint.route("/viewer")
def viewer():
    pdf_url = request.args.get("file")
    page = request.args.get("page", default=1, type=int)
    if not pdf_url:
        return "Missing PDF URL", 400
    return render_template("viewer.html", pdf_url=pdf_url, page=page)


@blueprint.route("/view_pdf/<filename>")
def view_pdf(filename):
    page = request.args.get("page", type=int)
    if not page or filename not in pdf_display_names:
        return "Invalid request.", 400

    pdf_path = os.path.join(PDF_FOLDER, filename)
    if not os.path.exists(pdf_path):
        return "PDF not found.", 404

    # Generate the relative file path for the viewer to open
    rel_path = f"/pdfs/{filename}"
    return f'''
    <html>
      <head>
        <meta http-equiv="refresh" content="0; url=/static/pdfjs/viewer.html?file={rel_path}&page={page}" />
      </head>
      <body>
        <p>Redirecting to PDF Viewer...<br>
        <a href="/static/pdfjs/viewer.html?file={rel_path}&page={page}">Click here if not redirected.</a></p>
      </body>
    </html>
    '''

