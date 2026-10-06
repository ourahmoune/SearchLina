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
# ✅ Plus de recherche par nom de ville via autocomplétion : chaque entrée est
# l'URL complète (avec bounds + locationName) qui pointe directement sur les
# résultats de la zone souhaitée.
#
# Pour ajouter une ville :
#   1. Va sur https://trouverunlogement.lescrous.fr/tools/47/search
#   2. Fais la recherche manuellement dans un navigateur (tape la ville, clique le résultat)
#   3. Une fois les résultats affichés, copie l'URL complète dans la barre d'adresse
#   4. Colle-la ci-dessous avec un nom de ton choix comme clé
RECHERCHES = {
    # "Tulle": "https://trouverunlogement.lescrous.fr/tools/47/search?bounds=1.7227855_45.2977832_1.809914_45.2392163&locationName=Tulle+%2819000%29",
    "Orsay": "https://trouverunlogement.lescrous.fr/tools/47/search?bounds=2.1695755_48.7188772_2.209699_48.6755091&locationName=Orsay+%2891400%29",
    # "Poitiers": "https://trouverunlogement.lescrous.fr/tools/47/search?bounds=...&locationName=Poitiers...",
}

EMAIL = os.getenv("EMAIL")
MOT_DE_PASSE_APP = os.getenv("MOT_DE_PASSE_APP")

SEEN_FILE = "seen.json"
DEBUG = True  # ✅ Mets à False une fois que ça fonctionne pour arrêter les captures
# ==========================================


def generate_offer_id(title, address, price, link):
    """Génère un ID stable basé sur l'URL de l'offre"""
    offer_url_id = re.search(r'/offer/(\d+)', link)
    if offer_url_id:
        return f"offer_{offer_url_id.group(1)}"
    else:
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
    msg["Subject"] = f"🔥 {len(new_offers)} NOUVELLE(S) OFFRE(S) CROUS ! 🔥"
    msg["From"] = EMAIL
    msg["To"] = "aminamansouur@gmail.com"

    body = f"🚨 ALERTE LOGEMENT ! 🚨\n\n"
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


async def close_cookie_banner(page):
    """Ferme le bandeau de consentement cookies s'il est présent"""
    try:
        selectors = [
            "button:has-text('Tout accepter')",
            "button:has-text('Accepter tout')",
            "button:has-text('Accepter')",
            "#tarteaucitronPersonalize2",
            "button[id*='accept' i]",
            "button[class*='accept' i]",
        ]
        for sel in selectors:
            btn = page.locator(sel)
            if await btn.count() > 0:
                await btn.first.click(timeout=3000)
                print(f"🍪 Bandeau cookies fermé via: {sel}")
                await page.wait_for_timeout(1000)
                return True
        return False
    except Exception as e:
        print(f"ℹ️ Gestion cookies: {e}")
        return False


async def debug_dump(page, nom):
    """Sauvegarde screenshot + HTML pour inspection si DEBUG=True"""
    if not DEBUG:
        return
    try:
        safe_name = re.sub(r'\W+', '_', nom)
        await page.screenshot(path=f"debug_{safe_name}.png", full_page=True)
        html_debug = await page.content()
        with open(f"debug_{safe_name}.html", "w", encoding="utf-8") as f:
            f.write(html_debug)
        print(f"🖼️ debug_{safe_name}.png / .html sauvegardés")
    except Exception as e:
        print(f"⚠️ Échec debug_dump: {e}")


async def goto_with_retry(page, url, attempts=3, timeout=45000):
    """Tente de charger l'URL plusieurs fois en cas de timeout/instabilité réseau"""
    last_exc = None
    for attempt in range(1, attempts + 1):
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
            return
        except Exception as e:
            last_exc = e
            print(f"⚠️ Tentative {attempt}/{attempts} échouée pour le chargement: {e}")
            await page.wait_for_timeout(3000)
    raise last_exc


async def fetch_recherche(page, nom, url):
    """Charge directement l'URL de recherche (bounds + locationName déjà encodés dans l'URL)"""
    print(f"🌐 Connexion à {url}")
    await goto_with_retry(page, url, attempts=3, timeout=45000)
    await page.wait_for_timeout(3000)

    await close_cookie_banner(page)

    # ✅ Attend l'apparition des cartes de résultats (silencieux si 0 résultat)
    try:
        await page.wait_for_selector(".fr-card", timeout=10000)
    except Exception:
        print(f"ℹ️ Pas de carte détectée immédiatement pour {nom} (probablement 0 résultat)")

    await page.wait_for_timeout(2000)

    html = await page.content()
    await debug_dump(page, nom)
    return html


async def check_offers():
    """Vérifie les nouvelles offres CROUS pour chaque recherche définie dans RECHERCHES"""
    print("="*70)
    print(f"🔍 Vérification {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"📧 Email configuré : {EMAIL if EMAIL else '❌ MANQUANT'}")
    print(f"🏙️  Recherches surveillées : {', '.join(RECHERCHES.keys())}")
    print("="*70)

    seen = load_seen()
    initial_count = len(seen)

    new_found = []
    current_offers = set()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        page = await browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="fr-FR",
        )
        await page.set_extra_http_headers({"Accept-Language": "fr-FR,fr;q=0.9"})

        for nom, url in RECHERCHES.items():
            print("-"*70)
            print(f"📍 Recherche en cours : {nom}")
            try:
                html = await fetch_recherche(page, nom, url)
                soup = BeautifulSoup(html, "html.parser")

                results_text = soup.get_text()
                if "0 logement" in results_text or "Aucun logement" in results_text:
                    print(f"📭 Aucun logement disponible pour {nom}")
                    continue

                cards = soup.select(".fr-card")
                print(f"🏠 {len(cards)} logement(s) trouvé(s) pour {nom}")

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

                        offer_id = generate_offer_id(title, address, price, link)
                        current_offers.add(offer_id)

                        if offer_id not in seen:
                            print(f"🆕 NOUVELLE OFFRE #{i} ({nom}): {title}")
                            print(f"   ID: {offer_id}")

                            details = card.select(".fr-card__detail")
                            details_text = [d.get_text(strip=True) for d in details]

                            offer_text = f"""🏙️ Recherche : {nom}
🏠 {title}
📍 {address}
💰 {price}
🔗 {link}
📝 {' | '.join(details_text)}"""

                            new_found.append(offer_text)
                            seen.add(offer_id)
                        else:
                            print(f"✅ Offre #{i} déjà connue: {title} (ID: {offer_id})")

            except Exception as e:
                print(f"❌ Erreur pour la recherche {nom}: {e}")
                import traceback
                traceback.print_exc()

        await browser.close()

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
