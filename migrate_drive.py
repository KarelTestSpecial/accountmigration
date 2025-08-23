import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# --- CONFIGURATIE ---

# De 'scopes' bepalen de permissies die de app aan de gebruiker vraagt.
# Voor deze tool hebben we volledige toegang tot Google Drive nodig.
SCOPES = ['https://www.googleapis.com/auth/drive']
CREDENTIALS_FILE = 'credentials.json'

# --- FUNCTIES ---

def get_drive_service(token_file):
    """
    Authenticeert met de Google Drive API en retourneert een service-object.
    Beheert de OAuth 2.0 flow en slaat de token op voor toekomstig gebruik.
    """
    creds = None
    # Het bestand token.pickle slaat de access en refresh tokens van de gebruiker op.
    # Het wordt automatisch aangemaakt bij de eerste keer autoriseren.
    if os.path.exists(token_file):
        with open(token_file, 'rb') as token:
            creds = pickle.load(token)

    # Als er geen (geldige) credentials zijn, laat de gebruiker inloggen.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                print(f"FOUT: Het bestand '{CREDENTIALS_FILE}' is niet gevonden.")
                print("Volg de stappen in README.md om dit bestand aan te maken.")
                exit()
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        # Sla de credentials op voor de volgende keer.
        with open(token_file, 'wb') as token:
            pickle.dump(creds, token)

    return build('drive', 'v3', credentials=creds)

def migrate_folders_and_files(source_service, dest_service):
    """
    De kernfunctie die de mappen en bestanden migreert.
    Het maakt gebruik van een recursieve hulpfunctie om de mappenstructuur te doorlopen.
    """
    folder_map = {'root': 'root'} # Houdt de mapping van source folder ID naar dest folder ID bij

    def recursively_copy(source_folder_id, dest_parent_id):
        page_token = None
        while True:
            try:
                # Haal een lijst op van bestanden en mappen in de huidige bronmap
                results = source_service.files().list(
                    q=f"'{source_folder_id}' in parents and trashed=false",
                    pageSize=200, # Max is 1000, maar lager is soms stabieler
                    fields="nextPageToken, files(id, name, mimeType)",
                    pageToken=page_token
                ).execute()

                items = results.get('files', [])

                for item in items:
                    item_name = item['name']
                    item_id = item['id']
                    item_mime_type = item['mimeType']

                    # Als het item een map is
                    if item_mime_type == 'application/vnd.google-apps.folder':
                        print(f"  📂 Map gevonden: {item_name}")
                        folder_metadata = {
                            'name': item_name,
                            'mimeType': 'application/vnd.google-apps.folder',
                            'parents': [dest_parent_id]
                        }

                        # Maak de map aan in de doel-drive
                        created_folder = dest_service.files().create(body=folder_metadata, fields='id').execute()
                        new_folder_id = created_folder.get('id')
                        print(f"    ✅ Map '{item_name}' aangemaakt in doel-drive.")

                        # Sla de mapping op en ga recursief verder
                        folder_map[item_id] = new_folder_id
                        recursively_copy(item_id, new_folder_id)

                    # Als het item een bestand is
                    else:
                        print(f"  📄 Bestand gevonden: {item_name}")
                        file_metadata = {
                            'name': item_name,
                            'parents': [dest_parent_id]
                        }

                        # Kopieer het bestand naar de doel-drive
                        dest_service.files().copy(
                            fileId=item_id,
                            body=file_metadata,
                            fields='id'
                        ).execute()
                        print(f"    ✅ Bestand '{item_name}' gekopieerd.")

                page_token = results.get('nextPageToken', None)
                if not page_token:
                    break

            except Exception as e:
                print(f" Fout opgetreden: {e}")
                print("   Opnieuw proberen...")
                continue

    print("\n▶️  Start van de migratie. Dit kan enige tijd duren, afhankelijk van de hoeveelheid data.")
    # Start het proces vanaf de root-map
    recursively_copy('root', 'root')

# --- HOOFDPROGRAMMA ---

if __name__ == '__main__':
    print("--- Google Drive Migratie Tool ---")
    print("WAARSCHUWING: Zorg ervoor dat 'credentials.json' in dezelfde map staat als dit script.")
    print("\nStap 1: Authenticatie voor het BRON-account (waar de bestanden vandaan komen).")

    # Authenticatie voor het bron-account
    source_token_file = 'token_source.json'
    source_drive_service = get_drive_service(source_token_file)
    print("✓ Authenticatie voor bron-account geslaagd.")

    print("\nStap 2: Authenticatie voor het DOEL-account (waar de bestanden naartoe gaan).")

    # Authenticatie voor het doel-account
    destination_token_file = 'token_destination.json'
    dest_drive_service = get_drive_service(destination_token_file)
    print("✓ Authenticatie voor doel-account geslaagd.")

    print("\nAuthenticatie voltooid. De migratie wordt voorbereid...")

    # Start de migratie
    migrate_folders_and_files(source_drive_service, dest_drive_service)

    print("\n🎉 Migratie voltooid!")
