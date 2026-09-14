# pemily-homelab

Declarative config for **donnager** (Dell OptiPlex 7070, tailnet name `pemily-homelab`).
Plan, decisions and inventory live in the vault note `02-Projects/Donnager.md`.

| Layer | Where | Applied by |
| :--- | :--- | :--- |
| Host (LVM, systemd, Cockpit, network) | `ansible/` | Ansible |
| Home Assistant | `compose/homeassistant/` | Ansible → Docker Compose |
| Family cluster (Immich, Jellyfin) | `clusters/family/` | Flux *(Phase 2)* |
| Personal cluster (seanpe.io, PepeVault Server) | `clusters/personal/` | Flux *(Phase 3)* |

## Running

```sh
cd ansible
ansible-playbook site.yml --tags user --check --diff        # dry run, no root needed
ansible-playbook site.yml --tags user                       # HA compose + user services
ansible-playbook site.yml --tags root --ask-become-pass     # linger, Cockpit, LVM
```

- `user` — runs as `pemily`, no sudo. The service cut-over only happens once linger is on.
- `root` — needs the sudo password. **Read the LVM role before running it.**
- `network` — tagged `never`; runs only with `--tags network`. Changing interfaces over SSH can lock you out.

Secrets never live here. Tunnel credentials stay in `~/.cloudflared/` on the host.
