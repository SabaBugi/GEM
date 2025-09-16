import os
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from database import DB_NAME, PHOTOS_DIR, DOCS_DIR

# -------------------------
# Paths
# -------------------------
APP_DIR = os.path.dirname(os.path.abspath(__file__))  # app installation directory
TOKEN_PATH = os.path.join(DOCS_DIR, "REMOVED")     # user-specific token
SETTINGS_PATH = os.path.join(APP_DIR, "REMOVED")  # shipped with app

# Backup folders in Google Drive
BACKUP_ROOT = "GGMuseum_Backup"
DB_FOLDER = "Database"
PHOTOS_FOLDER = "Photos"


def authenticate_drive():
    """Authenticate and return a GoogleDrive instance."""
    gauth = GoogleAuth(SETTINGS_PATH)

    # Always load user token from Documents folder
    if os.path.exists(TOKEN_PATH):
        try:
            gauth.LoadCredentialsFile(TOKEN_PATH)
        except Exception as e:
            print(f"⚠️ Failed to load REMOVED: {e}")
            gauth.credentials = None

    # If no credentials or invalid
    if gauth.credentials is None:
        print("🔑 First-time login or token missing → opening browser...")
        gauth.LocalWebserverAuth()
    elif gauth.access_token_expired:
        try:
            gauth.Refresh()
        except Exception as e:
            print(f"⚠️ Refresh failed: {e}, retrying full login...")
            gauth.LocalWebserverAuth()
    else:
        try:
            gauth.Authorize()
        except Exception as e:
            print(f"⚠️ Authorization failed: {e}, retrying full login...")
            gauth.LocalWebserverAuth()

    # Save back to Documents folder
    try:
        gauth.SaveCredentialsFile(TOKEN_PATH)
    except Exception as e:
        print(f"⚠️ Could not save REMOVED: {e}")

    return GoogleDrive(gauth)



def get_folder_id(drive, name, parent_id=None):
    """Find a folder ID by name (returns None if not found)."""
    query = f"title='{name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    if parent_id:
        query += f" and '{parent_id}' in parents"
    file_list = drive.ListFile({"q": query}).GetList()
    return file_list[0]["id"] if file_list else None


def get_or_create_folder(drive, name, parent_id=None):
    """Find or create a folder by name."""
    folder_id = get_folder_id(drive, name, parent_id)
    if folder_id:
        return folder_id
    metadata = {"title": name, "mimeType": "application/vnd.google-apps.folder"}
    if parent_id:
        metadata["parents"] = [{"id": parent_id}]
    folder = drive.CreateFile(metadata)
    folder.Upload()
    return folder["id"]


def upload_file(drive, folder_id, local_path):
    filename = os.path.basename(local_path)
    query = f"title='{filename}' and '{folder_id}' in parents and trashed=false"
    file_list = drive.ListFile({"q": query}).GetList()
    if file_list:
        file = file_list[0]
        file.SetContentFile(local_path)
        file.Upload()
        print(f"🔄 Updated {filename}")
    else:
        file = drive.CreateFile({"title": filename, "parents": [{"id": folder_id}]} )
        file.SetContentFile(local_path)
        file.Upload()
        print(f"✅ Uploaded {filename}")


def download_file(drive, file_obj, local_path):
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    file_obj.GetContentFile(local_path)
    print(f"⬇️ Downloaded {file_obj['title']} → {local_path}")


def backup_database_and_photos():
    drive = authenticate_drive()
    root_id = get_or_create_folder(drive, BACKUP_ROOT)
    db_folder_id = get_or_create_folder(drive, DB_FOLDER, root_id)
    photos_folder_id = get_or_create_folder(drive, PHOTOS_FOLDER, root_id)

    # Backup DB
    upload_file(drive, db_folder_id, DB_NAME)

    # Backup photos
    for root, _, files in os.walk(PHOTOS_DIR):
        for file in files:
            local_path = os.path.join(root, file)
            upload_file(drive, photos_folder_id, local_path)

    print("✅ Backup complete.")


def sync_from_drive(overwrite_all=True):
    drive = authenticate_drive()
    root_id = get_folder_id(drive, BACKUP_ROOT)
    if not root_id:
        print("❌ Backup folder not found on Google Drive.")
        return False

    db_folder_id = get_folder_id(drive, DB_FOLDER, root_id)
    photos_folder_id = get_folder_id(drive, PHOTOS_FOLDER, root_id)

    # --- Database restore ---
    if db_folder_id:
        files = drive.ListFile({"q": f"'{db_folder_id}' in parents and trashed=false"}).GetList()
        for f in files:
            if f["title"] == os.path.basename(DB_NAME):
                local_path = DB_NAME
                download_file(drive, f, local_path)

    # --- Photos restore ---
    if photos_folder_id:
        files = drive.ListFile({"q": f"'{photos_folder_id}' in parents and trashed=false"}).GetList()
        for f in files:
            local_path = os.path.join(PHOTOS_DIR, f["title"])
            download_file(drive, f, local_path)

    print("✅ Full sync complete.")
    return True
