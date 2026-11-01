FROM postgres:17-alpine

RUN apk add --no-cache age

COPY backup.sh /usr/local/bin/bs-manager-backup
RUN chmod 0755 /usr/local/bin/bs-manager-backup

ENTRYPOINT ["/usr/local/bin/bs-manager-backup"]
