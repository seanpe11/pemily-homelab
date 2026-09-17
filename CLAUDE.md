# pemily-homelab — context for Claude

**This repo is the household half of donnager**: the host layer (Ansible) plus the **family**
Kubernetes cluster. Sean's personal services are a *different* repo — don't build them here.

| Name | Is | Repo |
| :--- | :--- | :--- |
| **donnager** | the machine (Dell OptiPlex 7070, Ubuntu 26.04) | host layer lives here |
| **pemily-homelab** | the **family** cluster: k3s on donnager's host | **this repo** |
| **seanpe-homelab** | Sean's **personal** cluster, k3s inside an Incus VM on donnager | `~/Documents/explore/seanpe-homelab` (public) |

Full history and reasoning: the vault note `02-Projects/Donnager.md` and
`03-Library/Homelab Revival Report 2026-09-15.md` in `~/Documents/PepeVault`.

## Reaching the machine

```sh
ssh pemily@donnager          # tailnet MagicDNS name; the IP lives in the gitignored group_vars
cd ansible && ansible-playbook site.yml --tags <tag> --ask-become-pass
```

Ansible connects by tailnet **IP** (not name) so a rename can't strand a run. `--tags user`
needs no sudo; `root`, `incus`, `k3s` do. The VM play (`--tags seanpe-homelab`, `tailscale`)
needs no password because cloud-init gave that VM passwordless sudo.

## What is already applied

- Hostname, `/etc/hosts` and the Tailscale node name are all **donnager** (was `pemily-homelab` —
  that name now means the cluster, not the box).
- LVs carved and mounted: `k3s-family` 100G → `/var/lib/rancher/k3s/storage`,
  `immich-library` 350G → `/srv/immich/library`, `immich-backups` 250G → `/srv/backups/immich`,
  `incus` 100G raw → Incus btrfs pool. **~28 GiB unallocated.**
- Cockpit bound to the tailnet IP only, `:9090`.
- Home Assistant in Docker Compose (`compose/homeassistant/`), plus the `pemily-home` cloudflared
  tunnel and the printer forwarder as systemd **user** units with linger.
- Incus 6.0.5, bridge `incusbr0` 10.77.0.1/24, VM `seanpe-homelab-1` (4 vCPU / 8 GiB, autostart,
  on the tailnet) running the personal cluster.

## What is NOT built yet — the actual work

1. **k3s on the host** = the family cluster. The role is written and parameterised:
   `ansible-playbook site.yml --tags k3s --ask-become-pass`. It refuses to run unless
   `/var/lib/rancher/k3s/storage` is a mountpoint, so local-path PVs can't land on the 100 GiB root.
   Writes `~/.kube/pemily-homelab.yaml` on rocinante.
2. **Flux** for `clusters/family/`. Manifests are written and validated but **not yet applied** —
   `flux-system/` (components + anonymous-HTTPS GitRepository), and `infrastructure/family/` now
   carries the `immich` namespace, a `donnager-local` StorageClass and the two Immich PVs.
   `apps/family/` is still an empty kustomization. Needs the repo pushed to GitHub first.
3. **Immich** — the point of the 350G + 250G LVs.
4. **Jellyfin** — a draft is parked at `apps/family/jellyfin/`, unreferenced. See the blocker below.

## Traps that already cost time — don't rediscover these

- **`ansible_become_exe: sudo.ws`.** Ubuntu 26.04 ships **sudo-rs**, which rewraps the prompt
  Ansible waits for; without this every become task dies with
  `Timeout (12s) waiting for privilege escalation prompt`.
- **`--check` can't install.** The `command` module has no check mode, so a dry run on a host
  without k3s skips the install; the k3s role detects that and skips the dependent tasks with an
  explanation instead of failing.
- **Docker breaks bridged VM networking.** Docker's iptables backend sets `FORWARD` to `DROP`, which
  silently cuts `incusbr0` off from the internet. `incus-docker-forward.service` re-adds the
  `DOCKER-USER` accepts whenever Docker restarts. Don't remove it.
- **`group_vars/all.yml` and `group_vars/homelab.yml` are gitignored** — they hold this machine's
  tailnet address, tunnel UUID and LAN layout. Copy from the `.example` files. History was rewritten
  to remove those values, so don't reintroduce them into tracked files.
- **LVM grows, never shrinks.** `lvextend -r -L +NG` is safe; shrinking ext4 is not.

## One decision the next session has to make

### ~~Flux auth~~ — decided 2026-09-17: **this repo is public, Flux reads it anonymously**

The `seanpe-homelab` shortcut transfers after all, because the premise changed: this repo is
**public**, not private. `clusters/family/flux-system/` holds committed `flux install --export`
output and a GitRepository pointing at **HTTPS with no credential** — no deploy key, no PAT,
nothing to rotate, and nothing Flux holds that can write back to the repo.

Bootstrap is therefore `kubectl apply -k clusters/family/flux-system`, **not** `flux bootstrap`.
The runbook in `clusters/family/README.md` is now verified — follow it in order; step 4 (the
`sops-age` Secret) has to happen before step 5 or both Kustomizations fail on a missing secretRef.

**The coupling to remember:** making this repo private later breaks `gotk-sync.yaml`. That is the
price of the no-credential path, and it is paid only if the visibility changes.

### Jellyfin has nowhere to put media
The disk is fully committed: 100 root + 100 k3s-family + 350 immich-library + 250 immich-backups
+ 100 incus = **900 of 928.5 GiB**. There is no media LV. Options, none free:
- add a second drive (the chassis' free M.2/SATA capacity is **unverified** — check physically),
- take space from `immich-backups` before Immich fills it,
- keep media off this box entirely.

Transcoding hardware is present and unused: `/dev/dri/renderD128`, Intel UHD 630 (Quick Sync), and a
`DVD+-RW DU-8A5LH` optical drive for ripping discs. The parked draft pins to **pegasus** and asks for
an **NVIDIA** GPU — both wrong for donnager. Rework it for `/dev/dri` passthrough.

## Secrets

SOPS is set up (2026-09-17). `.sops.yaml` at the repo root encrypts `*.sops.yaml` under
`clusters|infrastructure|apps/family/` to the **family** age key — public half in that file,
private half at `~/.config/sops/age/family.agekey` on rocinante, **not yet backed up off it**.
One age key per cluster: the personal cluster keeps its own at `~/Documents/explore/age.key`.
A Secret in a file *not* named `*.sops.yaml` is committed in plaintext with no warning, and this
repo is public — check `git diff` before pushing one.
Never commit a plaintext Secret, a kubeconfig, or `~/.cloudflared/*.json`.

## Patterns worth copying from seanpe-homelab

That repo is a working reference for: the Flux layout (`clusters/<name>/` + `infrastructure/` +
`apps/`), an in-cluster cloudflared using a **credentials file** (a token makes the tunnel
dashboard-managed and silently ignores your ingress rules), SOPS-encrypted Secrets, and
`ops/rocinante/` systemd user units for a kubectl tunnel and nightly `pg_dump`.

**If you expose anything from this cluster**, remember the rule that repo learned the hard way:
Supabase's MCP endpoint is superuser SQL with no auth, so it lives on the tailnet only, never on a
public hostname.
