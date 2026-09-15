# clusters/family

The family cluster: a single k3s server on donnager's host, reconciled by Flux from this path.
Immich and Jellyfin live here (Phase 4). It's the stable one — upgrade rarely, and on purpose.

| File | Reconciles |
| :--- | :--- |
| `flux-system/` | written by `flux bootstrap` — don't edit by hand |
| `infrastructure.yaml` | `infrastructure/family/` |
| `apps.yaml` | `apps/family/`, after infrastructure is ready |

Both decrypt SOPS secrets with the `sops-age` Secret in `flux-system`.

## Bootstrap (once)

Needs on the control machine: `flux` v2.9.5, `age`, `sops`, `kubectl`, `ansible`.

1. **Storage first.** LVM must run before k3s, or local-path PVs land on the 100 GiB root LV.
   Read `ansible/roles/lvm/tasks/main.yml` first.
   ```sh
   cd ansible && ansible-playbook site.yml --tags root --ask-become-pass
   ```
2. **k3s.** The role refuses to run unless `/var/lib/rancher/k3s/storage` is a mountpoint.
   ```sh
   ansible-playbook site.yml --tags k3s --ask-become-pass
   ```
   Writes `~/.kube/family.yaml` (context `family`, server `https://pemily-homelab:6443`). Add it to
   `KUBECONFIG` — fish: `set -Ux KUBECONFIG $HOME/.kube/config:$HOME/.kube/family.yaml`.
3. **Age key for this cluster** (one key per cluster). **Back it up off this machine** — it is the
   only thing that can decrypt this cluster's secrets.
   ```sh
   mkdir -p ~/.config/sops/age
   age-keygen -o ~/.config/sops/age/family.agekey
   cat ~/.config/sops/age/family.agekey >> ~/.config/sops/age/keys.txt   # where sops looks
   ```
   Put the public key (`age-keygen -y ~/.config/sops/age/family.agekey`) in `.sops.yaml`.
4. **Hand the key to the cluster.**
   ```sh
   kubectl --context family create namespace flux-system
   kubectl --context family -n flux-system create secret generic sops-age \
     --from-file=age.agekey=$HOME/.config/sops/age/family.agekey
   ```
5. **Bootstrap Flux** over SSH with a deploy key (no GitHub token needed).
   ```sh
   flux bootstrap git --context family \
     --url=ssh://git@github.com/seanpe11/pemily-homelab.git \
     --branch=main --path=clusters/family
   ```
   It prints a public key and waits: add it under GitHub → repo → Settings → Deploy keys with
   **Allow write access**, then answer `y`. Flux commits `flux-system/` back to `main` — `git pull` after.
6. **Check.**
   ```sh
   flux --context family check
   flux --context family get kustomizations   # flux-system, infrastructure, apps → Ready
   ```
