#!/bin/sh
# Entrypoint for the DE4SDV pinned Systems Modeling API container.
#
# Translates compose-provided DB identity into JVM system properties at
# start; nothing is baked into the image. Fails closed when required
# environment is missing so a misconfigured container never boots with a
# silent default password.
set -eu

: "${DB_HOST:?DB_HOST is required}"
: "${DB_PORT:=5432}"
: "${DB_NAME:?DB_NAME is required}"
: "${DB_USER:?DB_USER is required}"
: "${DB_PASSWORD:?DB_PASSWORD is required}"
: "${PLAY_HTTP_SECRET_KEY:?PLAY_HTTP_SECRET_KEY is required}"

export JAVA_OPTS="-J-Xms512m -J-Xmx4g \
-Djavax.persistence.jdbc.url=jdbc:postgresql://${DB_HOST}:${DB_PORT}/${DB_NAME} \
-Djavax.persistence.jdbc.user=${DB_USER} \
-Djavax.persistence.jdbc.password=${DB_PASSWORD}"

exec "$@"
