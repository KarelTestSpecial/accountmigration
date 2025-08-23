# Google Drive Migratie Tool

Deze tool is ontworpen om de volledige inhoud (mappen en bestanden) van het ene Google Drive-account naar het andere te migreren, met behoud van de oorspronkelijke mappenstructuur.

## Waarschuwing

Deze tool kopieert bestanden en mappen. Het synchroniseert geen wijzigingen en verwijdert niets uit het bron- of doelaccount. Gebruik op eigen risico.

## Vereisten

1.  Python 3.6+
2.  Een `credentials.json` bestand van Google Cloud. Volg de onderstaande stappen om dit bestand te verkrijgen.

---

## Stap 1: Verkrijg `credentials.json` van Google

Voordat u deze tool kunt gebruiken, moet u Google toestemming geven om namens u te handelen. Dit doet u door een `credentials.json` bestand aan te maken. Volg deze stappen zorgvuldig:

1.  **Ga naar de Google Cloud Console:**
    *   Open [https://console.cloud.google.com/](https://console.cloud.google.com/) en log in met een Google-account. Het maakt niet uit welk account u hier gebruikt, het is alleen voor het beheer van de API-toegang.

2.  **Maak een nieuw project aan:**
    *   Klik bovenaan op de projectkiezer (naast het "Google Cloud Platform"-logo) en klik op **"NIEUW PROJECT"**.
    *   Geef het een duidelijke naam (bijv. "Drive Migratie Tool") en klik op **"MAKEN"**.

3.  **Schakel de Google Drive API in:**
    *   Zorg ervoor dat uw nieuwe project is geselecteerd.
    *   Ga in het linkermenu naar **"API's en services"** > **"Bibliotheek"**.
    *   Zoek naar **"Google Drive API"** en klik erop.
    *   Klik op de knop **"INSCHAKELEN"**.

4.  **Configureer het OAuth-toestemmingsscherm:**
    *   Ga in het linkermenu naar **"API's en services"** > **"OAuth-toestemmingsscherm"**.
    *   Kies **"Extern"** als gebruikerstype en klik op **"MAKEN"**.
    *   Vul de verplichte velden in:
        *   **App-naam:** Geef het een naam (bijv. "Mijn Drive Migratie Script").
        *   **E-mailadres voor gebruikersondersteuning:** Kies uw e-mailadres.
        *   **Contactgegevens van ontwikkelaar:** Vul uw e-mailadres opnieuw in.
    *   Klik op **"OPSLAAN EN DOORGAAN"** bij de volgende secties (Scopes, Testgebruikers). U hoeft hier niets toe te voegen.
    *   Ga terug naar het dashboard van het OAuth-toestemmingsscherm. Klik op **"APP PUBLICEREN"** en bevestig. Dit is nodig om te voorkomen dat uw authenticatie elke 7 dagen verloopt.

5.  **Maak OAuth 2.0-inloggegevens aan:**
    *   Ga in het linkermenu naar **"API's en services"** > **"Inloggegevens"**.
    *   Klik bovenaan op **"+ INLOGGEGEVENS MAKEN"** en kies **"OAuth-client-ID"**.
    *   Kies bij **"App-type"** voor **"Desktop-app"**.
    *   Geef het een naam (bijv. "Desktop Client 1").
    *   Klik op **"MAKEN"**.

6.  **Download het `credentials.json` bestand:**
    *   Er verschijnt een pop-up met uw client-ID en -geheim. Klik op **"JSON DOWNLOADEN"**.
    *   Hernoem het gedownloade bestand naar `credentials.json` en plaats het in dezelfde map als waar u dit script zult uitvoeren.

---

## Stap 2: Installeer de vereiste bibliotheken

Open een terminal of opdrachtprompt en voer het volgende commando uit in de projectmap:

```bash
pip install -r requirements.txt
```

## Stap 3: Voer de migratietool uit

Zodra de installatie is voltooid en uw `credentials.json` in de juiste map staat, voert u het script uit:

```bash
python migrate_drive.py
```

De tool zal u eerst vragen om in te loggen op het **bronaccount** (het account waarvan u wilt kopiëren) en vervolgens op het **doelaccount** (het account waarnaar u wilt kopiëren). Volg de instructies in de terminal. Er wordt een browservenster geopend waarin u toestemming moet geven.
