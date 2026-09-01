# DE4SDV pinned public Systems Modeling API service image.
#
# The pinned upstream is the exact pilot implementation revision used by the
# privileged DE4SDV full-model ingestion workflow (ADR 0011). The image builds
# the staged Play application in a JDK builder stage and applies documented,
# minimal deployment config patches so the service is restart-safe:
#
#   1. hbm2ddl.auto: create-drop -> update
#      The upstream pilot default DESTROYS all model data on every JVM
#      shutdown. A public deployment must survive restarts. `update` creates
#      the schema once on first boot and never drops committed data. The only
#      writer to the database is the DE4SDV validated importer, which runs
#      server-side; public users are read-only through the proxy.
#   2. hibernate.show_sql / format_sql: false
#      Production must not log every SQL statement for a 56k-element model.
#
# Database identity (host, user, password) is injected at container start by
# the entrypoint from compose-provided environment; nothing is baked in.
# No parser, schema, or API behavior is changed. The public read-only
# boundary is enforced by the reverse proxy (see deployment/caddy), not here.

# ---- builder: JDK + sbt stage, exactly like the privileged workflow ----
FROM eclipse-temurin:11-jdk-jammy@sha256:57bc74eb2a5ad92fe165abcc760a0f6cd1007c1a75aa004d16aa26d59eec0fac AS builder

ARG API_SERVICES_COMMIT=0af711b14bbcea7b240bb0a3a65817ae68302092
ARG API_SERVICES_REPO_URL=https://github.com/Systems-Modeling/SysML-v2-API-Services.git
ARG SBT_LAUNCH_SHA256=7e92e341d1a12ae225a2fa66fac0977b7fd107305653866adeb6c8a8b2f320fb

RUN set -eux; \
    apt-get update && apt-get install -y --no-install-recommends git curl && \
    rm -rf /var/lib/apt/lists/*

ADD https://repo1.maven.org/maven2/org/scala-sbt/sbt-launch/1.2.8/sbt-launch-1.2.8.jar /tmp/sbt-launch.jar
RUN echo "${SBT_LAUNCH_SHA256}  /tmp/sbt-launch.jar" | sha256sum -c -

RUN set -eux; \
    git clone --filter=blob:none "${API_SERVICES_REPO_URL}" /build/sysmlv2-api-services; \
    git -C /build/sysmlv2-api-services checkout "${API_SERVICES_COMMIT}"; \
    curl -fsSL -o /build/sbt-launch.jar \
      https://repo1.maven.org/maven2/org/scala-sbt/sbt-launch/1.2.8/sbt-launch-1.2.8.jar; \
    echo "${SBT_LAUNCH_SHA256}  /build/sbt-launch.jar" | sha256sum -c -

# Restart-safety config patch, applied before staging. Fail closed if the
# upstream content does not look like the expected file.
RUN set -eux; \
    CONF=/build/sysmlv2-api-services/conf/META-INF/persistence.xml; \
    grep -q 'hibernate.hbm2ddl.auto" value="create-drop"' "$CONF"; \
    grep -q 'hibernate.show_sql" value="true"' "$CONF"; \
    sed -i \
      -e 's/hibernate.hbm2ddl.auto" value="create-drop"/hibernate.hbm2ddl.auto" value="update"/' \
      -e 's/hibernate.show_sql" value="true"/hibernate.show_sql" value="false"/' \
      -e 's/hibernate.format_sql" value="true"/hibernate.format_sql" value="false"/' \
      "$CONF"; \
    ! grep -q 'create-drop' "$CONF"; \
    ! grep -q 'show_sql" value="true"' "$CONF"

RUN set -eux; cd /build/sysmlv2-api-services && java -Xmx4g -jar /tmp/sbt-launch.jar stage

# ---- runtime: JRE only ----
FROM eclipse-temurin:11-jre-jammy@sha256:372c96aef3c1c32281ecffbf9aa10de22ef9d8335c60033c2498a2ed4edcdb6f

ARG API_SERVICES_COMMIT=0af711b14bbcea7b240bb0a3a65817ae68302092
ARG API_SERVICES_REPO_URL=https://github.com/Systems-Modeling/SysML-v2-API-Services.git

LABEL org.opencontainers.image.title="DE4SDV pinned Systems Modeling API service" \
      org.opencontainers.image.description="Pinned SysML-v2-API-Services revision for the DE4SDV experimental read-only public API" \
      org.opencontainers.image.source="${API_SERVICES_REPO_URL}" \
      org.opencontainers.image.revision="${API_SERVICES_COMMIT}" \
      org.opencontainers.image.vendor="DE4SDV"

RUN set -eux; \
    useradd --system --home /opt/sysml2-api --shell /usr/sbin/nologin sysml2

COPY --from=builder --chown=sysml2:sysml2 /build/sysmlv2-api-services/target/universal/stage /opt/sysml2-api

COPY --chown=sysml2:sysml2 deployment/sysml2-api/conf/application-production.conf /opt/sysml2-api/conf/application-production.conf
COPY --chown=sysml2:sysml2 deployment/sysml2-api/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

USER sysml2
WORKDIR /opt/sysml2-api
EXPOSE 9000

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["/opt/sysml2-api/bin/sysml-v2-api-services", \
     "-Dconfig.file=/opt/sysml2-api/conf/application-production.conf", \
     "-Dpidfile.path=/dev/null"]
