# Deploy on a Hostinger VPS (off-Render option)

The app is a single Docker service (FastAPI serves the built React frontend + the
`/api`). Hostinger **shared/Cloud** hosting can't run it (no persistent process /
no Docker), but a **Hostinger VPS (KVM)** can. This is the all-Hostinger
alternative to Render.

> You only need this if you want everything under Hostinger. Render (see
> [../render.yaml](../render.yaml)) already hosts the demo with zero servers to
> manage. A VPS is ~$5–8/mo but gives you no cold starts and full control.

Two paths: **A** (recommended) gives a Render-like experience — connect GitHub,
auto-deploy on push, automatic HTTPS. **B** is plain Docker Compose.

---

## Path A — Coolify (or Dokploy) on the VPS  ✅ recommended

[Coolify](https://coolify.io) is a self-hosted PaaS. It connects to GitHub,
builds from our `Dockerfile`, redeploys on every push, and issues Let's Encrypt
TLS automatically — i.e. Render, but on your own VPS.

1. **Provision the VPS.** In hPanel → VPS, deploy a KVM plan. During setup pick
   the **Coolify** (or **Dokploy**) application template, or choose plain Ubuntu
   and install Coolify after: `curl -fsSL https://cdn.coollabs.io/coolify/install.sh | bash`.
2. **Point a domain/subdomain** (e.g. `cuas.yourdomain.com`) at the VPS IP with an
   `A` record. (Optional but needed for HTTPS.)
3. **Open Coolify** at `http://<vps-ip>:8000`, create an admin account.
4. **Connect GitHub** (Coolify → Sources → GitHub App) and authorize the
   `ProActive-B/cautious-chainsaw` repo.
5. **New Resource → Application → from your repo.** Coolify detects the
   `Dockerfile`. Set:
   - Build pack: **Dockerfile**
   - Port: **8000**
   - Domain: your subdomain (Coolify provisions HTTPS automatically)
   - Health check path: **/health**
6. **Deploy.** Auto-deploy on push is on by default. Done — you get
   `https://cuas.yourdomain.com`.

Environment variables (optional): add `FAA_NOTAM_API_KEY` etc. in the app's
Environment tab. Live aircraft need **no** key (keyless community feeds).

---

## Path B — plain Docker Compose

For a minimal setup without a PaaS layer.

1. **SSH in** and install Docker:
   ```bash
   curl -fsSL https://get.docker.com | sh
   ```
2. **Clone and start:**
   ```bash
   git clone https://github.com/ProActive-B/cautious-chainsaw.git
   cd cautious-chainsaw
   docker compose up -d --build
   ```
   The app is now on `http://<vps-ip>:8000`. Check `http://<vps-ip>:8000/health`.
3. **Update after changes:**
   ```bash
   git pull && docker compose up -d --build
   ```

### Add HTTPS (Caddy reverse proxy)
Plain compose serves HTTP on :8000. For a domain + automatic TLS, put Caddy in
front. Create `/etc/caddy/Caddyfile`:
```
cuas.yourdomain.com {
    reverse_proxy localhost:8000
}
```
Then `docker run -d --network host -v /etc/caddy/Caddyfile:/etc/caddy/Caddyfile -v caddy_data:/data caddy`.
Caddy fetches a Let's Encrypt cert automatically. (Coolify/Path A does this for you.)

---

## Operations
- **Logs:** `docker compose logs -f` (Path B) or the Coolify logs tab (Path A).
- **Health:** `GET /health` returns feed status (`faa_airspace_staged`, etc.).
- **Firewall:** allow 80/443 (and 8000 only if exposing it directly).
- **Resources:** the image loads ~5 MB of staged FAA airspace into memory; a
  1 GB VPS is plenty.
- **Updating the legal rules DB:** edit `backend/rules/**`, commit, push → Path A
  auto-redeploys; Path B `git pull && docker compose up -d --build`.
