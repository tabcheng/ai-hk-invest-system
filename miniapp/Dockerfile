FROM caddy:2.8-alpine

WORKDIR /srv
COPY index.html /srv/index.html
COPY config.js /srv/config.js
COPY Caddyfile /etc/caddy/Caddyfile
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8080
ENTRYPOINT ["/entrypoint.sh"]
