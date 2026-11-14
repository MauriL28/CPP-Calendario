FROM node:22-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY index.html vite.config.js ./
COPY src ./src
COPY public ./public
RUN npm run build

FROM nginx:1.27-alpine

COPY nginx.conf.template /etc/nginx/nginx.conf.template
COPY --from=build /app/dist /usr/share/nginx/html

COPY <<'EOF' /docker-entrypoint-stef365.sh
#!/bin/sh
set -eu
PORT="${PORT:-10000}"
BACKEND_URL="${BACKEND_URL:-https://stef365-backend.onrender.com}"
BACKEND_URL="${BACKEND_URL%/}"
BACKEND_HOST=$(printf '%s' "$BACKEND_URL" | sed -E 's#^[a-zA-Z][a-zA-Z0-9+.-]*://([^/:]+).*#\1#')
case "$BACKEND_HOST" in
  ""|http:*|https:*|/*|*[!A-Za-z0-9.-]*)
    echo "BACKEND_URL no tiene un host valido: $BACKEND_URL" >&2
    exit 1
    ;;
esac
export PORT BACKEND_URL BACKEND_HOST
envsubst '${PORT} ${BACKEND_URL} ${BACKEND_HOST}' \
  < /etc/nginx/nginx.conf.template \
  > /etc/nginx/conf.d/default.conf
exec nginx -g 'daemon off;'
EOF

RUN chmod +x /docker-entrypoint-stef365.sh

ENV PORT=10000
ENV BACKEND_URL=https://stef365-backend.onrender.com

EXPOSE 10000

ENTRYPOINT ["/docker-entrypoint-stef365.sh"]
