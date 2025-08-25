import os
import pickle
import base64
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# --- CONFIGURATION ---

# The 'scopes' determine the permissions the app requests from the user.
# For this tool, we need full access to read from the source and insert into the destination.
SCOPES = ['https://mail.google.com/']
CREDENTIALS_FILE = 'credentials.json'

# --- FUNCTIONS ---

def get_gmail_service(token_file):
    """
    Authenticates with the Gmail API and returns a service object.
    Manages the OAuth 2.0 flow and stores the token for future use.
    """
    creds = None
    # The token file stores the user's access and refresh tokens.
    # It's created automatically on the first authorization.
    if os.path.exists(token_file):
        with open(token_file, 'rb') as token:
            creds = pickle.load(token)

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                print(f"ERROR: The file '{CREDENTIALS_FILE}' was not found.")
                print("Please follow the steps in README.md to create this file.")
                exit()
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        # Save the credentials for the next run
        with open(token_file, 'wb') as token:
            pickle.dump(creds, token)

    return build('gmail', 'v1', credentials=creds)

def migrate_emails(source_service, dest_service):
    """
    The core function that migrates emails from the source to the destination account.
    It fetches all emails from the source and inserts them into the destination.
    """
    try:
        # 1. Get the list of all message IDs from the source account
        print("\n▶️  Fetching list of all emails from the source account. This may take a moment...")
        source_messages = []
        page_token = None
        while True:
            response = source_service.users().messages().list(userId='me', pageToken=page_token).execute()
            source_messages.extend(response.get('messages', []))
            page_token = response.get('nextPageToken')
            if not page_token:
                break

        total_emails = len(source_messages)
        print(f"  Found {total_emails} emails to migrate.")

        # 2. Iterate through each message, get its raw content, and insert it into the destination
        for i, msg_info in enumerate(source_messages):
            msg_id = msg_info['id']
            print(f"\n  Migrating email {i + 1} of {total_emails} (ID: {msg_id})")

            try:
                # Get the raw email content, which includes headers, body, and attachments
                print("    1/2: Fetching raw email data...")
                message = source_service.users().messages().get(userId='me', id=msg_id, format='raw').execute()

                # The raw data is base64url encoded, which is what the insert method requires
                raw_email_data = {'raw': message['raw']}

                # Insert the email into the destination account
                print("    2/2: Inserting email into destination account...")
                dest_service.users().messages().insert(userId='me', body=raw_email_data).execute()

                # Optional: You could add 'labelIds': ['INBOX'] to the body if you want to ensure it lands in the inbox

                print(f"    ✅ Email {i + 1} migrated successfully.")

            except HttpError as error:
                print(f"    ❌ FOUT: An HTTP error occurred while migrating email ID {msg_id}: {error}")
            except Exception as e:
                print(f"    ❌ FOUT: A general error occurred while migrating email ID {msg_id}: {e}")

    except HttpError as error:
        print(f"❌ CRITICAL ERROR: Could not retrieve message list from source account. {error}")
    except Exception as e:
        print(f"❌ CRITICAL ERROR: An unexpected error occurred. {e}")

# --- MAIN PROGRAM ---

if __name__ == '__main__':
    print("--- Google Gmail Migration Tool ---")
    print("WARNING: Make sure 'credentials.json' is in the same directory as this script.")
    print("You will also need to enable the 'Gmail API' in your Google Cloud project.")

    print("\nStep 1: Authenticate the SOURCE account (where emails will be copied from).")
    source_token_file = 'gmail_token_source.json'
    source_gmail_service = get_gmail_service(source_token_file)
    print("✓ Authentication for source account successful.")

    print("\nStep 2: Authenticate the DESTINATION account (where emails will be copied to).")
    destination_token_file = 'gmail_token_destination.json'
    dest_gmail_service = get_gmail_service(destination_token_file)
    print("✓ Authentication for destination account successful.")

    print("\nAuthentication complete. Preparing the migration...")

    # Start the migration
    migrate_emails(source_gmail_service, dest_gmail_service)

    print("\n🎉 Migration complete!")
