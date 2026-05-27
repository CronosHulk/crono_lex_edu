FROM node:22-alpine AS build

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY index.html ./
COPY vite.config.js ./
COPY scripts ./scripts
COPY public ./public
COPY src ./src
COPY --from=frontend_shared . /frontend_shared
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
