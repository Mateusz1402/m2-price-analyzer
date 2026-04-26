import requests
import psycopg2
import os
from dotenv import load_dotenv
from psycopg2.extras import execute_values


#1 --- INICJALIZACJA ZMIENNYCH ---
load_dotenv()
NEON_DATABASE_URL = os.getenv('DATABASE_URL')
GUS_API_KEY = os.getenv('BDL_API_KEY')

# Mapowanie ID zmiennych na kwartały (ID pochodzą z API)
QUARTER_MAP = {
    "1607934": 1,
    "1607954": 2,
    "1607974": 3,
    "1607994": 4
}


#2 --- FUNKCJE POMOCNICZE ---
#Definicja tabeli, gdy nie istnieje
def init_db():
    conn = psycopg2.connect(NEON_DATABASE_URL)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS housing_data (
            id SERIAL PRIMARY KEY,
            unit_id VARCHAR(12),
            unit_name VARCHAR(255),
            year INT,
            quarter INT,
            value FLOAT,
            UNIQUE(unit_id, year, quarter)
        );
    """)
    conn.commit()
    cur.close()
    conn.close()
    print("Baza danych gotowa.")


def fetch_gus_data(var_id):
    """Pobiera dane dla wszystkich powiatów (przechodzi przez wszystkie strony API)."""
    results = []
    page = 0
    total_pages = 1 # Na początek zakładamy jedną, zaktualizujemy po pierwszym strzale
    
    while page < total_pages:
        url = f"https://bdl.stat.gov.pl/api/v1/data/By-Variable/{var_id}?unit-level=5&page={page}&page-size=100"
        headers = {"X-ClientId": GUS_API_KEY} if GUS_API_KEY else {}
        #wysłanie zapytania o dane
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"Błąd API na stronie {page}: {response.status_code}")
            break

        data = response.json()
        
        # Przy pierwszym zapytaniu sprawdzamy, ile jest wszystkich stron i aktualizujemy 'total_pages'
        if page == 0:
            # Obliczamy ile stron przy 100 rekordach na stronę
            total_records = data.get('totalRecords', 0)
            total_pages = (total_records // 100) + 1
            print(f"Znaleziono {total_records} jednostek. Pobieranie {total_pages} stron...")

        for unit in data.get('results', []):    #pętla po powiatach  
            u_id = unit['id']
            u_name = unit['name']
            for v in unit.get('values', []):    #pętla po wartościach w powiecie
                results.append((
                    u_id, 
                    u_name, 
                    int(v['year']), 
                    QUARTER_MAP[str(var_id)], 
                    float(v['val'])
                ))
        
        page += 1
    return results


def save_to_neon(data):
    conn = psycopg2.connect(NEON_DATABASE_URL)
    cur = conn.cursor()
    
    query ="""
        INSERT INTO housing_data (unit_id, unit_name, year, quarter, value)
        VALUES %s
        ON CONFLICT (unit_id, year, quarter) 
        DO UPDATE SET value = EXCLUDED.value, unit_name = EXCLUDED.unit_name;
    """
    execute_values(cur, query, data)

    conn.commit()
    cur.close()
    conn.close()
    print(f"Zapisano {len(data)} rekordów.")



#3 --- URUCHOMIENIE ---
if __name__ == "__main__":
    init_db()
    
    for var_id in QUARTER_MAP.keys():   
        print(f"Pobieranie danych dla Q{QUARTER_MAP[var_id]}...")
        fetched_data = fetch_gus_data(var_id)
        if fetched_data:
            save_to_neon(fetched_data)
    
    print("Proces zakończony sukcesem!")