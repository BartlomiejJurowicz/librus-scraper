import os
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

def parse_calendar_view(driver):
    """Wyciąga dane z aktualnie wyrenderowanego miesiąca (Tekst widoczny + ukryte szczegóły)."""
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    extracted_events = []
    
    try:
        month_select = Select(driver.find_element(By.NAME, 'miesiac'))
        year_select = Select(driver.find_element(By.NAME, 'rok'))
        current_month = int(month_select.first_selected_option.get_attribute('value'))
        current_year = int(year_select.first_selected_option.get_attribute('value'))
    except:
        now = datetime.now()
        current_month, current_year = now.month, now.year

    days = soup.find_all('div', class_='kalendarz-dzien')
    
    for day in days:
        day_num_elem = day.find('div', class_='kalendarz-numer-dnia')
        if not day_num_elem:
            continue
            
        day_num = day_num_elem.get_text(strip=True)
        event_date = f"{current_year}-{current_month:02d}-{int(day_num):02d}"

        # Szukamy wszystkich kafelków po klasie
        events = day.find_all('td', class_=lambda c: c and 'no-border-left' in c)
        
        for cell in events:
            visible_text = cell.get_text(separator=' | ', strip=True)
            visible_text = visible_text.replace(" | ,", ",").replace("|,", ",")
            
            event = {
                "data_wydarzenia": event_date,
                "nauczyciel": "Nieznany", 
                "opis": f"**[{visible_text}]**\n" if visible_text else "", 
                "data_dodania": "Brak"
            }
            
            if cell.has_attr('title'):
                title_content = cell['title'].replace('<br>', '\n').replace('<br />', '\n')
                lines = [line.strip() for line in title_content.split('\n') if line.strip()]
                
                dodatkowy_opis = []
                for line in lines:
                    if line.startswith("Nauczyciel:"): 
                        event["nauczyciel"] = line.replace("Nauczyciel:", "").strip()
                    elif line.startswith("Data dodania:"): 
                        event["data_dodania"] = line.replace("Data dodania:", "").strip()
                    else:
                        if line.startswith("Opis:"):
                            line = line.replace("Opis:", "").strip()
                        if line: 
                            dodatkowy_opis.append(line)

                if dodatkowy_opis:
                    event["opis"] += "Szczegóły: " + " ".join(dodatkowy_opis)
            
            if event["nauczyciel"] == "Nieznany" and "Nauczyciel:" in visible_text:
                parts = visible_text.split("Nauczyciel:")
                if len(parts) > 1:
                    nauczyciel = parts[1].split("|")[0].replace("Godziny", "").strip()
                    event["nauczyciel"] = nauczyciel

            event["opis"] = event["opis"].strip()
            extracted_events.append(event)
            
    return extracted_events

def get_librus_data():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new") 
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    wait = WebDriverWait(driver, 15)
    
    all_events = []

    try:
        driver.get("https://portal.librus.pl/rodzina")
        time.sleep(2) 
        
        # Agresywne usuwanie ciasteczek
        driver.execute_script("""
            var overlays = document.querySelectorAll('.modal, .modal-backdrop, #consent-categories-modal, [id*="consent"]');
            overlays.forEach(el => el.remove());
            document.body.classList.remove('modal-open');
            document.body.style.filter = 'none';
        """)
        time.sleep(1)

        dropdown = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "a.dropdown-toggle.btn-synergia-top")))
        driver.execute_script("arguments[0].click();", dropdown)
        time.sleep(1)

        login_link = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "a[href='/rodzina/synergia/loguj']")))
        driver.execute_script("arguments[0].click();", login_link)
        
        time.sleep(3)
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        if iframes: 
            driver.switch_to.frame(iframes[0])

        try:
            login_input = wait.until(EC.presence_of_element_located((By.ID, "Login")))
            pass_input = driver.find_element(By.ID, "Pass")
        except:
            login_input = wait.until(EC.presence_of_element_located((By.NAME, "Login")))
            pass_input = driver.find_element(By.NAME, "Pass")

        login_input.clear()
        login_input.send_keys(os.getenv("LIBRUS_LOGIN"))
        
        pass_input.clear()
        pass_input.send_keys(os.getenv("LIBRUS_PASS"))
        
        # --- DIAGNOSTYKA I LUDZKIE KLIKNIĘCIE ---
        dlugosc_hasla = len(str(os.getenv("LIBRUS_PASS", "")))
        print(f"-> Zabezpieczenie: Długość przekazanego hasła to {dlugosc_hasla} znaków.")
        
        time.sleep(1) # Chwila oddechu dla walidacji formularza
        
        # Zamiast klikać przycisk, wciskamy ENTER
        pass_input.send_keys(Keys.RETURN)

        driver.switch_to.default_content()
        wait.until(EC.url_contains("synergia.librus.pl"))
        
        # POBIERANIE BIEŻĄCEGO MIESIĄCA
        print("-> Pobieram bieżący miesiąc...")
        driver.get("https://synergia.librus.pl/terminarz")
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "kalendarz")))
        all_events.extend(parse_calendar_view(driver))

        # ZMIANA NA NASTĘPNY MIESIĄC
        print("-> Przełączam na następny miesiąc...")
        try:
            driver.execute_script("""
                var m = document.querySelector('select[name="miesiac"]');
                if(m.selectedIndex < m.options.length - 1) {
                    m.selectedIndex = m.selectedIndex + 1;
                } else {
                    m.selectedIndex = 0;
                    var r = document.querySelector('select[name="rok"]');
                    r.selectedIndex = r.selectedIndex + 1;
                    r.dispatchEvent(new Event('change'));
                }
                m.dispatchEvent(new Event('change'));
            """)
            time.sleep(3) 
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, "kalendarz")))
            all_events.extend(parse_calendar_view(driver))
        except Exception as e:
            print("Nie udało się załadować kolejnego miesiąca.")

    except Exception as e:
        driver.save_screenshot("error_headless.png")
        raise e

    finally:
        driver.quit()
    
    return all_events
