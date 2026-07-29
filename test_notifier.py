import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from notifier import notify_all

# Wczytujemy zmienne z .env
load_dotenv()


def run_test():
    print("--- Rozpoczynam test modułu notifier.py (wersja Discord & E-mail) ---")

    # Tworzymy symulowane dane do powiadomień
    today_str = datetime.now().strftime("%Y-%m-%d")
    tomorrow_str = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    far_future_str = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d")

    # Tworzymy klucze sesji, które udają nowe/zmienione wpisy
    new_event_key = f"{today_str}_Testowy Nauczyciel 1_Brak"
    changed_event_key = f"{tomorrow_str}_Testowy Nauczyciel 2_Brak"
    far_future_key = f"{far_future_str}_Testowy Nauczyciel 3_Brak"

    session_keys = [new_event_key, changed_event_key, far_future_key]

    # Symulowane dane z obecnej sesji pobierania
    current_session_data = {
        new_event_key: {
            "data_wydarzenia": today_str,
            "nauczyciel": "Testowy Nauczyciel 1",
            "data_dodania": "Brak",
            "opis": "**[Nr lekcji: 1 | Testowe wydarzenie]**\nSzczegóły: To jest symulowane NOWE wydarzenie na dziś.",
            "status": "NOWE"
        },
        changed_event_key: {
            "data_wydarzenia": tomorrow_str,
            "nauczyciel": "Testowy Nauczyciel 2",
            "data_dodania": "Brak",
            "opis": "**[Nr lekcji: 2 | Zmienione wydarzenie]**\nSzczegóły: Zaktualizowana treść wydarzenia na jutro.",
            "status": "ZMIENIONO",
            "stary_opis": "**[Nr lekcji: 2 | Stare wydarzenie]**\nSzczegóły: Stara treść wydarzenia."
        },
        far_future_key: {
            "data_wydarzenia": far_future_str,
            "nauczyciel": "Testowy Nauczyciel 3",
            "data_dodania": "Brak",
            "opis": "**[Nr lekcji: 3 | Wydarzenie w przyszłości]**\nSzczegóły: Test zmian daleko w przyszłości.",
            "status": "NOWE"
        }
    }

    # Łączna baza (do wygenerowania pełnego planu)
    total_history = {
        # Dodajemy te z sesji
        new_event_key: current_session_data[new_event_key],
        changed_event_key: current_session_data[changed_event_key],
        far_future_key: current_session_data[far_future_key],
        # I jedno stabilne wydarzenie na pojutrze, które nie uległo zmianie (status OK)
        f"{(datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d')}_Testowy Nauczyciel 4_Brak": {
            "data_wydarzenia": (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d"),
            "nauczyciel": "Testowy Nauczyciel 4",
            "data_dodania": "Brak",
            "opis": "**[Nr lekcji: 4 | Stabilne wydarzenie]**\nSzczegóły: Brak zmian, powinno wyświetlić się normalnie.",
            "status": "OK"
        }
    }

    # Plik załącznika
    dummy_attachment = "Librus_Pelny_Terminarz.md"
    if not os.path.exists(dummy_attachment):
        with open(dummy_attachment, "w", encoding="utf-8") as f:
            f.write("# Testowy terminarz")

    # Wywołanie głównej funkcji notifiera
    notify_all(session_keys, current_session_data, total_history, dummy_attachment)

    print("--- Test zakończony. Sprawdź pocztę oraz swój serwer Discord ---")


if __name__ == "__main__":
    run_test()
