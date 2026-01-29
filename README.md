# PDF to Images API

REST API đơn giản để chuyển đổi PDF scan thành từng ảnh riêng biệt (mỗi trang 1 file) cho mục đích OCR.

## Tính năng

- Chuyển đổi PDF nhiều trang thành các file ảnh riêng lẻ
- Hỗ trợ định dạng PNG (lossless) và JPEG
- DPI tùy chỉnh (72-600, mặc định 300) cho OCR chất lượng cao
- Sử dụng poppler (pdftoppm) để render chất lượng tốt
- Không resize, không giảm chất lượng
- API đơn giản để tích hợp với n8n hoặc automation tools khác

## Yêu cầu hệ thống

- Docker (khuyến nghị)
- Hoặc Python 3.11+ và poppler-utils nếu chạy local

## Cài đặt và chạy

### Chạy bằng Docker Compose (Khuyến nghị cho Production)

```bash
# Start service
docker compose up -d

# Check logs
docker compose logs -f

# Check status
docker compose ps

# Health check
curl http://localhost:8000/health
```

**Deploy lên VPS Ubuntu?** Xem hướng dẫn chi tiết tại [DEPLOY.md](DEPLOY.md)

### Chạy bằng Docker (Manual)

1. Build Docker image:
```bash
docker build -t pdf-api .
```

2. Chạy container:
```bash
docker run -d -p 8000:8000 --name pdf-api pdf-api
```

3. Kiểm tra health:
```bash
curl http://localhost:8000/health
```

### Chạy local (không dùng Docker)

1. Cài đặt poppler-utils:

**Ubuntu/Debian:**
```bash
sudo apt-get install poppler-utils
```

**macOS:**
```bash
brew install poppler
```

**Windows:**
Tải poppler for Windows từ: https://github.com/oschwartz10612/poppler-windows/releases/

2. Cài đặt Python dependencies:
```bash
pip install -r requirements.txt
```

3. Chạy server:
```bash
python main.py
```

Hoặc:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

API sẽ chạy tại: http://localhost:8000

## Sử dụng API

### 1. Convert PDF to Images

**Endpoint:** `POST /pdf-to-images`

**Parameters:**
- `pdf` (file, required): File PDF cần convert
- `fmt` (query, optional): Format ảnh output - "png" hoặc "jpeg" (default: "png")
- `dpi` (query, optional): DPI resolution 72-600 (default: 300)

**Ví dụ với curl:**

```bash
# Convert PDF to PNG với DPI mặc định (300)
curl -X POST "http://localhost:8000/pdf-to-images" \
  -F "pdf=@document.pdf"

# Convert to JPEG với DPI 200
curl -X POST "http://localhost:8000/pdf-to-images?fmt=jpeg&dpi=200" \
  -F "pdf=@document.pdf"

# Convert với DPI cao cho OCR tốt hơn
curl -X POST "http://localhost:8000/pdf-to-images?dpi=400" \
  -F "pdf=@scan.pdf"
```

**Response thành công:**
```json
{
  "ok": true,
  "job_id": "a3f5b7c9-1234-5678-90ab-cdef12345678",
  "format": "png",
  "dpi": 300,
  "count": 5,
  "files": [
    "page-1.png",
    "page-2.png",
    "page-3.png",
    "page-4.png",
    "page-5.png"
  ],
  "download_base": "/download/a3f5b7c9-1234-5678-90ab-cdef12345678/"
}
```

**Response lỗi:**
```json
{
  "ok": false,
  "error": "pdftoppm failed: Invalid PDF"
}
```

### 2. Download ảnh

**Endpoint:** `GET /download/{job_id}/{filename}`

**Ví dụ:**

```bash
# Download từng file
curl -O "http://localhost:8000/download/a3f5b7c9-1234-5678-90ab-cdef12345678/page-1.png"
curl -O "http://localhost:8000/download/a3f5b7c9-1234-5678-90ab-cdef12345678/page-2.png"
```

### 3. Health Check

**Endpoint:** `GET /health`

```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
  "status": "healthy",
  "poppler_available": true,
  "temp_dir": "/tmp/pdf2img"
}
```

### 4. Cleanup Job (Optional)

**Endpoint:** `DELETE /cleanup/{job_id}`

```bash
curl -X DELETE "http://localhost:8000/cleanup/a3f5b7c9-1234-5678-90ab-cdef12345678"
```

## Workflow với n8n

Ví dụ workflow tự động:

1. **Upload PDF** → POST `/pdf-to-images`
2. **Nhận response** với `job_id`, `count`, và `files`
3. **Loop qua từng file** trong array `files`
4. **Download từng ảnh** → GET `/download/{job_id}/{filename}`
5. **OCR từng ảnh** → Gửi đến OCR service
6. **Aggregate kết quả** từ tất cả các trang
7. **(Optional) Cleanup** → DELETE `/cleanup/{job_id}`

## Script test hoàn chỉnh

```bash
#!/bin/bash

# 1. Upload và convert PDF
RESPONSE=$(curl -s -X POST "http://localhost:8000/pdf-to-images?dpi=300" \
  -F "pdf=@test.pdf")

echo "Response: $RESPONSE"

# 2. Parse job_id và files
JOB_ID=$(echo $RESPONSE | jq -r '.job_id')
FILES=$(echo $RESPONSE | jq -r '.files[]')

echo "Job ID: $JOB_ID"
echo "Files: $FILES"

# 3. Download tất cả các ảnh
for FILE in $FILES; do
  echo "Downloading $FILE..."
  curl -O "http://localhost:8000/download/$JOB_ID/$FILE"
done

echo "Done! All images downloaded."

# 4. Cleanup (optional)
# curl -X DELETE "http://localhost:8000/cleanup/$JOB_ID"
```

## Cấu trúc thư mục

```
/tmp/pdf2img/
├── <job_id_1>/
│   ├── page-1.png
│   ├── page-2.png
│   └── page-3.png
├── <job_id_2>/
│   ├── page-1.png
│   └── page-2.png
└── ...
```

## API Documentation

Sau khi chạy server, truy cập:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Lưu ý

- Files được lưu tạm tại `/tmp/pdf2img/<job_id>/`
- Mỗi job tạo một folder riêng với UUID
- Nên cleanup các job cũ định kỳ để tiết kiệm disk space
- DPI cao hơn = file lớn hơn nhưng OCR chính xác hơn
- PNG cho chất lượng tốt nhất (lossless), JPEG cho file nhỏ hơn

## Troubleshooting

**Lỗi "pdftoppm not found":**
- Cài đặt poppler-utils (xem phần Cài đặt)
- Nếu dùng Docker, rebuild image

**Lỗi timeout:**
- PDF quá lớn hoặc nhiều trang
- Tăng timeout trong code nếu cần (mặc định 5 phút)

**Lỗi "Invalid PDF":**
- File upload không phải PDF hợp lệ
- PDF bị corrupt hoặc được bảo vệ bởi password

## License

MIT License - Free to use
