import requests
import os
import tempfile
import shutil
import subprocess
import sys
import zipfile
from PyQt5.QtWidgets import QProgressDialog, QApplication, QMessageBox

# ---------------- Configuration ----------------
APP_VERSION = "1.2" # Current app version
GITHUB_OWNER = "SabaBugi"   # 🔴 change this
GITHUB_REPO = "GEM"       # 🔴 change this

API_URL = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"

# ------------------------------------------------

def check_for_updates(parent=None):
    try:
        response = requests.get(API_URL, timeout=10)
        if response.status_code != 200:
            QMessageBox.warning(parent, "განახლება", "შეცდომა GitHub-ზე განახლების შემოწმებისას.")
            return

        release_info = response.json()
        latest_version = release_info.get("tag_name", "").lstrip("v")  # GitHub tags usually like v1.2
        changelog = release_info.get("body", "")

        # Find installer asset (.exe)
        assets = release_info.get("assets", [])
        installer_url = None
        installer_name = None
        for asset in assets:
            if asset["name"].endswith(".exe"):
                installer_url = asset["browser_download_url"]
                installer_name = asset["name"]
                break

        if not installer_url:
            QMessageBox.warning(parent, "განახლება", "ინსტალატორი ვერ მოიძებნა GitHub რელიზში.")
            return

        if latest_version == APP_VERSION:
            QMessageBox.information(parent, "განახლება", "თქვენ იყენებთ უახლეს ვერსიას.")
            return

        reply = show_wide_messagebox(
            parent,
            "ახალი ვერსია ხელმისაწვდომია",
            f"მიმდინარე ვერსია: {APP_VERSION}\n"
            f"ახალი ვერსია: {latest_version}\n\n"
            f"ცვლილებები:\n{changelog}\n\nგსურთ განახლება?",
            buttons=QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            download_and_install(installer_url, installer_name, parent)

    except Exception as e:
        QMessageBox.warning(parent, "შეცდომა განახლებისას", str(e))


def download_and_install(download_url, installer_name, parent=None):
    try:
        temp_dir = tempfile.gettempdir()
        installer_path = os.path.join(temp_dir, installer_name)

        # --- Progress dialog ---
        progress = QProgressDialog("საინსტალაციო ფაილის ჩამოტვირთვა...", "გაუქმება", 0, 0, parent)
        progress.setWindowTitle("განახლება")
        progress.setMinimumDuration(0)
        progress.setValue(0)
        progress.show()
        QApplication.processEvents()

        # --- Download installer ---
        with requests.get(download_url, stream=True) as r:
            r.raise_for_status()
            with open(installer_path, "wb") as f:
                shutil.copyfileobj(r.raw, f)

        progress.setValue(100)
        progress.close()

        # --- Run installer ---
        QMessageBox.information(parent, "განახლება", "საინსტალაციო ფაილი ჩამოტვირთულია და გაიხსნება...")
        subprocess.Popen([installer_path])
        sys.exit(0)

    except Exception as e:
        QMessageBox.warning(parent, "შეცდომა განახლებისას", str(e))


def show_wide_messagebox(parent, title, text, detailed_text=None, buttons=QMessageBox.Ok):
    msg = QMessageBox(parent)
    msg.setWindowTitle(title)
    msg.setText(text)
    if detailed_text:
        msg.setInformativeText(detailed_text)
    msg.setStandardButtons(buttons)
    msg.setStyleSheet("QLabel{min-width: 500px;}")
    return msg.exec_()
