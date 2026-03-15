import requests
from bs4 import BeautifulSoup
import os
import time

# Fișierul unde salvăm datele combinate
OUTPUT_FILE = "scraped_knowledge.txt"

def scrape_safety_info():
    print("--- Starting MULTI-SOURCE Web Scraping Process ---")
    
    # LISTA DE SURSE (Site-uri de încredere)
    sources = [
        {
            "name": "NCBI - Domestic Violence Overview",
            "url": "https://www.ncbi.nlm.nih.gov/books/NBK499891/"
        },
        {
            "name": "The Hotline - Identify Abuse",
            "url": "https://www.thehotline.org/identify-abuse/"
        },
        {
            "name": "World Health Organization (WHO) - Violence against women",
            "url": "https://www.who.int/news-room/fact-sheets/detail/violence-against-women"
        }
    ]
    
    # Headers ca să părem un browser real (Chrome)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    # Variabila care va ține tot textul
    combined_knowledge = "=== AGGREGATED SAFETY KNOWLEDGE BASE ===\n\n"
    
    for source in sources:
        print(f"🌍 Scraping: {source['name']}...")
        
        try:
            response = requests.get(source['url'], headers=headers, timeout=10)
            
            if response.status_code != 200:
                print(f"   ❌ Failed to access {source['url']} (Code: {response.status_code})")
                continue # Trecem la următorul site

            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Adăugăm un titlu pentru fiecare sursă în fișier
            combined_knowledge += f"\n\n--- SOURCE: {source['name']} ---\n"
            combined_knowledge += f"URL: {source['url']}\n"
            combined_knowledge += "-" * 40 + "\n"
            
            # Extragem paragrafele <p> și titlurile <h2>, <h3> pentru context
            content_blocks = soup.find_all(['p', 'h2', 'h3'])
            
            paragraphs_collected = 0
            
            for block in content_blocks:
                text = block.get_text().strip()
                
                # Reguli de curățare (Cleaning Data)
                # 1. Ignorăm textele prea scurte (meniuri, linkuri)
                # 2. Ignorăm cuvinte specifice de subsol/cookie
                if len(text) > 60 and "cookie" not in text.lower() and "copyright" not in text.lower():
                    combined_knowledge += text + "\n\n"
                    paragraphs_collected += 1
                    
                    # Limită per site ca să nu avem prea mult text (ex: 40 de paragrafe per site)
                    if paragraphs_collected >= 40:
                        combined_knowledge += "[...Limit reached for this source...]\n"
                        break
            
            print(f"   ✅ Successfully extracted {paragraphs_collected} blocks of text.")
            
            # Pauză mică între cereri ca să fim politicoși cu serverele
            time.sleep(1)

        except Exception as e:
            print(f"   ❌ Error scraping {source['name']}: {e}")

    # --- SALVAREA FINALĂ ---
    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(combined_knowledge)
        print("\n============================================")
        print(f"🎉 DONE! All data saved to '{OUTPUT_FILE}'.")
        print("You can now run 'app.py'.")
        print("============================================")
    except Exception as e:
        print(f"❌ Error saving file: {e}")

if __name__ == "__main__":
    scrape_safety_info()