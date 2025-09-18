import requests

# === CONFIG ===
API_URL = "https://www.monkeytype.live/ocr"        # Change if API is on a different host/port
API_KEY = "supersecretapikey"                 # Your API key
INPUT_PDF = "ocr.pdf"                     # Path to the PDF you want to OCR
OUTPUT_PDF = "searchable.pdf"                # Path to save the resulting PDF

# === SEND REQUEST ===
with open(INPUT_PDF, "rb") as f:
    files = {"file": (INPUT_PDF, f, "application/pdf")}
    headers = {"X-API-Key": API_KEY}

    print(f"Uploading {INPUT_PDF} for OCR...")
    response = requests.post(API_URL, headers=headers, files=files)

# === HANDLE RESPONSE ===
if response.status_code == 200:
    with open(OUTPUT_PDF, "wb") as out_file:
        out_file.write(response.content)
    print(f"OCR complete! Searchable PDF saved as {OUTPUT_PDF}")
else:
    print(f"Error {response.status_code}: {response.text}")
