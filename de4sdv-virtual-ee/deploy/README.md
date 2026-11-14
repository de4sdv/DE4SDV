# Host setup — lock, sign, verify, run

What a host needs before `de4sdv-virtual-ee` may run on it. Every step below was
executed on the testbed; the outputs quoted are from that run.

## 1. A signed package

`vehicle/` is a `vxp/1` package: `vxp.yaml` is the descriptor, `main.yaml` the
experiment, `vehicle.yaml` the composition, `parts.yaml` the software baseline.
`vxp.lock` pins all five files and the published images the manifest names.

```bash
cd vehicle
vxedge pkg lock          # writes vxp.lock (never edit it by hand)
vxedge pkg validate      # ok: is a valid package and its lock matches
vxedge pkg pack --out ../packages
# packed de4sdv-virtual-ee-0.1.0.vxp
# digest sha256:3886296e793bfc13830c3b8ee26f6c5f5056ee3c4066466531da92646179d8da
```

A package digest is the SHA-256 of the packed bytes, so it can be checked with
`sha256sum` and cited in a result: *"this ran from package `sha256:3886…`"*.

## 2. A lab key pair

The private key never enters the repository. On the testbed it lives at
`/opt/ee/keys/lab.key` with mode 0600, unlocked by a passphrase in a 0600 file
beside it.

```bash
mkdir -p keys && cd keys
head -c 24 /dev/urandom | base64 > passphrase && chmod 600 passphrase
COSIGN_PASSWORD="$(cat passphrase)" cosign generate-key-pair --output-key-prefix lab
```

`cosign` v3.1.4, installed from the release binary after checking its SHA-256
against the release's own `cosign_checksums.txt`.

## 3. Sign and verify

```bash
export COSIGN_PASSWORD="$(cat keys/passphrase)"
vxedge pkg sign --key keys/lab.key packages/de4sdv-virtual-ee-0.1.0.vxp
# signed … / bundle de4sdv-virtual-ee-0.1.0.vxp.sigstore.json

vxedge pkg verify --key keys/lab.pub packages/de4sdv-virtual-ee-0.1.0.vxp
# verified … digest sha256:3886…
# signer key:sha256:5a2e2d2b71c9f9ef3119e75b48e18bbf2940b90cbce694cda28e327e965909ae
```

Verification is recorded **beside** the package, under the part cache, keyed by the
package digest (`~/.cache/vxedge/parts/packages/<digest>.verified.json`). A folder
edited after verification has another digest, and therefore no record.

## 3b. Image digests come from a registry

The lock can only pin an image that has a digest, and a locally built image has
none until it is pushed. The testbed runs a registry on the host:

```bash
# TLS + htpasswd, so the refs have the shape a published registry would
mkdir -p /opt/ee/registry-tls && cd /opt/ee/registry-tls
openssl req -x509 -newkey rsa:4096 -nodes -days 365 -keyout domain.key -out domain.crt \
  -subj "/CN=localhost" -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"
head -c 18 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' > registry-pass && chmod 600 registry-pass
podman run --rm --entrypoint htpasswd docker.io/library/httpd:2 \
  -Bbn de4sdv "$(cat registry-pass)" > htpasswd

podman run -d --name ee-registry -p 127.0.0.1:5000:5000 \
  -v /opt/ee/registry:/var/lib/registry:Z -v /opt/ee/registry-tls:/certs:Z \
  -e REGISTRY_HTTP_TLS_CERTIFICATE=/certs/domain.crt \
  -e REGISTRY_HTTP_TLS_KEY=/certs/domain.key \
  -e REGISTRY_AUTH=htpasswd -e REGISTRY_AUTH_HTPASSWD_REALM=de4sdv \
  -e REGISTRY_AUTH_HTPASSWD_PATH=/certs/htpasswd \
  docker.io/library/registry@sha256:46faa9a1ae6813194b53921a370f2f4f8c5e1aae228a89bceafef5847a6a3278

# podman must trust the CA and hold the credentials, or the pull 401s / fails TLS
sudo mkdir -p /etc/containers/certs.d/localhost:5000
sudo cp domain.crt /etc/containers/certs.d/localhost:5000/ca.crt
podman login --tls-verify=true -u de4sdv -p "$(cat registry-pass)" localhost:5000

podman push --tls-verify=true localhost/de4sdv/zone-ecu:10 localhost:5000/de4sdv/zone-ecu:10
podman push --tls-verify=true localhost/de4sdv/can-gw:4   localhost:5000/de4sdv/can-gw:4
```

