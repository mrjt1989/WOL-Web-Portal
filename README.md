# WOL Web Portal

A small Flask web app for waking a home PC remotely by sending a Wake-on-LAN magic packet. It's designed to run on an always-on device on your home network (e.g. a Raspberry Pi) and be reached remotely over a private overlay network such as [Tailscale](https://tailscale.com/), rather than being exposed to the public internet.

## Features

- Single-admin login — first run walks you through creating one admin account; credentials are stored locally in `users.json` with scrypt-hashed passwords and restricted file permissions (`chmod 600`).
- Simple dashboard with a "Send Wake-on-LAN Packet" button.
- Served with [Waitress](https://docs.pylonsproject.org/projects/waitress/), a production-ready WSGI server (not Flask's dev server).

## Requirements

- Python 3
- Dependencies listed in `requirements.txt`

## Setup

1. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy the example environment file and fill in your own values:
   ```bash
   cp .env.example .env
   ```

   | Variable     | Description                                                        |
   |--------------|---------------------------------------------------------------------|
   | `TARGET_MAC` | MAC address of the PC you want to wake, e.g. `aa:bb:cc:dd:ee:ff`    |
   | `HOST_IP`    | IP address the web server binds to (e.g. your Tailscale IP)          |
   | `PORT`       | Port the web server listens on                                      |
   | `SECRET_KEY` | Random secret used to sign Flask session cookies                    |

   Generate a strong `SECRET_KEY` with:
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```
4. Run the app:
   ```bash
   python main.py
   ```
5. On first visit you'll be redirected to `/setup` to create the admin account. After that, use `/login`.

## Usage

Log in, then click **Send Wake-on-LAN Packet** on the dashboard to broadcast a magic packet to `TARGET_MAC`, waking the target machine.

## Project structure

```
main.py            Flask app: auth, setup/login/logout, wake endpoint
templates/          HTML pages (login, setup, dashboard, wake result)
static/styles.css   App styling
requirements.txt    Python dependencies
.env.example        Template for required environment variables
```

## Security notes

- This is a single-admin app: the `/setup` route only works until the first account is created.
- There is no CSRF protection or login rate limiting, so it's meant to run on a trusted private network (e.g. behind Tailscale) rather than being exposed directly to the internet.
- If you put this behind a reverse proxy with HTTPS, consider also setting `SESSION_COOKIE_SECURE` in `main.py`.
