# Testing FIREMaster on a Windows VM in Azure (Dv5)

A repeatable, throwaway **Windows + Docker** environment for the Windows acceptance test —
the one this project can't run on an Apple Silicon (M1/M2) Mac VM, because that hardware
can't do **nested virtualization** and Docker Desktop/WSL2 require it.

**Why Dv5 specifically:** the Azure **Dv5 / Dsv5** sizes expose nested virtualization, so
Windows' WSL2/Hyper-V (and therefore Docker Desktop) run normally. Pick a non-nested size
and you'll hit the exact "virtualization support not detected" error again.

**Bonus:** Azure Windows VMs are **amd64** — the architecture most real Windows users run,
and the one your arm64 Mac/VM never exercises (see Part 4 of `../CONTAINERIZATION.md`).

> **Cost:** a `Standard_D4s_v5` runs roughly **$0.20–0.30/hour** (compute + Windows
> license). A test session is a few dollars. **Deallocate or delete when done** (Part F) or
> it bills around the clock.

---

## Prerequisites

- An Azure subscription (a pay-as-you-go or free-trial one is fine).
- One of:
  - the **Azure Portal** (browser) — the click-path in Part A1, or
  - the **Azure CLI** (`az`) — the scripted path in Part A2 (recommended for "repeatable").
- An RDP client (Windows has one built in; on macOS use **Windows App**, formerly Microsoft
  Remote Desktop, from the Mac App Store).

> **Windows 11 image eligibility:** Azure's Windows 11 *client* images require an eligible
> subscription (e.g. Visual Studio subscription, or Enterprise/dev-test). If `az` rejects
> the Windows 11 image, use **Windows Server 2022** instead (note in Part A2) — it runs the
> same Docker, it's just slightly less "real user."

---

## Part A1 — Create the VM (Azure Portal click-path)

