# Nginx Configuration for InvIQ

This directory contains the Nginx reverse proxy configuration for the InvIQ Smart Inventory Assistant.

## Files

- **nginx.conf** - Main Nginx configuration with rate limiting, security headers, and routing
- **Dockerfile** - Nginx container build configuration
- **README.md** - This file

## Quick Start

### Local Development with Docker Compose

```bash
# From project root
docker compose up -d

# Access via Nginx
curl http://localhost/health

# View Nginx logs
docker compose logs -f nginx
```

### Standalone Nginx Container

```bash
# Build Nginx image
cd nginx
docker build -t inviq-nginx:latest .

# Run Nginx container
docker run -d \
  --name inviq-nginx \
  -p 80:80 \
  --network inviq_network \
  inviq-nginx:latest
```

## Configuration Highlights

### Rate Limiting

| Zone | Limit | Endpoints |
|------|-------|-----------|
| `api_limit` | 10 req/s | All `/api/*` |
| `auth_limit` | 5 req/min | `/api/auth/login`, `/api/auth/register` |
| `upload_limit` | 2 req/min | `/api/vendor/upload-delivery` |

### Security Headers

- `X-Frame-Options: SAMEORIGIN`
- `X-Content-Type-Options: nosniff`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: no-referrer-when-downgrade`

### Features

- ✅ Rate limiting (3 zones)
- ✅ Gzip compression
- ✅ WebSocket proxying
- ✅ Connection pooling
- ✅ SSL/TLS support (production)
- ✅ Health check endpoint
- ✅ Request logging

## Testing

### Test Rate Limits

```bash
# Test general API rate limit (10 req/s)
for i in {1..15}; do curl http://localhost/api/inventory/locations; done

# Test auth rate limit (5 req/min)
for i in {1..7}; do 
  curl -X POST http://localhost/api/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username":"test","password":"test"}'; 
done
```

### Test WebSocket

```bash
# Install wscat if needed
npm install -g wscat

# Connect to WebSocket
wscat -c "ws://localhost/ws/alerts/1?token=YOUR_JWT_TOKEN"
```

### Verify Configuration

```bash
# Test Nginx config syntax
docker compose exec nginx nginx -t

# Reload Nginx config (no downtime)
docker compose exec nginx nginx -s reload
```

## Production Setup

### SSL/TLS Configuration

1. Obtain SSL certificates (Let's Encrypt):
```bash
certbot certonly --nginx -d inviq.example.com
```

2. Update `nginx.conf` with SSL configuration (see commented section)

3. Restart Nginx:
```bash
docker compose restart nginx
```

### Environment Variables

No environment variables required for Nginx. All configuration is in `nginx.conf`.

## Monitoring

### View Logs

```bash
# Access logs
docker compose exec nginx tail -f /var/log/nginx/access.log

# Error logs
docker compose exec nginx tail -f /var/log/nginx/error.log

# Both logs
docker compose logs -f nginx
```

### Key Metrics

- Active connections
- Request rate
- 429 (rate limit) responses
- 5xx errors
- Response times

## Troubleshooting

| Issue | Solution |
|-------|----------|
| 502 Bad Gateway | Check backend: `docker compose logs app` |
| 429 Too Many Requests | Rate limit hit, wait or increase limits |
| WebSocket fails | Check upgrade headers in config |
| Config errors | Run `nginx -t` to test syntax |

## Documentation

For complete documentation, see [docs/NGINX.md](../docs/NGINX.md)

## Architecture

```
Client → Nginx (80/443) → FastAPI (8000) → PostgreSQL + Redis
```

Nginx handles:
- Rate limiting
- SSL/TLS termination
- Gzip compression
- Security headers
- WebSocket proxying
- Load balancing

FastAPI handles:
- Business logic
- Authentication
- Database operations
- AI agent
