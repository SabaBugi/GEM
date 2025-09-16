import sqlite3
import os
import re
import shutil
from PIL import Image

# -------------------------
# Database & Storage Setup
# -------------------------

# Base directory = current working directory (optional, not used here)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Main data folder
DOCS_DIR = r"C:\GEM DATABASE"
os.makedirs(DOCS_DIR, exist_ok=True)  # Ensure main folder exists

# Photos subfolder
PHOTOS_DIR = os.path.join(DOCS_DIR, "photos")
os.makedirs(PHOTOS_DIR, exist_ok=True)  # Ensure photos folder exists

# Database path
DB_NAME = os.path.join(DOCS_DIR, "GGMuseum.db")

# -------------------------
# Dropdown Options
# -------------------------

CATEGORIES = [
    "სხვა",
    "კერამიკა",
    "მეტალი",
    "ძვალი",
    "მინა",
    "ქვა",
    "ხე",
]

STATUS_OPTIONS = [
    "გამოფენილი",
    "საცავში",
    "გატანილია სარესტავრაციოდ",
]

# -------------------------
# Database Initialization
# -------------------------

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    # Artefacts table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS artefacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            artefact_code TEXT UNIQUE,
            name TEXT NOT NULL,
            category TEXT,
            origin TEXT,
            description TEXT,
            period TEXT,
            location TEXT,
            condition TEXT,
            status TEXT,
            curator TEXT,
            date_added DATE DEFAULT (DATE('now'))
        )
    """)

    # Images table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS artefact_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            artefact_id INTEGER,
            image_path TEXT,
            FOREIGN KEY (artefact_id) REFERENCES artefacts(id) ON DELETE CASCADE
        )
    """)

    conn.commit()
    conn.close()

# -------------------------
# Artefact Functions
# -------------------------

def add_artefact(artefact):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO artefacts 
        (artefact_code, name, category, origin, description, period, location, condition, status, curator) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, artefact)
    conn.commit()
    conn.close()

def get_artefacts():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT * FROM artefacts")
    rows = cur.fetchall()
    conn.close()
    return rows

def update_artefact(artefact_id, artefact):
    code = artefact[0]

    # Prevent duplicate codes
    if artefact_code_exists_for_other(code, artefact_id):
        raise ValueError(f"კოდი '{code}' უკვე გამოიყენება სხვა არტეფაქტში.")

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        UPDATE artefacts 
        SET artefact_code=?, name=?, category=?, origin=?, description=?, 
            period=?, location=?, condition=?, status=?, curator=? 
        WHERE id=?
    """, (*artefact, artefact_id))
    conn.commit()
    conn.close()

def delete_artefact(artefact_id):
    """Delete artefact and all its photos (DB + disk)."""
    photos = get_images(artefact_id)

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("DELETE FROM artefacts WHERE id=?", (artefact_id,))
    conn.commit()
    conn.close()

    for path in photos:
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception as e:
            print(f"⚠ Could not delete {path}: {e}")

def get_artefact_by_id(artefact_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT * FROM artefacts WHERE id=?", (artefact_id,))
    row = cur.fetchone()
    conn.close()
    return row

# -------------------------
# Image Functions
# -------------------------

def add_image(artefact_id, image_path):
    """
    Copy & compress the image into PHOTOS_DIR.
    Save with artefact_code-based name, avoid overwriting by suffix.
    Only the filename is stored in DB.
    """
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT artefact_code FROM artefacts WHERE id=?", (artefact_id,))
    result = cur.fetchone()
    conn.close()

    if not result:
        raise ValueError("Artefact not found in database")

    artefact_code = result[0]

    base_name = artefact_code
    dest_filename = f"{base_name}.jpg"
    dest_path = os.path.join(PHOTOS_DIR, dest_filename)

    counter = 1
    while os.path.exists(dest_path):
        dest_filename = f"{base_name}_{counter}.jpg"
        dest_path = os.path.join(PHOTOS_DIR, dest_filename)
        counter += 1

    try:
        img = Image.open(image_path)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        max_size = (1600, 1600)
        img.thumbnail(max_size, Image.Resampling.LANCZOS)

        img.save(dest_path, "JPEG", quality=70, optimize=True, progressive=True)

    except Exception as e:
        print(f"⚠ Image processing failed, copying original: {e}")
        shutil.copy2(image_path, dest_path)

    # Save only the filename in DB
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO artefact_images (artefact_id, image_path) VALUES (?, ?)",
        (artefact_id, dest_filename)
    )
    conn.commit()
    conn.close()

def get_images(artefact_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT image_path FROM artefact_images WHERE artefact_id=?", (artefact_id,))
    rows = [r[0] for r in cur.fetchall()]
    conn.close()

    # Convert filenames back to absolute paths
    full_paths = [os.path.join(PHOTOS_DIR, r) for r in rows]

    # Sort numerically by suffix
    def sort_key(p):
        name = os.path.splitext(os.path.basename(p))[0]
        parts = name.rsplit("_", 1)
        if len(parts) == 2 and parts[1].isdigit():
            return (parts[0], int(parts[1]))
        return (name, 0)

    full_paths.sort(key=sort_key)
    return full_paths

def delete_images(artefact_id):
    photos = get_images(artefact_id)

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("DELETE FROM artefact_images WHERE artefact_id=?", (artefact_id,))
    conn.commit()
    conn.close()

    for path in photos:
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception as e:
            print(f"⚠ Could not delete {path}: {e}")

# -------------------------
# Code Validation
# -------------------------

def artefact_code_exists(code):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM artefacts WHERE artefact_code=?", (code,))
    exists = cur.fetchone()[0] > 0
    conn.close()
    return exists

def artefact_code_exists_for_other(code, artefact_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) FROM artefacts WHERE artefact_code=? AND id<>?",
        (code, artefact_id),
    )
    exists = cur.fetchone()[0] > 0
    conn.close()
    return exists



