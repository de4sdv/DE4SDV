#!/bin/sh
# Entrypoint for the DE4SDV pinned Systems Modeling API container.
#
# The pinned pilot hard-codes its DB identity inside
# conf/META-INF/persistence.xml (jdbc:postgresql://localhost:5432/sysml2,
# postgres/mysecretpassword). JPA reads those properties from the unit XML,
# so JVM -D flags do NOT override them and there is no upstream env hook.
#
# Architecture-consistent solution (no second parser, no code change): at
# container start the entrypoint rewrites ONLY the jdbc url/user/password
# attribute values inside the staged persistence.xml from compose-provided
# environment, then execs the launcher. The file lives in the container's
# writable layer; the image itself never contains deployment secrets.
# Fails closed when required environment is missing.
set -eu

: "${DB_HOST:?DB_HOST is required}"
: "${DB_PORT:=5432}"
: "${DB_NAME:?DB_NAME is required}"
: "${DB_USER:?DB_USER is required}"
: "${DB_PASSWORD:?DB_PASSWORD is required}"
: "${PLAY_HTTP_SECRET_KEY:?PLAY_HTTP_SECRET_KEY is required}"

CONF=/opt/sysml2-api/conf/META-INF/persistence.xml

if [ ! -w "$CONF" ] || [ ! -w "$(dirname "$CONF")" ]; then
    echo "persistence.xml is not writable; cannot inject DB identity" >&2
    exit 1
fi

sed -i \
  -e "s|<property name=\"javax.persistence.jdbc.url\" value=\"[^\"]*\"/>|<property name=\"javax.persistence.jdbc.url\" value=\"jdbc:postgresql://${DB_HOST}:${DB_PORT}/${DB_NAME}\"/>|" \
  -e "s|<property name=\"javax.persistence.jdbc.user\" value=\"[^\"]*\"/>|<property name=\"javax.persistence.jdbc.user\" value=\"${DB_USER}\"/>|" \
  -e "s|<property name=\"javax.persistence.jdbc.password\" value=\"[^\"]*\"/>|<property name=\"javax.persistence.jdbc.password\" value=\"${DB_PASSWORD}\"/>|" \
  "$CONF"

# Fail closed if the substitution did not land exactly once each.
grep -q "jdbc:postgresql://${DB_HOST}:${DB_PORT}/${DB_NAME}" "$CONF"
grep -q "value=\"${DB_USER}\"" "$CONF"
grep -q "value=\"${DB_PASSWORD}\"" "$CONF"
! grep -q 'localhost:5432' "$CONF"
! grep -q 'mysecretpassword' "$CONF"

# The sbt-stage launcher passes JAVA_OPTS straight to the `java` binary
# (no -J stripping), so raw JVM flags go here.
export JAVA_OPTS="-Xms512m -Xmx4g"

exec "$@"
