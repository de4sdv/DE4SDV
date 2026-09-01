# DE4SDV custom Caddy image: stock Caddy + the pinned caddy-ratelimit module.
#
# Stock caddy images do not contain the rate_limit directive used by the
# public proxy, so we build a custom binary with xcaddy from the pinned
# builder image and copy it into the matching stock runtime image. Both
# stages are digest-pinned.
#
# Pins:
#   builder  caddy:2.8.4-builder-alpine
#            sha256:4ac56838081008c467ae701ebf425c53db62f91e5fa723151904b9ee75d09346
#   runtime  caddy:2.8.4-alpine
#            sha256:af32e97399febea808609119bb21544d0265c58a02836576e32a2d082c262c17
#   module   github.com/mholt/caddy-ratelimit@b8d8c9a9d99ee352d675cbbe416ec2b489fc8cab
#            (2026-01-16, "Remove WIP notice from readme (close #93)")
#
# Module pin note: the three newest upstream commits (6cc6d952a591, 16aecbbcb8ca,
# 5625512f24f6, all 2026-05/06) declare go >= 1.24 in go.mod, which the pinned
# Caddy 2.8.4 builder (Go 1.23, GOTOOLCHAIN=local) cannot compile. The newest
# Go-1.21-compatible revision is b8d8c9a9d99e; re-evaluate the pin when the
# builder image ships a newer Go.

FROM caddy:2.8.4-builder-alpine@sha256:4ac56838081008c467ae701ebf425c53db62f91e5fa723151904b9ee75d09346 AS builder

ARG CADDY_VERSION=2.8.4
ARG CADDY_RATELIMIT_MODULE=github.com/mholt/caddy-ratelimit@b8d8c9a9d99ee352d675cbbe416ec2b489fc8cab

RUN set -eux; xcaddy build "v${CADDY_VERSION}" \
      --output /usr/bin/caddy \
      --with "${CADDY_RATELIMIT_MODULE}"

FROM caddy:2.8.4-alpine@sha256:af32e97399febea808609119bb21544d0265c58a02836576e32a2d082c262c17

COPY --from=builder /usr/bin/caddy /usr/bin/caddy

# Sanity: the built binary must report the expected version and carry the
# rate_limit module. Fails the build otherwise.
RUN set -eux; \
    caddy version; \
    caddy list-modules | grep -q 'rate_limit'

LABEL org.opencontainers.image.title="DE4SDV public proxy Caddy" \
      org.opencontainers.image.description="Caddy 2.8.4 + caddy-ratelimit @5625512f for the DE4SDV experimental read-only API"
