# Build the Vite SPA, serve it from nginx and proxy /api to the api container.
FROM node:20-alpine AS build
WORKDIR /app
COPY apps/web/package.json apps/web/package-lock.json ./
RUN npm ci
COPY apps/web ./
RUN npm run build

FROM nginx:1.27-alpine
COPY apps/web/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80

# 127.0.0.1 on purpose: "localhost" resolves to ::1 here and nginx listens
# IPv4-only, which flapped the container healthcheck.
HEALTHCHECK CMD wget -q -O /dev/null http://127.0.0.1/ || exit 1