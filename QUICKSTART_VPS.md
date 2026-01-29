# Quick Start - Deploy lên VPS Ubuntu trong 2 phút

## Cách 1: One-Command Deploy (Nhanh nhất)

SSH vào VPS và chạy:

```bash
curl -fsSL https://raw.githubusercontent.com/nguyenxtan/pdf_api/main/deploy.sh | bash
```

Script sẽ tự động:
- Cài Docker & Docker Compose (nếu chưa có)
- Clone repository
- Build & start service
- Health check

Done! API chạy tại `http://your-vps-ip:8000`

---

## Cách 2: Manual (Nếu đã có Docker)

```bash
# SSH vào VPS
ssh user@your-vps-ip

# Clone repo
git clone https://github.com/nguyenxtan/pdf_api.git
cd pdf_api

# Start service
docker compose up -d

# Check status
curl http://localhost:8000/health
```

Done!

---

## Test API ngay

```bash
# Health check
curl http://your-vps-ip:8000/health

# Test convert (cần file PDF)
curl -X POST "http://your-vps-ip:8000/pdf-to-images?dpi=300" \
  -F "pdf=@test.pdf"
```

---

## Setup Production với Domain + SSL

Xem hướng dẫn đầy đủ tại [DEPLOY.md](DEPLOY.md) để:
- Setup Nginx reverse proxy
- Cài SSL certificate (Let's Encrypt)
- Rate limiting
- Monitoring & maintenance

---

## Các lệnh hữu ích

```bash
# View logs
docker compose logs -f

# Restart service
docker compose restart

# Stop service
docker compose down

# Update to latest version
git pull && docker compose up -d --build

# Check resource usage
docker stats pdf-api
```

---

## Mở port firewall (nếu cần)

```bash
sudo ufw allow 8000/tcp
sudo ufw reload
```

---

## Troubleshooting

**Service không start?**
```bash
docker compose logs pdf-api
```

**Port đã được dùng?**
```bash
sudo netstat -tulpn | grep 8000
```

**Cần đổi port?**
Edit `docker-compose.yml`:
```yaml
ports:
  - "9000:8000"  # đổi 9000 thành port bạn muốn
```

---

Xem full documentation: [DEPLOY.md](DEPLOY.md)
