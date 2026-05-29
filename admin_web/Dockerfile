# === Этап 1: Сборка статики ===
FROM node:22-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci --prefer-offline --no-audit
COPY . .
# Копируем общую шару, которую CI скопировал внутрь контекста перед сборкой
COPY frontend_shared /frontend_shared
RUN npm run build

# === Этап 2: Раздача через Caddy ===
FROM caddy:2.9-alpine
# Копируем билд в подпапку admin, чтобы пути /admin/... соответствовали файловой системе
COPY --from=build /app/dist/ /usr/share/caddy/admin/

# Создаем Caddyfile для поддержки SPA-роутинга по пути /admin
RUN echo -e ":{\$PORT} {\n    root * /usr/share/caddy\n    file_server\n    try_files {path} /admin/index.html\n}" > /etc/caddy/Caddyfile

EXPOSE 8080
CMD ["caddy", "run", "--config", "/etc/caddy/Caddyfile"]
