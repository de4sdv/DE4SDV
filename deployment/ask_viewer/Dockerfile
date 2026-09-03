FROM python:3.12.11-slim-bookworm@sha256:519591d6871b7bc437060736b9f7456b8731f1499a57e22e6c285135ae657bf7

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates git \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir PyYAML==6.0.2 \
    && groupadd --gid 10001 de4sdv \
    && useradd --uid 10001 --gid 10001 --no-create-home --home-dir /nonexistent de4sdv \
    && mkdir -p /var/cache/de4sdv-viewer \
    && chown 10001:10001 /var/cache/de4sdv-viewer

COPY --chown=10001:10001 entrypoint.py /opt/de4sdv/entrypoint.py

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /srv/de4sdv/DE4SDV
USER 10001:10001
ENTRYPOINT ["python", "/opt/de4sdv/entrypoint.py"]
