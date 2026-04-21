# ═══════════════════════════════════════════════════════════════════════════
# Nginx Dockerfile for InvIQ Smart Inventory Assistant
# ═══════════════════════════════════════════════════════════════════════════
# Purpose: Lightweight Nginx reverse proxy container
# Base: Official Nginx Alpine image (minimal size)
# ═══════════════════════════════════════════════════════════════════════════

FROM nginx:1.25-alpine

# Install curl for health checks
RUN apk add --no-cache curl

# Remove default Nginx configuration
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom Nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Create log directory
RUN mkdir -p /var/log/nginx && \
    chown -R nginx:nginx /var/log/nginx

# Expose HTTP port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost/health || exit 1

# Start Nginx in foreground
CMD ["nginx", "-g", "daemon off;"]
