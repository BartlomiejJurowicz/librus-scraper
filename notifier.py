import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime, timedelta
import requests

POLISH_WEEKDAYS = ["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek", "Sobota", "Niedziela"]


def send_email(subject, html_body, attachment_path=None):
    server = os.getenv("SMTP_SERVER")
    port_str = os.getenv("SMTP_PORT", "465")
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")
    receiver = os.getenv("EMAIL_RECEIVER")

    if not all([server, user, password, receiver]):
        print("-> Brak pełnej konfiguracji SMTP (E-mail). Pomijam wysyłkę e-mail.")
        return

    try:
        port = int(port_str)
    except ValueError:
        print(f"-> Niepoprawny port SMTP: {port_str}. Pomijam wysyłkę e-mail.")
        return

    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = receiver

    # Część alternatywna dla treści
    alt_part = MIMEMultipart("alternative")
    alt_part.attach(MIMEText(html_body, "html"))
    msg.attach(alt_part)

    # Załącznik
    if attachment_path and os.path.exists(attachment_path):
        part = MIMEBase("application", "octet-stream")
        try:
            with open(attachment_path, "rb") as f:
                part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f"attachment; filename={os.path.basename(attachment_path)}"
            )
            msg.attach(part)
        except Exception as e:
            print(f"-> Błąd przy dołączaniu pliku {attachment_path}: {e}")

    try:
        if port == 465:
            with smtplib.SMTP_SSL(server, port, timeout=15) as smtp:
                smtp.login(user, password)
                smtp.sendmail(user, receiver, msg.as_string())
        else:
            with smtplib.SMTP(server, port, timeout=15) as smtp:
                smtp.ehlo()
                smtp.starttls()
                smtp.ehlo()
                smtp.login(user, password)
                smtp.sendmail(user, receiver, msg.as_string())
        print("-> Wiadomość e-mail została wysłana pomyślnie.")
    except Exception as e:
        print(f"-> Błąd podczas wysyłania e-maila: {e}")


def send_discord(embeds):
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")

    if not webhook_url:
        print("-> Brak konfiguracji DISCORD_WEBHOOK_URL. Pomijam wysyłkę Discord.")
        return

    payload = {
        "content": "🔔 **Aktualizacja terminarza Librus**",
        "embeds": embeds
    }

    try:
        response = requests.post(payload_url:=webhook_url, json=payload, timeout=15)
        if response.status_code in [200, 204]:
            print("-> Wiadomość Discord została wysłana pomyślnie.")
        else:
            print(f"-> Bramka Discord zwróciła status {response.status_code}: {response.text}")
    except Exception as e:
        print(f"-> Błąd podczas wysyłania wiadomości Discord: {e}")


def format_discord_message(session_keys, current_session_data, total_history):
    # 1. Wykryte zmiany w tym przebiegu
    changes = []
    for key in session_keys:
        ev = current_session_data.get(key)
        if not ev:
            ev = total_history.get(key)
        if ev:
            status = ev.get("status", "NOWE")
            date = ev.get("data_wydarzenia")
            teacher = ev.get("nauczyciel")
            desc = ev.get("opis", "")
            if len(desc) > 200:
                desc = desc[:197] + "..."

            if status == "NOWE":
                changes.append(f"🔴 **[NOWE]** {date} | **{teacher}**: {desc}")
            elif status == "ZMIENIONO":
                stary = ev.get("stary_opis", "Brak")
                if len(stary) > 100:
                    stary = stary[:97] + "..."
                changes.append(f"🟡 **[ZMIENIONO]** {date} | **{teacher}**:\n*Stary:* {stary}\n*Nowy:* {desc}")

    changes_text = "\n".join(changes) if changes else "🔄 *Brak nowych zmian.*"

    # 2. Plan na dziś i +2 dni (łącznie 3 dni)
    today_dt = datetime.now().date()
    days_to_check = [today_dt + timedelta(days=i) for i in range(3)]

    plan_sections = []
    events_by_date = {}
    for ev in total_history.values():
        try:
            ev_date = datetime.strptime(ev["data_wydarzenia"], "%Y-%m-%d").date()
            if ev_date in days_to_check:
                if ev_date not in events_by_date:
                    events_by_date[ev_date] = []
                events_by_date[ev_date].append(ev)
        except Exception:
            continue

    for day in days_to_check:
        day_str = day.strftime("%Y-%m-%d")
        weekday_name = POLISH_WEEKDAYS[day.weekday()]
        day_header = f"🗓️ **{weekday_name}, {day_str}**"

        day_events = events_by_date.get(day, [])
        if not day_events:
            plan_sections.append(f"{day_header}\n_Brak zaplanowanych wydarzeń_")
        else:
            event_lines = []
            for ev in sorted(day_events, key=lambda x: x.get("nauczyciel", "")):
                key = f"{ev['data_wydarzenia']}_{ev['nauczyciel']}_{ev['data_dodania']}"
                prefix = ""
                desc = ev.get("opis", "")

                if key in session_keys:
                    current_ev = current_session_data.get(key)
                    if current_ev:
                        if current_ev.get("status") == "NOWE":
                            prefix = "🔴 "
                        elif current_ev.get("status") == "ZMIENIONO":
                            prefix = "🟡 "

                teacher = ev.get("nauczyciel")
                desc_clean = desc.replace("\n", " ")
                if len(desc_clean) > 150:
                    desc_clean = desc_clean[:147] + "..."
                event_lines.append(f"- {prefix}**{teacher}**: {desc_clean}")
            plan_sections.append(f"{day_header}\n" + "\n".join(event_lines))

    plan_text = "\n\n".join(plan_sections)

    embeds = [
        {
            "title": "🔄 Wykryte zmiany",
            "description": changes_text,
            "color": 15158332 if changes else 3066993  # Czerwony jeśli są zmiany, zielony jeśli brak
        },
        {
            "title": "📅 Plan na dziś i kolejne 2 dni",
            "description": plan_text,
            "color": 3447003  # Niebieski
        }
    ]

    return embeds


