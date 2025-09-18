from fastapi import FastAPI, File, UploadFile, Response, Header, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import tempfile
import subprocess
import shutil
import os

API_KEY = "supersecretapikey"  # Replace with your own key
MAX_FILE_SIZE = 200 * 1024 * 1024  # 200 MB in bytes

app = FastAPI(title="OCR PDF API", version="1.0")

# Middleware to enforce file size limit
class LimitUploadSizeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.headers.get("content-length"):
            content_length = int(request.headers["content-length"])
            if content_length > MAX_FILE_SIZE:
                raise HTTPException(status_code=413, detail="File too large (max 200MB)")
        return await call_next(request)

app.add_middleware(LimitUploadSizeMiddleware)

def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")

@app.post("/ocr")
async def ocr_pdf(file: UploadFile = File(...), x_api_key: str = Header(...)):
    # Verify API Key
    verify_api_key(x_api_key)

    # Create temp input/output files
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as input_pdf:
        shutil.copyfileobj(file.file, input_pdf)
        input_path = input_pdf.name
    
    output_fd, output_path = tempfile.mkstemp(suffix=".pdf")
    os.close(output_fd)  # Only need the path

    try:
        # Run OCRmyPDF
        subprocess.run(
            ["ocrmypdf", "--jobs", "6", "--optimize", "3", "--fast-web-view", "1", input_path, output_path],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        # Return searchable PDF as response
        with open(output_path, "rb") as f:
            pdf_bytes = f.read()
        return Response(content=pdf_bytes, media_type="application/pdf")

    except subprocess.CalledProcessError as e:
        return {"error": f"OCR failed: {e.stderr.decode()}"}

    finally:
        # Clean up
        if os.path.exists(input_path):
            os.remove(input_path)
        if os.path.exists(output_path):
            os.remove(output_path)