1. Portal → **Create a resource** → **Virtual machine**.
2. **Basics:**
   - **Resource group:** *Create new* → `firemaster-test-rg`.
   - **VM name:** `fm-win-test`.
   - **Region:** one near you.
   - **Image:** **Windows 11 Pro** (click "See all images" if it's not in the dropdown).
     Fallback: **Windows Server 2022 Datacenter: Azure Edition**.
   - **Size:** click "See all sizes", search **D4s_v5** → `Standard_D4s_v5`
     (4 vCPU / 16 GiB). *Make sure it's a `v5` — that's the nested-virt-capable family.*
   - **Administrator account:** set a username (e.g. `azureuser`) and a strong password.
   - **Inbound ports:** allow **RDP (3389)**.
   - Check the licensing/eligibility confirmation box if shown.
3. **Review + create** → **Create**. Wait ~2–3 minutes for deployment.
4. Open the VM resource → copy its **Public IP address**.

Skip to **Part B**.

---

## Part A2 — Create the VM (Azure CLI — repeatable)

Run in PowerShell or bash with `az` installed and `az login` done. (Backtick line
continuations are PowerShell; for bash, join the lines or swap `` ` `` for `\`.)

```powershell
# --- variables ---
$RG  = "firemaster-test-rg"
$LOC = "eastus"               # pick a region near you
$VM  = "fm-win-test"
$USER= "azureuser"
$PASS= "<ChooseAStrongP@ssw0rd!>"   # 12+ chars, upper/lower/digit/symbol

# --- resource group ---
az group create -n $RG -l $LOC

# --- find the current Windows 11 Pro SKU (optional; SKUs change) ---
az vm image list --publisher MicrosoftWindowsDesktop --offer windows-11 --all -o table

# --- create the VM (Windows 11 Pro, nested-virt-capable D4s_v5) ---
az vm create `
  -g $RG -n $VM `
  --image "MicrosoftWindowsDesktop:windows-11:win11-24h2-pro:latest" `
  --size Standard_D4s_v5 `
  --admin-username $USER `
  --admin-password $PASS `
  --public-ip-sku Standard `
  --nic-delete-option Delete --os-disk-delete-option Delete

# --- ensure RDP is open ---
az vm open-port -g $RG -n $VM --port 3389

# --- print the public IP to RDP into ---
az vm show -d -g $RG -n $VM --query publicIps -o tsv
```

> **If the Windows 11 image is rejected** (eligibility), swap the `--image` line for
> Windows Server 2022:
> ```
> --image "MicrosoftWindowsServer:WindowsServer:2022-datacenter-azure-edition:latest"
> ```
> On Server 2022, Docker Desktop isn't officially supported; if it refuses to start, install
> **Docker CE with the WSL2 backend** instead — but Windows 11 Pro avoids this entirely.

> Nested virtualization needs **no extra toggle** — choosing a `Ds_v5`/`Dv5` size is what
> enables it. Inside Windows, Docker Desktop's installer turns on WSL2/Hyper-V itself.

---

## Part B — Connect via RDP

1. Open your RDP client → connect to the **public IP** from Part A.
2. Sign in with the admin username/password you set.
3. Accept the certificate prompt. You're now on the Windows desktop.

---

## Part C — Install Docker Desktop + Git (inside the VM)

Windows 11 includes **winget**. Open **PowerShell** (Start → type PowerShell) and run:

```powershell
winget install --id Git.Git -e --accept-package-agreements --accept-source-agreements
winget install --id Docker.DockerDesktop -e --accept-package-agreements --accept-source-agreements
```

Then:

1. **Reboot** (Docker Desktop's WSL2 setup needs it): `Restart-Computer`. Reconnect via RDP
   after ~1 minute.
2. Launch **Docker Desktop** from the Start menu. Accept the service agreement.
3. If it offers **"Use WSL 2 based engine"**, accept (default). Let it finish — wait until
   the whale icon in the tray is steady and the dashboard says **"Engine running."**
4. Sanity check in PowerShell:
   ```powershell
   docker version
   docker run --rm hello-world
   ```
   `hello-world` printing a success message proves nested virt + Docker are working — the
   exact thing that fails on the M1/M2 Mac VM.

> **Note:** a fresh PowerShell window may not have `git`/`docker` on PATH immediately after
> install. Open a **new** terminal, or refresh PATH:
> ```powershell
> $env:Path = [Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [Environment]::GetEnvironmentVariable("Path","User")
> ```

---

## Part D — Clone the repo and run the stack

The repo is **private**, so authenticate first. Easiest is the GitHub CLI:

```powershell
winget install --id GitHub.cli -e --accept-package-agreements --accept-source-agreements
# open a new terminal, then:
gh auth login        # GitHub.com → HTTPS → login with a web browser
gh repo clone gdb-mtx/fire-master
cd fire-master
```

Then run the **one-time setup** (generates the JWT secret + your admin password into
`backend/.env`), and bring up the whole stack:

```powershell
docker compose run --rm backend uv run python -m app.setup   # prompts for an admin password
docker compose up                                            # builds, migrates, auto-seeds the demo, then runs everything
```

First run downloads base images and builds — give it a few minutes. Migrations **and** the
demo persona load automatically: a one-shot `migrate` container does that and then exits, so
seeing it as `Exited (0)` in `docker compose ps` is **normal**.

> **Fully unattended (no prompt):** set the password inline instead of being prompted —
> ```powershell
> $env:FIREMASTER_ADMIN_PASSWORD="<StrongPass>"
> docker compose run --rm -e FIREMASTER_ADMIN_PASSWORD backend uv run python -m app.setup
> ```
> Handy if you want the whole Azure test to run hands-off. (Use `uv run python …`, not bare
> `python` — the latter misses the uv venv.)

---

## Part E — Verify (the real acceptance test)

Inside the VM:

1. **Log in:** open **http://localhost:5173** and sign in as **`admin`** with the password
   you set during setup. The **demo persona is already loaded** (auto-seeded on first boot),
   so Dashboard, Retirement, Runway, and Settings → Plan are all alive immediately — **with
   no Node installed on the host**.
2. **API:** open **http://localhost:8000/docs** — the OpenAPI explorer confirms the backend
   is reachable on its published port.
3. **Backend ↔ DB:** in the `docker compose up` logs, the backend should connect to Postgres
   cleanly (the old `localhost`-vs-`postgres` bug is fixed). A `Connection refused` here now
   indicates a real problem, not the known issue — see the runbook.
4. **Copilot (optional):** install Claude Code in the VM, point it at `http://localhost:8000`,
   and confirm it can authenticate and pull a projection — proving the dual-interface works
   over the published port on Windows too.
5. **Scenarios (optional):** the demo seeds automatically, but example what-if scenarios
   don't — add them with
   `docker compose exec backend uv run python ../scripts/seed_scenarios.py`.

What this run uniquely validates that the Mac can't: the **Docker Desktop install/reboot
flow**, **amd64** images, **path/line-ending** quirks, and that **no bash/uv/node** is ever
needed.

---

## Part F — Stop the meter (do this every time)

```powershell
# Stop compute billing but keep the VM (fast to restart):
az vm deallocate -g firemaster-test-rg -n fm-win-test

# Restart it later:
az vm start -g firemaster-test-rg -n fm-win-test

# Or delete EVERYTHING when fully done (no further charges):
az group delete -n firemaster-test-rg --yes --no-wait
```

> **Deallocate ≠ delete.** Deallocated stops compute charges; the OS disk still costs a few
> cents/day. Delete the resource group to zero it out.

---

## Troubleshooting

- **"virtualization support not detected" again** → you picked a non-nested VM size. Confirm
  it's a **`v5`** (`Standard_D4s_v5`). Resize: `az vm resize -g <rg> -n <vm> --size Standard_D4s_v5`.
- **Docker Desktop hangs on "starting"** → ensure WSL2 is set: run `wsl --status` and
  `wsl --update`, then restart Docker Desktop. Reboot once more if needed.
- **Login fails with a startup error about `JWT_SECRET_KEY` / `AUTH_PASSWORD_HASH`** → you
  skipped the one-time setup: `docker compose run --rm backend uv run python -m app.setup`.
- **`migrate` container shows `Exited (0)`** → normal; it applied migrations + seeded the
  demo, then quit.
- **Port already in use** (`:5432`/`:6379`/`:8000`/`:5173`) → remap with the host-port env
  vars, e.g. `$env:BACKEND_HOST_PORT="8001"; $env:FRONTEND_HOST_PORT="5174"; docker compose up`.
- **Backend `Connection refused` to the DB** → with the networking fix merged this shouldn't
  happen; if it does, it's a real issue, not the old `localhost` bug. Full container
  troubleshooting table: [CONTAINER_RUNBOOK.md](CONTAINER_RUNBOOK.md).
- **Slow first build** → expected; subsequent `docker compose up` runs are cached. Prebuilt
  multi-arch images (Change 6, still open) would remove the build entirely.
- **Can't RDP** → confirm the NSG allows port 3389 from your IP:
  `az vm open-port -g firemaster-test-rg -n fm-win-test --port 3389`.
