FROM nginx:1.27-alpine

COPY mvp-app/static /usr/share/nginx/html
COPY deploy/frontend-nginx.conf /etc/nginx/conf.d/default.conf
COPY deploy/frontend-entrypoint.sh /docker-entrypoint.d/40-parkflow-config.sh

RUN chmod +x /docker-entrypoint.d/40-parkflow-config.sh

EXPOSE 80
