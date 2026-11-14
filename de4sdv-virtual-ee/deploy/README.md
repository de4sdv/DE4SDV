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
podman run -d --name ee-registry -p 127.0.0.1:5000:5000 \
  -v /opt/ee/registry:/var/lib/registry:Z \
  docker.io/library/registry@sha256:46faa9a1ae6813194b53921a370f2f4f8c5e1aae228a89bceafef5847a6a3278

# Podman treats plain HTTP as an error until the registry is declared insecure;
# without this the pull fails with "server gave HTTP response to HTTPS client".
printf '[[registry]]\nlocation = "localhost:5000"\ninsecure = true\n' \
  | sudo tee /etc/containers/registries.conf.d/999-ee-registry.conf
systemctl --user restart podman.socket

podman push --tls-verify=false localhost/de4sdv/zone-ecu:9 localhost:5000/de4sdv/zone-ecu:9
podman push --tls-verify=false localhost/de4sdv/can-gw:4   localhost:5000/de4sdv/can-gw:4
```

A push does not create a local ref, so the digest is read from the registry, not
from `podman inspect`:

```bash
curl -sI -H "Accept: application/vnd.oci.image.manifest.v1+json" \
  http://127.0.0.1:5000/v2/de4sdv/zone-ecu/manifests/9 \
  | tr -d '\r' | awk -F': ' '/Docker-Content-Digest/{print $2}'
# sha256:84f265334c5fec1c92e5aa1c1730cf339b42585e5cd8b792163712f310ee3253
```

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
