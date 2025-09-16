import requests
import gdown
import os
import zipfile
import tempfile
import shutil
import subprocess
import sys
from PyQt5.QtWidgets import QProgressDialog, QApplication, QMessageBox

APP_VERSION = "1.1"
METADATA_URL = "https://drive.google.com/uc?export=download&id=16bMHDzyZz6Zt2QvKYD0syv7SeyhvwgH1" 

def check_for_updates(parent=None):
    try:
        response = requests.get(METADATA_URL, timeout=10)
        if response.status_code != 200:
            QMessageBox.warning(parent, "განახლება", "შეცდომა განახლების შემოწმებისას.")
            return

        update_info = response.json()
        latest_version = update_info.get("latest_version")
        download_url = update_info.get("download_url")
        changelog = update_info.get("changelog", "")

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
            download_and_install(download_url, parent)

    except Exception as e:
        QMessageBox.warning(parent, "შეცდომა განახლებისას", str(e))



def download_and_install(download_url, parent=None):
    try:
        temp_dir = tempfile.gettempdir()
        zip_path = os.path.join(temp_dir, "GEM_Update.zip")

        # --- Progress dialog ---
        progress = QProgressDialog("საინსტალაციო ფაილის ჩამოტვირთვა...", "გაუქმება", 0, 0, parent)
        progress.setWindowTitle("განახლება")
        progress.setMinimumDuration(0)
        progress.setValue(0)
        progress.show()
        QApplication.processEvents()

        # --- Download using gdown ---
        gdown.download(download_url, zip_path, quiet=False)

        progress.setValue(100)
        progress.close()

        # --- Extract ZIP ---
        extract_dir = os.path.join(temp_dir, "GEM_Update")
        if os.path.exists(extract_dir):
            shutil.rmtree(extract_dir)
        os.makedirs(extract_dir, exist_ok=True)

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)

        # --- Run installer ---
        installer_exe = os.path.join(extract_dir, "GEM_1.2_setup.exe")
        if not os.path.exists(installer_exe):
            QMessageBox.warning(parent, "შეცდომა", "ინსტალატორი ვერ მოიძებნა ზიპ ფაილში.")
            return

        QMessageBox.information(parent, "განახლება", "საინსტალაციო ფაილი ჩამოტვირთულია და გაიხსნება...")
        subprocess.Popen([installer_exe])
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
