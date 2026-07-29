import json
import time
from scraper import get_librus_data
from notifier import notify_all

DB_FILE = "history.json"
MD_FULL_CALENDAR_FILE = "Librus_Pelny_Terminarz.md"

def load_history():
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Ochrona przed błędem 404 z API GitHuba w przypadku pustego repozytorium
            if isinstance(data, dict) and data.get("message") == "Not Found":
                return {}
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_history(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def check_for_updates():
    history = load_history()
    # Zabezpieczenie przed uszkodzoną strukturą
    if not isinstance(history, dict):
        history = {}

    current_data = get_librus_data()
    
    session_updates = []
    new_history = {}

    for event in current_data:
        key = f"{event['data_wydarzenia']}_{event['nauczyciel']}_{event['data_dodania']}"
        status = "OK"
        old_desc = None

        if key not in history:
            status = "NOWE"
            session_updates.append(key)
        elif isinstance(history.get(key), dict) and history[key].get('opis', '') != event['opis']:
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
        
        if old_desc:
            event_entry["stary_opis"] = old_desc

        new_history[key] = event_entry

    updated_history_to_save = history.copy()
    updated_history_to_save.update(new_history)
    
    # Usuwamy "śmieci", zostawiamy tylko poprawne słowniki wydarzeń
    clean_history = {k: v for k, v in updated_history_to_save.items() if isinstance(v, dict) and 'data_wydarzenia' in v}
    save_history(clean_history)
    
    return session_updates, new_history, clean_history

def generate_unified_calendar(session_keys, current_session_data, total_history):
    with open(MD_FULL_CALENDAR_FILE, "w", encoding="utf-8") as f:
        f.write(f"# 📅 Pełny Terminarz Librus\n")
        f.write(f"*Ostatnia aktualizacja: {time.strftime('%Y-%m-%d %H:%M')}*\n\n")
        
        if session_keys:
            f.write(f"> 💡 **Uwaga:** W tym widoku znaleziono {len(session_keys)} zmian względem poprzedniego sprawdzenia.\n\n")

        # Filtrujemy dane, aby upewnić się, że nie ma w nich śmieci z pobierania
        valid_events = [x for x in total_history.values() if isinstance(x, dict) and 'data_wydarzenia' in x]
        sorted_events = sorted(valid_events, key=lambda x: x['data_wydarzenia'])
        
        last_date = ""
        for ev in sorted_events:
            key = f"{ev['data_wydarzenia']}_{ev['nauczyciel']}_{ev['data_dodania']}"
            
            if ev['data_wydarzenia'] != last_date:
                last_date = ev['data_wydarzenia']
                f.write(f"\n## 📆 {last_date}\n")
            
            prefix = ""
            desc_text = ev.get('opis', '')
            
            if key in session_keys:
                current_ev = current_session_data.get(key)
                if current_ev and current_ev.get('status') == "NOWE":
                    prefix = "🔴 **[NOWE]** "
                elif current_ev and current_ev.get('status') == "ZMIENIONO":
                    prefix = "🟡 **[ZMIENIONO]** "
                    stary = current_ev.get('stary_opis', '...')
                    desc_text = f"~~{stary}~~  \n  ➡️ **AKTUALIZACJA:** {ev['opis']}"

            f.write(f"- {prefix}**{ev['nauczyciel']}**: {desc_text}\n")
            if ev.get('data_dodania') and ev['data_dodania'] != "Brak":
                f.write(f"  *(Dodano: {ev['data_dodania']})*\n")
            f.write("\n")
                
    print(f"-> Zaktualizowano pełny widok kalendarza ({MD_FULL_CALENDAR_FILE}).")
    if session_keys:
        print(f"-> Wykryto {len(session_keys)} istotnych zmian.")

if __name__ == "__main__":
    print("Rozpoczynam analizę terminarza...")
    keys_updated_now, current_session, full_db = check_for_updates()
    generate_unified_calendar(keys_updated_now, current_session, full_db)
    
    # Wysyłamy powiadomienia
    notify_all(keys_updated_now, current_session, full_db, MD_FULL_CALENDAR_FILE)
    
    print("\nProces zakończony.")
