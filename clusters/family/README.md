# clusters/family

The family cluster: a single k3s server on donnager's host, reconciled by Flux from this path.
Immich lives here (Phase 4); Jellyfin is blocked on storage. It's the stable one — upgrade
rarely, and on purpose.

| File | Reconciles |
| :--- | :--- |
| `flux-system/` | Flux's own components + the GitRepository. Flux re-applies these itself |
| `infrastructure.yaml` | `infrastructure/family/` — namespaces, StorageClass, the Immich PVs |
| `apps.yaml` | `apps/family/`, after infrastructure is ready |

Both decrypt SOPS secrets with the `sops-age` Secret in `flux-system`, so **that Secret has to
exist before Flux is applied** — a `decryption.secretRef` pointing at a missing Secret fails the
reconcile rather than being ignored. Step 4 below, not an afterthought.

## Flux auth — decided 2026-09-17

**This repo is public, and Flux reads it over anonymous HTTPS with no credential at all** — the
same arrangement as `seanpe-homelab`. There is no deploy key and no PAT to rotate, and nothing
Flux holds can write back to the repo.

The earlier draft of this file described `flux bootstrap git` with a **write-access** deploy key,
on the assumption that this repo would be private. That assumption was dropped. Note the coupling:
if this repo is ever made private, `flux-system/gotk-sync.yaml` stops working and Flux needs a
deploy key or a PAT. That is the trade.

What makes this safe to publish is SOPS, not obscurity: every Secret is encrypted to the family
age key before it is committed, and `.sops.yaml` at the repo root enforces which paths that
applies to. **Never commit a plaintext Secret here.** The history was audited before the first
push (2026-09-17) and contains no tailnet address, tunnel UUID, LAN address, private key or token.

## Bootstrap (once)

Needs on the control machine: `flux` v2.9.5, `age`, `sops`, `kubectl`, `ansible`.

1. **Storage first.** LVM must run before k3s, or local-path PVs land on the 100 GiB root LV.
   ```sh
   cd ansible && ansible-playbook site.yml --tags root --ask-become-pass
   ```

2. **k3s.** The role refuses to run unless `/var/lib/rancher/k3s/storage` is a mountpoint.
   ```sh
   ansible-playbook site.yml --tags k3s --ask-become-pass
   ```
   Writes `~/.kube/pemily-homelab.yaml` — context **`pemily-homelab`**, server
   `https://<tailnet-ip>:6443`. Add it to `KUBECONFIG`; fish:
   ```sh
   set -Ux KUBECONFIG $HOME/.kube/config:$HOME/.kube/seanpe-homelab.yaml:$HOME/.kube/pemily-homelab.yaml
   ```
   donnager's become goes through `sudo.ws` — see the sudo-rs trap in `CLAUDE.md`.

3. **The repo must exist on GitHub first.** Flux reads from it, so pushing is a prerequisite of
   bootstrapping, not a follow-up.
   ```sh
   git remote add origin git@github.com:seanpe11/pemily-homelab.git
   git push -u origin main
   ```

4. **Age key → cluster.** One key per cluster. The private half is at
   `~/.config/sops/age/family.agekey` on rocinante; its public half is already in `.sops.yaml`.
   **Back it up off this machine** — it is the only thing that can decrypt this cluster's secrets.
   ```sh
   kubectl --context pemily-homelab create namespace flux-system
   kubectl --context pemily-homelab -n flux-system create secret generic sops-age \
     --from-file=age.agekey=$HOME/.config/sops/age/family.agekey
   ```
   The key inside the Secret must end in `.agekey` or kustomize-controller won't find it.

5. **Apply Flux.** No `flux bootstrap` — the manifests are committed, so this is an apply.
   ```sh
   kubectl --context pemily-homelab apply -k clusters/family/flux-system
   ```

6. **Check.**
   ```sh
   flux --context pemily-homelab check
   flux --context pemily-homelab get kustomizations   # flux-system, infrastructure, apps → Ready
   kubectl --context pemily-homelab get pv            # immich-library, immich-backups → Available
   ```

## Adding a Secret

```sh
# write the plaintext Secret as <name>.sops.yaml, then, from the repo root:
sops --encrypt --in-place apps/family/<app>/secret.sops.yaml
```
`.sops.yaml` matches on the `*.sops.yaml` suffix under `clusters|infrastructure|apps/family/`, so
a file named anything else is committed in plaintext with no warning. Check `git diff` before the
first push of any Secret.
