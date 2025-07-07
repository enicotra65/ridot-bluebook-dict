import os
import json
import requests
from urllib.parse import urlparse
import re

PDF_FOLDER = os.path.join(os.path.dirname(__file__), '../bluebook_pdfs')
CACHE = {}


def get_cached_bluebooks():
    if 'bluebooks' in CACHE:
        return CACHE['bluebooks']

    if not os.path.exists(PDF_FOLDER):
        os.makedirs(PDF_FOLDER)

    with open('bluebooks.json', 'r') as f:
        data = json.load(f)

    urls = data.get('urls', {})
    valid_pdfs = []

    for filename, url in urls.items():
        local_path = os.path.join(PDF_FOLDER, filename)
        if not os.path.exists(local_path):
            try:
                response = requests.get(url)
                if response.status_code == 200:
                    with open(local_path, 'wb') as f:
                        f.write(response.content)
                    print(f"Downloaded: {filename}")
            except Exception as e:
                print(f"Error downloading {url}: {e}")

        if os.path.exists(local_path):
            valid_pdfs.append(filename)

    CACHE['bluebooks'] = valid_pdfs
    return valid_pdfs