# TLS bootstrap

## Goal

Get a real Let's Encrypt certificate on the production host so HTTPS
works on day 1 and renews itself for the next two years.

## One-time setup

1. DNS A record `landloads.example.co.ke` → server public IP.
2. On the server:
   ```bash
   sudo apt update && sudo apt install -y certbot
   sudo mkdir -p /var/www/certbot /etc/letsencrypt
   ```
3. Run the bootstrap one-shot:
   ```bash
   sudo certbot certonly --webroot -w /var/www/certbot \
     -d landloads.example.co.ke \
     --email ops@landloads.example.co.ke --agree-tos --no-eff-email
   ```
4. Symlink the cert path the production Nginx config expects:
   ```bash
   sudo ln -sfn /etc/letsencrypt/live/landloads.example.co.ke \
     /etc/letsencrypt/live/landloads
   ```
5. Swap `default.conf` → production template (from the repo, kept outside
   `conf.d/` in git so Docker Compose does not load two files that both define
   the same `upstream` names):
   ```bash
   sudo mv /etc/nginx/conf.d/default.conf /etc/nginx/conf.d/default.dev.conf
   sudo cp deploy/nginx/prod/default.prod.conf /etc/nginx/conf.d/default.conf
   sudo nginx -t && sudo systemctl reload nginx
   ```

## Renewal

Certbot installs a systemd timer (`certbot.timer`) that renews 30 days
before expiry. Verify with:

```bash
systemctl list-timers certbot.timer
sudo certbot renew --dry-run
```

Add a post-renew hook to reload Nginx:

```ini
# /etc/letsencrypt/renewal-hooks/post/reload-nginx.sh
#!/usr/bin/env bash
systemctl reload nginx
```
```bash
sudo chmod +x /etc/letsencrypt/renewal-hooks/post/reload-nginx.sh
```

## Verification

```bash
curl -sSI https://landloads.example.co.ke/healthz | grep -i strict-transport
# expect: Strict-Transport-Security: max-age=63072000; includeSubDomains
```
