from fastapi import FastAPI, File, UploadFile, Response, Header, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import tempfile, subprocess, shutil, os, multiprocessing
from pypdf import PdfReader

API_KEY = "supersecretapikey"
MAX_FILE_SIZE = 200 * 1024 * 1024
CPU_COUNT = multiprocessing.cpu_count()

app = FastAPI(title="OCR PDF API", version="1.2")


# ---------------- Middleware to limit upload size ----------------
class LimitUploadSizeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.headers.get("content-length"):
            content_length = int(request.headers["content-length"])
            if content_length > MAX_FILE_SIZE:
                raise HTTPException(status_code=413, detail="File too large (max 200 MB)")
        return await call_next(request)

app.add_middleware(LimitUploadSizeMiddleware)


# ---------------- Helper functions ----------------
def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")


def is_pdf_searchable_fast(path: str, sample_pages: int = 2) -> bool:
    """
    Quickly determine if a PDF has searchable text.
    Checks only the first `sample_pages` pages for performance.
    """
    try:
        reader = PdfReader(path)
        pages_to_check = min(len(reader.pages), sample_pages)
        for i in range(pages_to_check):
            text = reader.pages[i].extract_text()
            if text and text.strip():
                print("searchable")
                return True
        print("none searchable")        
        return False
    except Exception:
        print('Unable to check is is searchable')
       # return False


# ---------------- OCR Endpoint ----------------
@app.post("/ocr")
async def ocr_pdf(file: UploadFile = File(...), x_api_key: str = Header(...)):
    verify_api_key(x_api_key)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as input_pdf:
        shutil.copyfileobj(file.file, input_pdf)
        input_path = input_pdf.name

    output_fd, output_path = tempfile.mkstemp(suffix=".pdf")
    os.close(output_fd)

    try:
        # ✅ Quick text detection (top 2 pages)
        if is_pdf_searchable_fast(input_path):
            # Already searchable → return as-is
            with open(input_path, "rb") as f:
                return Response(content=f.read(), media_type="application/pdf")

        # 🔍 Otherwise run OCR only when needed
        subprocess.run(
            [
                "ocrmypdf",
                "--jobs=6",
                "--optimize", "2",
                "--fast-web-view", "1",
                input_path,
                output_path,
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        with open(output_path, "rb") as f:
            return Response(content=f.read(), media_type="application/pdf")

    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"OCR failed: {e.stderr.decode()}")

    finally:
        for path in (input_path, output_path):
            if os.path.exists(path):
                os.remove(path)
