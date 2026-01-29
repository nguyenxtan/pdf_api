# Hướng dẫn Deploy lên VPS Ubuntu

## Yêu cầu VPS

- Ubuntu 20.04+ (hoặc Debian-based distro)
- Docker & Docker Compose đã cài đặt
- Port 8000 available (hoặc custom port)
- RAM: tối thiểu 512MB (khuyến nghị 1GB+)
- Disk: tùy thuộc số lượng PDF xử lý

## Bước 1: Cài đặt Docker & Docker Compose (nếu chưa có)

```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group (không cần sudo mỗi lần)
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt-get install docker-compose-plugin -y

# Verify installation
docker --version
docker compose version
```

**Lưu ý:** Logout và login lại để group membership có hiệu lực.

## Bước 2: Clone repository

```bash
# SSH vào VPS của bạn
ssh user@your-vps-ip

# Clone repo
git clone https://github.com/nguyenxtan/pdf_api.git
cd pdf_api
```

## Bước 3: Deploy với Docker Compose

```bash
# Build và start service
docker compose up -d

# Xem logs
docker compose logs -f

# Check status
docker compose ps
```

## Bước 4: Verify deployment

```bash
# Health check
curl http://localhost:8000/health

# Test với sample PDF (nếu có)
curl -X POST "http://localhost:8000/pdf-to-images" \
  -F "pdf=@test.pdf"
```

## Quản lý Service

```bash
# Start service
docker compose up -d

# Stop service
docker compose down

# Restart service
docker compose restart

# View logs
docker compose logs -f pdf-api

# View real-time logs (last 100 lines)
docker compose logs --tail=100 -f pdf-api

# Rebuild after code changes
git pull
docker compose up -d --build
```

## Expose API ra Internet

### Option 1: Direct Port Exposure (Simple)

Nếu muốn expose port 8000 trực tiếp:

```bash
# Đảm bảo firewall cho phép port 8000
sudo ufw allow 8000/tcp
sudo ufw reload
```

API accessible tại: `http://your-vps-ip:8000`

### Option 2: Nginx Reverse Proxy (Recommended)

Setup Nginx làm reverse proxy với SSL:

```bash
# Install Nginx
sudo apt-get install nginx -y

# Create Nginx config
sudo nano /etc/nginx/sites-available/pdf-api
```

Paste config sau:

```nginx
server {
    listen 80;
    server_name your-domain.com;  # Thay bằng domain của bạn

    client_max_body_size 100M;  # Tăng limit cho PDF lớn

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts cho PDF lớn
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }
}
```

Enable site:

```bash
# Enable config
sudo ln -s /etc/nginx/sites-available/pdf-api /etc/nginx/sites-enabled/

# Test config
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx

# Allow HTTP traffic
sudo ufw allow 'Nginx Full'
```

### Option 3: Nginx + SSL (Production Ready)

Install Certbot cho Let's Encrypt SSL:

```bash
# Install Certbot
sudo apt-get install certbot python3-certbot-nginx -y

# Get SSL certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal is configured automatically
```

API accessible tại: `https://your-domain.com`

## Custom Port

Nếu muốn đổi port (ví dụ 9000):

1. Edit `docker-compose.yml`:
```yaml
ports:
  - "9000:8000"  # host:container
```

2. Restart:
```bash
docker compose down
docker compose up -d
```

## Monitoring & Maintenance

### Check resource usage

```bash
# Container stats
docker stats pdf-api

# Disk usage
du -sh /var/lib/docker/volumes/pdf_api_pdf-data/

# View volume data
sudo ls -lh /var/lib/docker/volumes/pdf_api_pdf-data/_data/
```

### Cleanup old jobs

Tạo cron job để tự động dọn job cũ:

```bash
# Edit crontab
crontab -e

# Thêm dòng này để dọn mỗi ngày lúc 2am
0 2 * * * docker exec pdf-api find /tmp/pdf2img -type d -mtime +1 -exec rm -rf {} + 2>/dev/null
```

Hoặc dọn manual:

```bash
# Remove jobs older than 24 hours
docker exec pdf-api find /tmp/pdf2img -type d -mtime +1 -exec rm -rf {} +
```

### Update to latest version

```bash
cd pdf_api
git pull
docker compose up -d --build
```

## Troubleshooting

### Container không start

```bash
# Check logs
docker compose logs pdf-api

# Check if port is already in use
sudo netstat -tulpn | grep 8000

# Restart Docker
sudo systemctl restart docker
docker compose up -d
```

### Out of disk space

```bash
# Clean up Docker
docker system prune -a
docker volume prune

# Check disk usage
df -h
```

### High memory usage

```bash
# Add memory limit to docker-compose.yml
services:
  pdf-api:
    # ... other configs
    mem_limit: 1g
    mem_reservation: 512m
```

## Security Best Practices

1. **Firewall:** Chỉ mở port cần thiết
```bash
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
# Không expose 8000 nếu dùng Nginx proxy
```

2. **Rate limiting:** Thêm vào Nginx config
```nginx
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;

location / {
    limit_req zone=api_limit burst=20 nodelay;
    # ... rest of config
}
```

3. **Regular updates:**
```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Update app
cd pdf_api && git pull && docker compose up -d --build
```

4. **Backup volume data (optional):**
```bash
# Backup
docker run --rm -v pdf_api_pdf-data:/data -v $(pwd):/backup ubuntu tar czf /backup/pdf-data-backup.tar.gz /data

# Restore
docker run --rm -v pdf_api_pdf-data:/data -v $(pwd):/backup ubuntu tar xzf /backup/pdf-data-backup.tar.gz -C /
```

## Monitoring với script đơn giản

Tạo file `monitor.sh`:

```bash
#!/bin/bash

echo "=== PDF API Health Check ==="
curl -s http://localhost:8000/health | jq .

echo -e "\n=== Container Status ==="
docker compose ps

echo -e "\n=== Resource Usage ==="
docker stats --no-stream pdf-api

echo -e "\n=== Disk Usage ==="
du -sh /var/lib/docker/volumes/pdf_api_pdf-data/

echo -e "\n=== Active Jobs ==="
sudo ls -1 /var/lib/docker/volumes/pdf_api_pdf-data/_data/ | wc -l
```

Chạy:
```bash
chmod +x monitor.sh
./monitor.sh
```

## Support

Nếu gặp vấn đề, check logs đầu tiên:
```bash
docker compose logs --tail=100 pdf-api
```
