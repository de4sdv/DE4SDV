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