def format_email_html(session_keys, current_session_data, total_history):
    now = datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M")
    start_of_month = now.replace(day=1).date()

    # Sortowanie chronologiczne
    sorted_events = sorted(total_history.values(), key=lambda x: x['data_wydarzenia'])

    filtered_events = []
    for ev in sorted_events:
        try:
            ev_date = datetime.strptime(ev["data_wydarzenia"], "%Y-%m-%d").date()
            if ev_date >= start_of_month:
                filtered_events.append(ev)
        except Exception:
            filtered_events.append(ev)

    # Budowanie sekcji zmian na początku
    changes_html = ""
    changes_count = 0
    for key in session_keys:
        ev = current_session_data.get(key)
        if not ev:
            ev = total_history.get(key)
        if ev:
            changes_count += 1
            status = ev.get("status", "NOWE")
            date = ev.get("data_wydarzenia")
            teacher = ev.get("nauczyciel")
            desc = ev.get("opis", "").replace("\n", "<br>")

            if status == "NOWE":
                badge = '<span class="update-badge badge-new">NOWE</span>'
                row_class = 'class="row-new"'
            else:
                badge = '<span class="update-badge badge-changed">ZMIENIONO</span>'
                row_class = 'class="row-changed"'
                stary = ev.get("stary_opis", "Brak").replace("\n", "<br>")
                desc = f'<span class="old-desc">{stary}</span><br>➡️ <span class="new-desc">AKTUALIZACJA: {desc}</span>'

            changes_html += f"""
            <tr {row_class}>
                <td style="white-space: nowrap;"><strong>{date}</strong></td>
                <td>{badge}</td>
                <td><strong>{teacher}</strong></td>
                <td>{desc}</td>
            </tr>
            """

    changes_section = ""
    if changes_count > 0:
        changes_section = f"""
        <h2>🔄 Wykryte zmiany ({changes_count})</h2>
        <table>
            <thead>
                <tr>
                    <th style="width: 15%;">Data</th>
                    <th style="width: 15%;">Status</th>
                    <th style="width: 25%;">Nauczyciel</th>
                    <th style="width: 45%;">Opis / Zmiana</th>
                </tr>
            </thead>
            <tbody>
                {changes_html}
            </tbody>
        </table>
        """
    else:
        changes_section = "<p>🔄 <em>Brak nowo wykrytych zmian od ostatniego uruchomienia.</em></p>"

    # Budowanie pełnej tabeli
    full_schedule_html = ""
    for ev in filtered_events:
        key = f"{ev['data_wydarzenia']}_{ev['nauczyciel']}_{ev['data_dodania']}"
        date = ev.get("data_wydarzenia")
        teacher = ev.get("nauczyciel")
        desc = ev.get("opis", "").replace("\n", "<br>")
        added = ev.get("data_dodania", "Brak")

        row_style = ""
        badge = ""

        if key in session_keys:
            current_ev = current_session_data.get(key)
            if current_ev:
                status = current_ev.get("status")
                if status == "NOWE":
                    row_style = 'class="row-new"'
                    badge = '<span class="update-badge badge-new">NOWE</span> '
                elif status == "ZMIENIONO":
                    row_style = 'class="row-changed"'
                    badge = '<span class="update-badge badge-changed">ZMIENIONO</span> '
                    stary = current_ev.get("stary_opis", "Brak").replace("\n", "<br>")
                    desc = f'<span class="old-desc">{stary}</span><br>➡️ <span class="new-desc">AKTUALIZACJA: {desc}</span>'

        full_schedule_html += f"""
        <tr {row_style}>
            <td style="white-space: nowrap;"><strong>{date}</strong></td>
            <td><strong>{teacher}</strong></td>
            <td>{badge}{desc}</td>
            <td style="font-size: 11px; color: #64748b; white-space: nowrap;">{added}</td>
        </tr>
        """

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; color: #333; line-height: 1.6; margin: 0; padding: 20px; background-color: #f8fafc; }}
  .container {{ max-width: 850px; margin: 0 auto; background: #ffffff; padding: 30px; border-radius: 8px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); border: 1px solid #e2e8f0; }}
  h1 {{ color: #0f172a; border-bottom: 2px solid #e2e8f0; padding-bottom: 10px; margin-top: 0; }}
  h2 {{ color: #1e293b; margin-top: 30px; margin-bottom: 10px; font-size: 18px; }}
  .update-badge {{ display: inline-block; padding: 3px 8px; border-radius: 4px; font-size: 10px; font-weight: bold; text-transform: uppercase; }}
  .badge-new {{ background-color: #dcfce7; color: #166534; }}
  .badge-changed {{ background-color: #fef9c3; color: #854d0e; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 15px; margin-bottom: 20px; }}
  th, td {{ text-align: left; padding: 12px; border-bottom: 1px solid #e2e8f0; font-size: 14px; vertical-align: top; }}
  th {{ background-color: #f1f5f9; color: #475569; font-weight: 600; }}
  tr.row-new {{ background-color: #f0fdf4; }}
  tr.row-changed {{ background-color: #fefce8; }}
  .old-desc {{ text-decoration: line-through; color: #94a3b8; font-size: 13px; }}
  .new-desc {{ font-weight: 600; color: #0f172a; }}
  .footer {{ font-size: 11px; color: #94a3b8; margin-top: 40px; border-top: 1px solid #e2e8f0; padding-top: 15px; text-align: center; }}
</style>
</head>
<body>
  <div class="container">
    <h1>📅 Terminarz Librus - Aktualizacja</h1>
    <p>Ostatnie sprawdzenie planu: <strong>{now_str}</strong></p>
    
    {changes_section}
    
    <h2>📅 Pełny Terminarz (od {start_of_month.strftime('%Y-%m-%d')})</h2>
    <table>
        <thead>
            <tr>
                <th style="width: 15%;">Data</th>
                <th style="width: 25%;">Nauczyciel</th>
                <th style="width: 45%;">Wydarzenie</th>
                <th style="width: 15%;">Dodano</th>
            </tr>
        </thead>
        <tbody>
            {full_schedule_html}
        </tbody>
    </table>
    
    <div class="footer">
        Wiadomość wygenerowana automatycznie przez bota Librus Scraper.
    </div>
  </div>
</body>
</html>
"""
    return html


def notify_all(session_keys, current_session_data, total_history, attachment_path):
    print("-> Przygotowuję powiadomienia...")

    # Wysyłka Discord
    try:
        discord_embeds = format_discord_message(session_keys, current_session_data, total_history)
        send_discord(discord_embeds)
    except Exception as e:
        print(f"-> Wyjątek przy wysyłce Discord: {e}")

    # Wysyłka E-mail
    try:
        changes_count = len(session_keys)
        subject = f"📅 Librus: Pełny plan ({changes_count} zmian)" if changes_count > 0 else "📅 Librus: Pełny plan (brak zmian)"
        email_html = format_email_html(session_keys, current_session_data, total_history)
        send_email(subject, email_html, attachment_path)
    except Exception as e:
        print(f"-> Wyjątek przy wysyłce e-mail: {e}")
