# pemily-homelab

Declarative config for **donnager** (Dell OptiPlex 7070) — the host layer, and the family
Kubernetes cluster named `pemily-homelab`. The personal cluster lives in a separate repo,
`seanpe-homelab`, and runs in an Incus VM on this box.

Copy `ansible/group_vars/homelab.yml.example` to `homelab.yml` and fill in your own addresses.

| Layer | Where | Applied by |
| :--- | :--- | :--- |
| Host (LVM, systemd, Cockpit, network) | `ansible/` | Ansible |
| Home Assistant | `compose/homeassistant/` | Ansible → Docker Compose |
| Family cluster (Immich, Jellyfin) | `clusters/family/` | Flux *(Phase 2)* |
| Personal cluster (seanpe.io, Supabase) | separate repo `seanpe-homelab`, in an Incus VM | Flux |

## Running

```sh
cd ansible
ansible-playbook site.yml --tags user --check --diff        # dry run, no root needed
ansible-playbook site.yml --tags user                       # HA compose + user services
ansible-playbook site.yml --tags root --ask-become-pass     # linger, Cockpit, LVM
ansible-playbook site.yml --tags root,incus --ask-become-pass   # + Incus and the seanpe-homelab VM
ansible-playbook site.yml --tags seanpe-homelab               # k3s inside that VM (no sudo prompt)
ansible-playbook site.yml --tags k3s --ask-become-pass      # pemily-homelab family cluster k3s (after LVM; not built yet)
```

- `user` — runs as `pemily`, no sudo. The service cut-over only happens once linger is on.
- `root` — needs the sudo password. **Read the LVM role before running it.**
- `network` — tagged `never`; runs only with `--tags network`. Changing interfaces over SSH can lock you out.

Secrets never live here. Tunnel credentials stay in `~/.cloudflared/` on the host.
