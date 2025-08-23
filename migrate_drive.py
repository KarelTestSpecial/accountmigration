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

def migrate_folders_and_files(source_service, dest_service, dest_user_email):
    """
    De kernfunctie die de mappen en bestanden migreert.
    Het maakt gebruik van een recursieve hulpfunctie om de mappenstructuur te doorlopen.
    """
    print(f"\nDoelaccount e-mail: {dest_user_email}")
    folder_map = {'root': 'root'} # Houdt de mapping van source folder ID naar dest folder ID bij

    def recursively_copy(source_folder_id, dest_parent_id):
        page_token = None
        while True:
            try:
                # Haal een lijst op van bestanden en mappen in de huidige bronmap
                results = source_service.files().list(
                    q=f"'{source_folder_id}' in parents and trashed=false",
                    pageSize=200,
                    fields="nextPageToken, files(id, name, mimeType, capabilities)",
                    pageToken=page_token
                ).execute()

                items = results.get('files', [])

                for item in items:
                    item_id = item['id']
                    item_name = item['name']
                    item_mime_type = item['mimeType']
                    capabilities = item.get('capabilities', {})
                    can_share = capabilities.get('canShare', False)

                    # --- MAP VERWERKING ---
                    if item_mime_type == 'application/vnd.google-apps.folder':
                        try:
                            print(f"  📂 Map gevonden: {item_name}")
                            folder_metadata = {
                                'name': item_name,
                                'mimeType': 'application/vnd.google-apps.folder',
                                'parents': [dest_parent_id]
                            }
                            created_folder = dest_service.files().create(body=folder_metadata, fields='id').execute()
                            new_folder_id = created_folder.get('id')
                            print(f"    ✅ Map '{item_name}' aangemaakt in doel-drive.")
                            folder_map[item_id] = new_folder_id
                            recursively_copy(item_id, new_folder_id)
                        except Exception as e:
                            print(f"    ❌ FOUT bij verwerken van map '{item_name}'. Wordt overgeslagen. Fout: {e}")
                        continue # Ga verder met het volgende item in de lijst

                    # --- BESTANDSVERWERKING (SHARE-COPY-MOVE WORKFLOW) ---
                    print(f"  📄 Bestand gevonden: {item_name} ({item_mime_type})")
                    if not can_share:
                        print(f"    ⚠️ WAARSCHUWING: Bestand '{item_name}' kan niet worden gedeeld en wordt daarom overgeslagen.")
                        continue

                    permission_id = None
                    try:
                        # Stap 1: Deel het bestand met het doelaccount
                        print(f"    1/4: Bezig met delen van '{item_name}'...")
                        permission = {
                            'type': 'user',
                            'role': 'writer',
                            'emailAddress': dest_user_email
                        }
                        created_permission = source_service.permissions().create(
                            fileId=item_id,
                            body=permission,
                            sendNotificationEmail=False,
                            fields='id'
                        ).execute()
                        permission_id = created_permission.get('id')

                        # Stap 2: Kopieer het bestand met het doelaccount
                        print(f"    2/4: Bezig met kopiëren...")
                        copied_file = dest_service.files().copy(
                            fileId=item_id,
                            body={'name': item_name},
                            fields='id, parents'
                        ).execute()
                        copied_file_id = copied_file.get('id')
                        original_parents = copied_file.get('parents', [])

                        # Stap 3: Verplaats de kopie naar de juiste map
                        print(f"    3/4: Bezig met verplaatsen...")
                        dest_service.files().update(
                            fileId=copied_file_id,
                            addParents=dest_parent_id,
                            removeParents=','.join(original_parents) if original_parents else None,
                            fields='id, parents'
                        ).execute()

                        print(f"    ✅ Bestand '{item_name}' succesvol gemigreerd.")

                    except Exception as e:
                        print(f"    ❌ FOUT bij migreren van '{item_name}' (ID: {item_id}). Proces voor dit bestand afgebroken. Fout: {e}")
                        # De 'finally'-clausule zal de permissies opschonen

                    finally:
                        # Stap 4: Opschonen van de deelpermissie op het bronbestand
                        if permission_id:
                            try:
                                source_service.permissions().delete(
                                    fileId=item_id,
                                    permissionId=permission_id
                                ).execute()
                                print(f"    4/4: Tijdelijke deellink opgeschoond.")
                            except Exception as e:
                                print(f"    ⚠️ WAARSCHUWING: Kon deellink voor '{item_name}' niet opschonen. U kunt dit handmatig doen. Fout: {e}")

                page_token = results.get('nextPageToken', None)
                if not page_token:
                    break

            except Exception as e:
                print(f"    ❌ KRITISCHE FOUT bij ophalen van bestandenlijst. Kan niet doorgaan met deze map. Fout: {e}")
                break # Breek de while-loop af voor deze map

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

    # Haal het e-mailadres van het doelaccount op
    about_info = dest_drive_service.about().get(fields='user').execute()
    destination_user_email = about_info['user']['emailAddress']

    print("\nAuthenticatie voltooid. De migratie wordt voorbereid...")

    # Start de migratie
    migrate_folders_and_files(source_drive_service, dest_drive_service, destination_user_email)

    print("\n🎉 Migratie voltooid!")
