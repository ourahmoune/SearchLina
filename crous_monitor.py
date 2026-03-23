from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import json
import smtplib
from email.message import EmailMessage
from datetime import datetime
import os
import asyncio
import hashlib
import re

# ================= CONFIG =================
VILLE = "Niort"
URL = "https://trouverunlogement.lescrous.fr/tools/42/search"

EMAIL = os.getenv("EMAIL")
MOT_DE_PASSE_APP = os.getenv("MOT_DE_PASSE_APP")

SEEN_FILE = "seen.json"
# ==========================================


def generate_offer_id(title, address, price, link):
    """Génère un ID stable basé sur l'URL de l'offre"""
    # Extraire l'ID de l'offre depuis l'URL
    # Ex: /tools/42/offer/12345 → utilise 12345
    offer_url_id = re.search(r'/offer/(\d+)', link)
    if offer_url_id:
        # ✅ Utilise l'ID de l'URL (unique par annonce)
        return f"offer_{offer_url_id.group(1)}"
    else:
        # Fallback : hash des infos
        unique_string = f"{title}|{address}|{price}|{link}"
        return hashlib.md5(unique_string.encode()).hexdigest()


def load_seen():
    """Charge l'historique des offres déjà vues"""
    try:
        with open(SEEN_FILE, "r") as f:
            data = json.load(f)
            print(f"📂 {len(data)} offre(s) déjà en historique")
            return set(data)
    except Exception as e:
        print(f"📝 Création nouvel historique ({e})")
        return set()


def save_seen(seen):
    """Sauvegarde l'historique des offres vues"""
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen), f, indent=2)


def send_email(new_offers):
    """Envoie un email avec les nouvelles offres"""
    if not EMAIL or not MOT_DE_PASSE_APP:
        print("⚠️ Credentials email manquants")
        return False
        
    msg = EmailMessage()
    msg["Subject"] = f"🔥 {len(new_offers)} NOUVELLE(S) OFFRE(S) CROUS NIORT ! 🔥"
    msg["From"] = EMAIL
    msg["To"] = "djoumace07@gmail.com"

    body = f"🚨 ALERTE LOGEMENT NIORT ! 🚨\n\n"
    body += f"📅 {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n\n"
    body += "⚡ POSTULE VITE, ÇA VA PARTIR RAPIDEMENT !\n\n"
    body += "="*70 + "\n\n"
    body += ("\n" + "="*70 + "\n\n").join(new_offers)
    
    msg.set_content(body)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL, MOT_DE_PASSE_APP)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"❌ Erreur email: {e}")
        return False


async def check_offers():
    """Vérifie les nouvelles offres CROUS"""
    print("="*70)
    print(f"🔍 Vérification {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"📧 Email configuré : {EMAIL if EMAIL else '❌ MANQUANT'}")
    print("="*70)
    
    seen = load_seen()
    initial_count = len(seen)
    
    new_found = []
    current_offers = set()  # ✅ IDs des offres actuellement en ligne

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            print(f"🌐 Connexion à {URL} ")
            await page.goto(URL, wait_until="domcontentloaded")
            await page.wait_for_timeout(2000)

            input_selector = "#PlaceAutocompletearia-autocomplete-1-input"
            await page.wait_for_selector(input_selector, state="visible", timeout=10000)
            await page.click(input_selector)
            await page.wait_for_timeout(300)
            
            print(f"🔎 Recherche de '{VILLE}'...")
            await page.fill(input_selector, "")
            await page.type(input_selector, VILLE, delay=100)
            await page.wait_for_timeout(1500)

            list_selector = "#PlaceAutocompletearia-autocomplete-1-list"
            try:
                await page.wait_for_function(
                    f"document.querySelector('{list_selector}').classList.contains('PlaceAutocomplete__list--has-results')",
                    timeout=5000
                )
                
                option_selector = f"li.PlaceAutocomplete__option:has-text('{VILLE}')"
                await page.wait_for_selector(option_selector, state="visible", timeout=5000)
                await page.click(option_selector, force=True)
            except:
                await page.keyboard.press("Enter")
            
            await page.wait_for_timeout(4000)
            
            soup = BeautifulSoup(await page.content(), "html.parser")
            
            results_text = soup.get_text()
            if "0 logement" in results_text or "Aucun logement" in results_text:
                print("📭 Aucun logement disponible à Niort")
            else:
                cards = soup.select(".fr-card")
                print(f"🏠 {len(cards)} logement(s) trouvé(s) sur le site")
                
                for i, card in enumerate(cards, 1):
                    title_elem = card.select_one(".fr-card__title a")
                    desc_elem = card.select_one(".fr-card__desc")
                    price_elem = card.select_one(".fr-badge")
                    link_elem = card.select_one(".fr-card__title a")
                    
                    if title_elem and desc_elem and price_elem:
                        title = title_elem.get_text(strip=True)
                        address = desc_elem.get_text(strip=True)
                        price = price_elem.get_text(strip=True)
                        link = "https://trouverunlogement.lescrous.fr" + link_elem.get("href", "")
                        print(f" Link est  : {link} ")
                        
                        # ✅ Créer un ID basé sur l'URL de l'offre
                        offer_id = generate_offer_id(title, address, price, link)
                        current_offers.add(offer_id)
                        
                        # ✅ Vérifier si déjà vu
                        if offer_id not in seen:
                            print(f"🆕 NOUVELLE OFFRE #{i}: {title}")
                            print(f"   ID: {offer_id}")
                            
                            details = card.select(".fr-card__detail")
                            details_text = [d.get_text(strip=True) for d in details]
                            
                            offer_text = f"""🏠 {title}
📍 {address}
💰 {price}
🔗 {link}
📝 {' | '.join(details_text)}"""
                            
                            new_found.append(offer_text)
                            seen.add(offer_id)
                        else:
                            print(f"✅ Offre #{i} déjà connue: {title} (ID: {offer_id})")

        except Exception as e:
            print(f"❌ Erreur: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await browser.close()

    # ✅ NETTOYAGE : Retire de seen les offres qui ne sont plus en ligne
    # Cela permet de détecter les réapparitions
    removed_offers = seen - current_offers
    if removed_offers:
        print(f"🗑️  {len(removed_offers)} offre(s) disparue(s) du site (retirées de l'historique)")
        seen = current_offers.union(seen.intersection(current_offers))
    
    save_seen(seen)
    
    print("="*70)
    print(f"📊 STATISTIQUES :")
    print(f"   • Offres actuellement en ligne : {len(current_offers)}")
    print(f"   • Offres en historique          : {len(seen)} (avant: {initial_count})")
    print(f"   • Nouvelles offres détectées    : {len(new_found)}")
    print(f"   • Offres disparues              : {len(removed_offers)}")
    print("="*70)

    if new_found:
        print(f"🚨 {len(new_found)} NOUVELLE(S) OFFRE(S) !")
        print("📧 Envoi de l'email...")
        if send_email(new_found):
            print("✅ Email envoyé !")
        else:
            print("❌ Échec envoi email")
    else:
        print("✅ Aucune nouvelle offre - surveillance continue")
    
    print("="*70)


if __name__ == '__main__':
    asyncio.run(check_offers())