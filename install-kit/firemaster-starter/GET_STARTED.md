# Get Started with FIREMaster

FIREMaster runs entirely on your own computer. Your financial data never leaves your
machine. This starter kit launches the app from prebuilt images — no coding, no GitHub
account, nothing to compile.

**Total time: about 5 minutes** (most of it is installing Docker).

---

## 1. Install Docker Desktop

Docker is the free tool that runs FIREMaster on your machine.

- **Mac:** Download from [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/),
  drag it to Applications, and launch it. Wait until the whale icon in your menu bar stops animating.
- **Windows:** Download the installer from the same page, run it, and reboot once when asked
  (this sets up "WSL2", which Docker needs). Launch Docker Desktop and wait for it to say
  **"Engine running"**.

You only ever do this once.

---

## 2. Open a terminal in this folder

Unzip this kit somewhere easy to find (e.g. your Desktop), then:

- **Mac:** Right-click the `firemaster-starter` folder → **New Terminal at Folder**.
- **Windows:** Open the folder, click the address bar, type `powershell`, and press Enter.

---

## 3. Set your password (first run only)

Paste this and press Enter. It asks you to choose an admin password for the app:

```
docker compose run --rm --no-deps backend uv run python -m app.setup
```

---

## 4. Start FIREMaster

```
docker compose up
```

The first time, this downloads the app (~30–60 seconds). When you see the logs settle and
`migrate` say it finished, you're ready.

> **Tip — getting your terminal back.** `docker compose up` runs in the foreground and streams
> logs. Docker shows a small menu at the bottom of the window:
> - Press **`d`** to **detach** — the app keeps running, and you get your terminal back.
> - Press **Ctrl+C** to **stop** the app.
>
> (You can also skip the foreground entirely and start detached from the get-go with
> `docker compose up -d`.)

---

## 5. Open the app

Go to **http://localhost:5173** in your browser and log in with the password you just set.

You'll land in a fully populated demo: dashboard, retirement projections, runway, scenarios —
all driven by example data so you can explore everything before connecting anything real.

---

## Using your own data (connect Monarch)

The demo is great for exploring, but when you're ready to track your **real** finances, connect your
Monarch Money account — one command, your data stays on your machine. See **CONNECT_MONARCH.md** in
this folder. The demo is replaced by your real accounts automatically on the first sync.

---

## Everyday use

| What | Command (run in this folder) |
|------|------------------------------|
| Start | `docker compose up` (add `-d` to run in the background) |
| Stop | `docker compose down` — your data is kept |
| Update to the latest version | `docker compose pull` then `docker compose up -d` |

In a foreground session, press **`d`** to detach (app keeps running) or **Ctrl+C** to stop it.

---

## Troubleshooting

- **"Cannot connect to the Docker daemon"** — Docker Desktop isn't running. Launch it, wait for
  the engine to start, try again.
- **"port is already allocated" / 5173 in use** — something else is using that port. Stop it,
  or ask support how to change the port.
- **The page won't load** — give it a few more seconds on first run while images download, then
  refresh `http://localhost:5173`.

Questions? Reply to your welcome email and we'll help.
