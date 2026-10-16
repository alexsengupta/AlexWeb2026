#!/usr/bin/env python3
"""Daily health check for the Scopus -> website pipeline. Runs on the Nectar VM.

Emails only when something is wrong (or always, with --test). Checks:
  1. The newest Katana run log is < MAX_AGE_DAYS old and all 4 scripts exited 0.
  2. The newest run log has no OpenAI 401 / bad-key errors (these do not change exit codes).
  3. A scopus_monthly PBS job is waiting in the queue (the self-resubmitting chain is alive).
  4. The website's scopus_all_MHW.csv matches Katana's (VM copy step worked).

SMTP settings live in ~/.alert_env (chmod 600, OUTSIDE the web root):
    ALERT_SMTP_USER=you@gmail.com
    ALERT_SMTP_PASS=<16-character Gmail app password>
    ALERT_TO=you@example.com
    # optional: ALERT_SMTP_HOST=smtp.gmail.com  ALERT_SMTP_PORT=587
"""
import datetime as dt
import os
import re
import smtplib
import subprocess
import sys
from email.message import EmailMessage

KATANA = "z3045790@katana.restech.unsw.edu.au"
SITE_CSV = "/home/ubuntu/AlexWeb2026/MarineHeatwaves/scopus_all_MHW.csv"
MAX_AGE_DAYS = 35
ENV_FILE = os.path.expanduser("~/.alert_env")


def load_env(path):
    cfg = {}
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                cfg[k.strip()] = v.strip().strip('"').strip("'")
    return cfg


def ssh(cmd):
    try:
        r = subprocess.run(
            ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=20", KATANA, cmd],
            capture_output=True, text=True, timeout=120)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except subprocess.TimeoutExpired:
        return 255, "", "ssh timed out"


def run_checks():
    problems, notes = [], []

    # 1 + 2. Newest Katana run log
    rc, log, err = ssh("ls -1t ~/SCOPUS/logs/cron_*.log | head -1")
    if rc != 0 or not log:
        problems.append(f"Could not read Katana run logs (ssh rc={rc}): {err or 'no logs found'}")
        return problems, notes
    m = re.search(r"cron_(\d{8})_(\d{6})\.log$", log)
    age = None
    if not m:
        problems.append(f"Unexpected log name: {log}")
    else:
        when = dt.datetime.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M%S")
        age = (dt.datetime.now() - when).total_seconds() / 86400
        notes.append(f"Last Katana run: {when:%Y-%m-%d %H:%M} (Sydney), {age:.1f} days ago")
        if age > MAX_AGE_DAYS:
            problems.append(f"Last Katana run was {age:.0f} days ago (limit {MAX_AGE_DAYS}).")

    _, n_ok, _ = ssh(f"grep -c 'exit code: 0' {log}")
    n_ok = int(n_ok) if n_ok.isdigit() else 0
    notes.append(f"Scripts exiting 0 in last run: {n_ok}/4")
    if n_ok < 4:
        problems.append(f"Last run: only {n_ok}/4 scripts exited 0. See {log} on Katana.")

    _, n_key, _ = ssh(f"grep -c -i '401\\|Incorrect API key' {log}")
    if n_key.isdigit() and int(n_key) > 0:
        problems.append(f"{n_key} API-key/401 errors in {log} (themes will be blank).")

    # 3. Next run queued
    rc, waiting, err = ssh("qselect -u z3045790 -N scopus_monthly -s W")
    if rc != 0:
        problems.append(f"Could not query the PBS queue: {err}")
    elif not waiting:
        problems.append("No scopus_monthly job is waiting in the PBS queue: the monthly chain "
                        "is broken. Restart with:  qsub ~/SCOPUS/scopus_monthly.pbs")
    else:
        notes.append(f"Next run queued: {waiting}")

    # 4. Website copy matches Katana (skip in the ~11 h gap between Katana run and VM copy)
    if age is not None and age > 1:
        _, ksize, _ = ssh("stat -c %s ~/SCOPUS/scopus_all_MHW.csv")
        try:
            vsize = os.path.getsize(SITE_CSV)
        except OSError:
            vsize = -1
        notes.append(f"scopus_all_MHW.csv size: Katana {ksize}, website {vsize}")
        if ksize.isdigit() and int(ksize) != vsize:
            problems.append("Website CSV differs from Katana's: the VM copy step "
                            "(download_katana_csv.sh) may have failed. Check MarineHeatwaves/cron.log.")
    return problems, notes


def send(cfg, subject, body):
    msg = EmailMessage()
    msg["Subject"], msg["From"], msg["To"] = subject, cfg["ALERT_SMTP_USER"], cfg["ALERT_TO"]
    msg.set_content(body)
    host = cfg.get("ALERT_SMTP_HOST", "smtp.gmail.com")
    port = int(cfg.get("ALERT_SMTP_PORT", "587"))
    with smtplib.SMTP(host, port, timeout=30) as s:
        s.starttls()
        s.login(cfg["ALERT_SMTP_USER"], cfg["ALERT_SMTP_PASS"])
        s.send_message(msg)


def main():
    test = "--test" in sys.argv
    problems, notes = run_checks()
    stamp = f"{dt.datetime.utcnow():%Y-%m-%d %H:%M} UTC"
    print(f"[{stamp}] problems={len(problems)}; " + "; ".join(notes))
    if not problems and not test:
        return 0
    body = (("PROBLEMS:\n- " + "\n- ".join(problems) + "\n\n") if problems else "All checks passed.\n\n")
    body += "Details:\n- " + "\n- ".join(notes) + f"\n\nChecked {stamp} from the Nectar VM."
    subject = ("[Scopus pipeline] PROBLEM: " + problems[0][:80]) if problems else "[Scopus pipeline] test: all OK"
    send(load_env(ENV_FILE), subject, body)
    print("Email sent.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
