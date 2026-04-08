import json
import time
from scraper import get_librus_data

DB_FILE = "out/history.json"
MD_FULL_CALENDAR_FILE = "out/Librus_Pelny_Terminarz.md"


def load_history():
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_history(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def check_for_updates():
    history = load_history()
    current_data = get_librus_data()

    # Przechowujemy klucze wpisów, które zmieniły się w tym konkretnym uruchomieniu
    session_updates = []
    new_history = {}

    for event in current_data:
        key = f"{event['data_wydarzenia']}_{event['nauczyciel']}_{event['data_dodania']}"

        status = "OK"
        old_desc = None

        # Porównanie z historią
        if key not in history:
            status = "NOWE"
            session_updates.append(key)
        elif history[key].get('opis', '') != event['opis']:
            status = "ZMIENIONO"
            old_desc = history[key].get('opis', 'Brak starego opisu')
            session_updates.append(key)

        event_entry = {
            "data_wydarzenia": event['data_wydarzenia'],
            "nauczyciel": event['nauczyciel'],
            "data_dodania": event['data_dodania'],
            "opis": event['opis'],
            "status": status
        }

        # Jeśli nastąpiła zmiana, zachowujemy starą wersję do wyświetlenia w MD
        if old_desc:
            event_entry["stary_opis"] = old_desc

        new_history[key] = event_entry

    # Aktualizujemy bazę danych, ale zachowujemy stare statusy tylko dla sesji
    # W history.json po zapisie wszystko wróci do "OK" przy następnym sprawdzaniu,
    # chyba że znowu wystąpi różnica.
    updated_history_to_save = history.copy()
    updated_history_to_save.update(new_history)
    save_history(updated_history_to_save)

    return session_updates, new_history, updated_history_to_save


def generate_unified_calendar(session_keys, current_session_data, total_history):
    """
    Generuje jeden plik MD, który zawiera wszystko, ale z wyróżnieniem zmian
    z ostatniego pobierania.
    """
    with open(MD_FULL_CALENDAR_FILE, "w", encoding="utf-8") as f:
        f.write(f"# 📅 Pełny Terminarz Librus\n")
        f.write(f"*Ostatnia aktualizacja: {time.strftime('%Y-%m-%d %H:%M')}*\n\n")

        if session_keys:
            f.write(
                f"> 💡 **Uwaga:** W tym widoku znaleziono {len(session_keys)} zmian względem poprzedniego sprawdzenia.\n\n")

        # Sortujemy chronologicznie wszystkie zdarzenia z historii
        sorted_events = sorted(total_history.values(), key=lambda x: x['data_wydarzenia'])

        last_date = ""
        for ev in sorted_events:
            # Klucz do identyfikacji czy to zmiana z TEJ sesji
            key = f"{ev['data_wydarzenia']}_{ev['nauczyciel']}_{ev['data_dodania']}"

            if ev['data_wydarzenia'] != last_date:
                last_date = ev['data_wydarzenia']
                f.write(f"\n## 📆 {last_date}\n")

            # Logika ikonek i opisu zmian
            prefix = ""
            desc_text = ev['opis']

            if key in session_keys:
                current_ev = current_session_data.get(key)
                if current_ev and current_ev['status'] == "NOWE":
                    prefix = "🔴 **[NOWE]** "
                elif current_ev and current_ev['status'] == "ZMIENIONO":
                    prefix = "🟡 **[ZMIENIONO]** "
                    stary = current_ev.get('stary_opis', '...')
                    desc_text = f"~~{stary}~~  \n  ➡️ **AKTUALIZACJA:** {ev['opis']}"

            f.write(f"- {prefix}**{ev['nauczyciel']}**: {desc_text}\n")
            if ev['data_dodania'] != "Brak":
                f.write(f"  *(Dodano: {ev['data_dodania']})*\n")
            f.write("\n")

    print(f"-> Zaktualizowano pełny widok kalendarza ({MD_FULL_CALENDAR_FILE}).")
    if session_keys:
        print(f"-> Wykryto {len(session_keys)} istotnych zmian.")


if __name__ == "__main__":
    print("Rozpoczynam analizę terminarza...")

    # Pobieramy dane i sprawdzamy co jest nowe w tym konkretnym przebiegu
    keys_updated_now, current_session, full_db = check_for_updates()

    # Tworzymy jeden, spójny plik
    generate_unified_calendar(keys_updated_now, current_session, full_db)

    print("\nProces zakończony.")