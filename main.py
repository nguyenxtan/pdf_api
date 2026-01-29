"""
PDF to Images API - FastAPI service for converting PDF pages to images
Uses poppler (pdftoppm) for high-quality rendering suitable for OCR
"""

import os
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

# Configuration
TEMP_BASE_DIR = Path("/tmp/pdf2img")
TEMP_BASE_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="PDF to Images API",
    description="Convert PDF pages to images for OCR processing",
    version="1.0.0"
)


class ConversionResponse(BaseModel):
    ok: bool
    job_id: str
    format: str
    dpi: int
    count: int
    files: list[str]
    download_base: str


class ErrorResponse(BaseModel):
    ok: bool = False
    error: str


def cleanup_job_folder(job_path: Path) -> None:
    """Remove job folder if it exists"""
    if job_path.exists():
        shutil.rmtree(job_path)


def validate_dpi(dpi: int) -> int:
    """Validate and clamp DPI value to allowed range"""
    if dpi < 72:
        return 72
    if dpi > 600:
        return 600
    return dpi


def convert_pdf_to_images(
    pdf_path: Path,
    output_dir: Path,
    fmt: str = "png",
    dpi: int = 300
) -> tuple[bool, str, list[str]]:
    """
    Convert PDF to images using pdftoppm

    Returns:
        (success: bool, error_msg: str, files: list[str])
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Build pdftoppm command
    # Output pattern: output_dir/page will create page-1.png, page-2.png, ...
    output_prefix = str(output_dir / "page")

    cmd = [
        "pdftoppm",
        "-r", str(dpi),  # Resolution in DPI
        str(pdf_path),
        output_prefix
    ]

    # Add format-specific flags
    if fmt == "png":
        cmd.insert(1, "-png")
    elif fmt == "jpeg":
        cmd.insert(1, "-jpeg")
        cmd.extend(["-jpegopt", "quality=95"])  # High quality for OCR

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        if result.returncode != 0:
            error_msg = result.stderr or "pdftoppm failed with unknown error"
            return False, error_msg, []

        # List generated files
        extension = "png" if fmt == "png" else "jpg"
        files = sorted([
            f.name for f in output_dir.glob(f"page-*.{extension}")
        ])

        if not files:
            return False, "No images generated from PDF", []

        return True, "", files

    except subprocess.TimeoutExpired:
        return False, "PDF conversion timed out (5 minutes)", []
    except FileNotFoundError:
        return False, "pdftoppm not found. Install poppler-utils.", []
    except Exception as e:
        return False, f"Conversion error: {str(e)}", []


@app.post("/pdf-to-images", response_model=ConversionResponse)
async def pdf_to_images(
    pdf: UploadFile = File(..., description="PDF file to convert"),
    fmt: Literal["png", "jpeg"] = Query("png", description="Output image format"),
    dpi: int = Query(300, ge=72, le=600, description="DPI resolution (72-600)")
) -> ConversionResponse | JSONResponse:
    """
    Convert PDF pages to individual image files

    Each page becomes a separate image file suitable for OCR processing.
    Files are stored temporarily and accessible via download endpoint.
    """

    # Validate file
    if not pdf.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    if not pdf.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")

    # Validate and clamp DPI
    dpi = validate_dpi(dpi)

    # Generate unique job ID
    job_id = str(uuid.uuid4())
    job_path = TEMP_BASE_DIR / job_id
    job_path.mkdir(parents=True, exist_ok=True)

    # Save uploaded PDF temporarily
    pdf_temp_path = job_path / "input.pdf"

    try:
        # Write uploaded file to disk
        content = await pdf.read()
        with open(pdf_temp_path, "wb") as f:
            f.write(content)

        # Convert PDF to images
        success, error_msg, files = convert_pdf_to_images(
            pdf_path=pdf_temp_path,
            output_dir=job_path,
            fmt=fmt,
            dpi=dpi
        )

        if not success:
            # Clean up on failure
            cleanup_job_folder(job_path)
            return JSONResponse(
                status_code=500,
                content={"ok": False, "error": error_msg}
            )

        # Remove input PDF to save space
        pdf_temp_path.unlink()

        return ConversionResponse(
            ok=True,
            job_id=job_id,
            format=fmt,
            dpi=dpi,
            count=len(files),
            files=files,
            download_base=f"/download/{job_id}/"
        )

    except Exception as e:
        # Clean up on any error
        cleanup_job_folder(job_path)
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": f"Server error: {str(e)}"}
        )


@app.get("/download/{job_id}/{filename}")
async def download_image(job_id: str, filename: str) -> FileResponse | JSONResponse:
    """
    Download a specific image file from a conversion job

    Use the job_id and filename from the /pdf-to-images response
    """

    # Validate job_id format (basic UUID check)
    try:
        uuid.UUID(job_id)
    except ValueError:
        return JSONResponse(
            status_code=400,
            content={"ok": False, "error": "Invalid job_id format"}
        )

    # Validate filename (prevent path traversal)
    if ".." in filename or "/" in filename or "\\" in filename:
        return JSONResponse(
            status_code=400,
            content={"ok": False, "error": "Invalid filename"}
        )

    # Check if file exists
    file_path = TEMP_BASE_DIR / job_id / filename

    if not file_path.exists() or not file_path.is_file():
        return JSONResponse(
            status_code=404,
            content={"ok": False, "error": "File not found"}
        )

    # Determine media type
    extension = filename.lower().split('.')[-1]
    media_type_map = {
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg"
    }
    media_type = media_type_map.get(extension, "application/octet-stream")

    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=filename
    )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    # Check if pdftoppm is available
    try:
        result = subprocess.run(
            ["pdftoppm", "-v"],
            capture_output=True,
            timeout=5
        )
        poppler_available = result.returncode == 0
    except:
        poppler_available = False

    return {
        "status": "healthy" if poppler_available else "degraded",
        "poppler_available": poppler_available,
        "temp_dir": str(TEMP_BASE_DIR)
    }


@app.delete("/cleanup/{job_id}")
async def cleanup_job(job_id: str) -> JSONResponse:
    """
    Manually delete a job folder (optional endpoint for cleanup)
    """
    try:
        uuid.UUID(job_id)
    except ValueError:
        return JSONResponse(
            status_code=400,
            content={"ok": False, "error": "Invalid job_id format"}
        )

    job_path = TEMP_BASE_DIR / job_id

    if not job_path.exists():
        return JSONResponse(
            status_code=404,
            content={"ok": False, "error": "Job not found"}
        )

    cleanup_job_folder(job_path)

    return JSONResponse(
        content={"ok": True, "message": f"Job {job_id} cleaned up"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