Measured on the testbed: unauthenticated `GET /v2/` is **401**, authenticated is
**200**. A push does not create a local ref, so the digest is read from the registry
(GET, not HEAD — the header is only on the body response):

```bash
curl -s -D - -o /dev/null -u "de4sdv:$(cat registry-pass)" \
  --cacert domain.crt -H "Accept: application/vnd.oci.image.manifest.v1+json" \
  https://localhost:5000/v2/de4sdv/zone-ecu/manifests/10 \
  | tr -d '\r' | grep -i docker-content-digest
# docker-content-digest: sha256:7d2a051e86ce5e3af8fdf8b4d9241b467c3f5ae1410989de7fb02ee0c0284359
```

The digests did not change when the transport did — they are content, not transport.

`parts.yaml` names the tag **and** the digest, and the lock records five images
instead of three.

**Proof that the digest binds and the tag does not:** the tag `9` was moved to a
different image (`sha256:1a85cad1…`), the experiment re-converged, and the zone
still ran

```text
localhost:5000/de4sdv/zone-ecu@sha256:84f26533…
```

A moved tag did not change what ran. That is the claim, and it is the reason the
baseline names digests.

## 4. The host policy

```bash
sudo install -D -m 0644 keys/lab.pub /etc/vxedge/lab.pub
sudo install -D -m 0644 deploy/trust.yaml.example /etc/vxedge/trust.yaml
# require_signed: true
# signers:
#   - { kind: key, public_key: /etc/vxedge/lab.pub }
```

The daemon reads it at start and logs the decision:

```text
INFO vxedged: trust policy policy=Some("/etc/vxedge/trust.yaml") require_signed=true
```

## 5. Run

```bash
export VXEDGE_ENDPOINT=unix:///run/user/$(id -u)/vxedge.sock
vxedge experiment up --chdir vehicle
```

`experiment up`, not `vehicle up`: a workspace that defines its own
network/slices is an experiment, and `vehicle up` refuses it.

## 6. What the host refuses, and why

Two independent gates, both proven by trying to run a package that should fail:

| Attempt | Refusal |
|---|---|
| a file changed, lock not rewritten | `ERROR_REASON_LOCK_MISMATCH` — "the package does not match its `vxp.lock`: `vehicle.yaml` changed" |
| a file changed **and** re-locked, never signed | `ERROR_REASON_SIGNATURE_INVALID` — "this host requires signed packages, and package `sha256:6e2f…` has not been verified here. Nothing was provisioned." |

Both refused before provisioning: no container was created by either attempt.

## 6b. Update, health gate, rollback

`checks/update_with_rollback.sh <candidate> <fallback> [zone] [signal-id]` applies a
package, gates on the zone actually working, and rolls back if it does not.

**The gate is ours because the orchestrator has none.** A package whose zone dies on
a missing file converges "successfully": `experiment up` reports the vehicle up while
the zone is gone. Measured on the testbed — the rear zone died on a missing DBC,
`up` still returned `succeeded`, and the container was `exited` moments later.

The probe is the zone's own status frame, filtered by CAN id (`candump -n 1
vcan0,281:7FF`). A frame bridged in from another zone is not evidence, and a running
container that publishes nothing is exactly the failure the gate exists for.

```text
[update] candidate: /opt/ee/vehicle-pkg-b
[update] health gate FAILED: no 281 from vx-zone-rl-payload within 12s
[update] rolling back to /opt/ee/vehicle-pkg
[update] rolled back: vx-zone-rl-payload is publishing again
```

Exit codes: `0` accepted, `2` rolled back, `3` unhealthy even after rollback.

The two sides of that run, both signed and verified on the host:

| | package digest | what happened |
|---|---|---|
| A, accepted | `sha256:4f801214…` | zone publishes 30 status frames in 3 s |
| B, rejected | `sha256:fb741dae…` | zone exits, no status frames |

**What this is not.** There are no A/B banks and no automatic rollback: B is a second
signed package, the revert is an orchestrated `experiment up` of A, and the gate is a
script. A production SUMS has the bank switch and the revert in the ECU's own update
manager, and that is the part this testbed does not model.

## 6c. Over the air: publish, fetch, verify, apply

The update in 6b was applied from the host. The same signed artifact can travel
through the vehicle network instead — the OTA service (`vxota`) is a TUF-style store
inside the vehicle, and a zone can fetch from it over its own slice.

```bash
# 1. publish, inside the store the OTA service serves
vxota publish --artifacts-dir ota-store \
  --file de4sdv-virtual-ee-0.2.0.vxp --name de4sdv-virtual-ee-0.2.0.vxp \
  --signing-key .ota-root.key          # a PATH: the argument is a file, not the hex seed
vxota publish --artifacts-dir ota-store \
  --file de4sdv-virtual-ee-0.2.0.vxp.sigstore.json \
  --name de4sdv-virtual-ee-0.2.0.vxp.sigstore.json --signing-key .ota-root.key
```

```bash
# 2-3. fetch and check from inside a zone (python: no curl in the image)
podman exec -i vx-zone-fl-payload python - <<'PY'
import hashlib, json, urllib.request
base = "http://10.100.0.50:9900"
t = json.loads(urllib.request.urlopen(base + "/targets.json", timeout=10).read())["signed"]["targets"]
for name in ("de4sdv-virtual-ee-0.2.0.vxp", "de4sdv-virtual-ee-0.2.0.vxp.sigstore.json"):
    e = t[name]
    d = urllib.request.urlopen(base + "/artifacts/" + e["sha256"], timeout=30).read()
    print(name, len(d), "bytes, digest ok =", hashlib.sha256(d).hexdigest() == e["sha256"])
    open("/tmp/" + name, "wb").write(d)
PY
```

Measured:

```text
de4sdv-virtual-ee-0.2.0.vxp: 11776 bytes, digest ok=True
de4sdv-virtual-ee-0.2.0.vxp.sigstore.json: 387 bytes, digest ok=True
vxedge pkg verify → signer key:sha256:5a2e2d2b… (the host's trusted key)
vxedge pkg unpack → digest sha256:fb741dae… (the published digest)
```

Then the gate from 6b decides: the fetched package fails its health check and the
host returns to the previous baseline.

**What this is still not.** There is no A/B bank and no revert inside an ECU update
manager; the fetch client is a short Python script because `vxota-probe` is not in
the 0.30.0 tarball, and the TUF root/targets signature is present in the metadata but
verified here by digest plus the package signature, not by a TUF client. The pieces a
reviewer would ask about — signed artifact, content address, transfer over the vehicle
network, verification before use, gate, revert — are all present and measured.

## 7. The daemon as a unit

```bash
install -m 0644 deploy/systemd/vxedged.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now vxedged
loginctl enable-linger "$USER"      # survive logout
```

`Restart=on-failure` covers a converge that dies half-way: the next start
reconciles. After a restart the gateway came back at `state=3`, 2 slices, 4/4
endpoints, with the trust policy still loaded.

## What this does not cover

- **The two DE4SDV images are still local tags** (`localhost/de4sdv/zone-ecu:9`,
  `can-gw:4`). The lock pins only published refs; a local ref has no digest to
  record. Digest-pinning and signing our own images needs them pushed to a
  registry first, and that is not part of this runbook.
- **`resources:` is declarative.** The descriptor declares per-device CPU and
  memory limits and `vxedge` validates them, but nothing in 0.30.0 applies them:
  `podman inspect` reports `CpuQuota=0 Memory=0` for every payload and infra
  container, and the `Resources` struct has no consumer outside the model.
