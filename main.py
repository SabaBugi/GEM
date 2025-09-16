import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTableWidget, QTableWidgetItem, QPushButton, QFileDialog,
    QVBoxLayout, QWidget, QLineEdit, QLabel, QHBoxLayout, QComboBox, QDialog, QHeaderView,
    QMessageBox
)
import sqlite3
import database
from artefact_form import ArtefactForm
from PyQt5.QtCore import Qt
from database import CATEGORIES, STATUS_OPTIONS, get_images, artefact_code_exists
from gallery import ImageGallery
from PyQt5.QtGui import QPixmap, QIcon
from users import LoginDialog, init_users_table, users_exist, create_first_admin, ManageUsersDialog
from users import ROLE_TRANSLATIONS
from backup import backup_database_and_photos, sync_from_drive
from exporter import export_to_excel, export_to_pdf
from updater import check_for_updates


class MainWindow(QMainWindow):
    def __init__(self, username, role):
        super().__init__()

        self.current_user_name = username
        self.current_user_role = role

        self.setWindowTitle("GEM - გრაკლიანის ექსპოზიციის მენეჯერი")
        self.resize(1350, 750)

        layout = QVBoxLayout()
        top_bar_layout = QHBoxLayout()

        # User info label on the top left
        display_role = ROLE_TRANSLATIONS.get(self.current_user_role, self.current_user_role)
        self.user_info_label = QLabel(f"მომხმარებელი: {self.current_user_name} ({display_role})")
        top_bar_layout.addWidget(self.user_info_label)

        # Spacer pushes the buttons to the right
        top_bar_layout.addStretch()

        # Search bar
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("არტეფაქტის ძებნა...")
        self.search_input.textChanged.connect(self.apply_filters)
        search_layout.addWidget(QLabel("ძებნა:"))
        search_layout.addWidget(self.search_input)

        # Filters
        self.category_filter = QComboBox()
        self.category_filter.addItem("ყველა კატეგორია")
        self.category_filter.addItems(CATEGORIES)
        self.category_filter.currentIndexChanged.connect(self.apply_filters)

        self.status_filter = QComboBox()
        self.status_filter.addItem("ყველა სტატუსი")
        self.status_filter.addItems(STATUS_OPTIONS)
        self.status_filter.currentIndexChanged.connect(self.apply_filters)

        search_layout.addWidget(QLabel("კატეგორია:"))
        search_layout.addWidget(self.category_filter)
        search_layout.addWidget(QLabel("სტატუსი:"))
        search_layout.addWidget(self.status_filter)

        layout.addLayout(search_layout)

        # Artefact table
        self.table = QTableWidget()
        layout.addWidget(self.table)
        self.table.cellDoubleClicked.connect(self.open_gallery)

        # Artefact buttons
        self.add_button = QPushButton("არტეფაქტის დამატება")
        self.edit_button = QPushButton("არტეფაქტის რედაქტირება")
        self.delete_button = QPushButton("არტეფაქტის წაშლა")
        self.clear_filters_button = QPushButton("ფილტრების გასუფთავება")

        self.add_button.clicked.connect(self.add_artefact)
        self.edit_button.clicked.connect(self.edit_artefact)
        self.delete_button.clicked.connect(self.delete_artefact)
        self.clear_filters_button.clicked.connect(self.clear_filters)

        layout.addWidget(self.add_button)
        layout.addWidget(self.edit_button)
        layout.addWidget(self.delete_button)
        layout.addWidget(self.clear_filters_button)

        # Disable buttons based on role
        if self.current_user_role == "viewer":
            self.add_button.setEnabled(False)
            self.edit_button.setEnabled(False)
            self.delete_button.setEnabled(False)

        # Admin-only: "Manage Users" + Backup/Sync
        if self.current_user_role == "admin":
            self.manage_users_button = QPushButton("მომხმარებლების მართვა")
            self.manage_users_button.clicked.connect(self.open_manage_users_dialog)
            top_bar_layout.addWidget(self.manage_users_button)

            self.backup_button = QPushButton("სარეზერვო ასლის შექმნა")
            self.backup_button.clicked.connect(self.backup_data)
            self.sync_button = QPushButton("სინქრონიზაცია")
            self.sync_button.clicked.connect(self.sync_data)
            top_bar_layout.addWidget(self.backup_button)
            top_bar_layout.addWidget(self.sync_button)


        # Export buttons (Excel, PDF) for admin and curator
        if self.current_user_role in ["admin", "curator"]:
            self.export_excel_btn = QPushButton("ექსპორტი Excel-ში")
            self.export_excel_btn.clicked.connect(self.export_excel)

            self.export_pdf_btn = QPushButton("ექსპორტი PDF-ში")
            self.export_pdf_btn.clicked.connect(self.export_pdf)

            layout.addWidget(self.export_excel_btn)
            layout.addWidget(self.export_pdf_btn)

        # Update button
        self.update_button = QPushButton("განახლების შემოწმება")
        self.update_button.clicked.connect(lambda: check_for_updates(self))
        top_bar_layout.addWidget(self.update_button)

        # Log out button
        self.logout_button = QPushButton("გამოსვლა")
        self.logout_button.clicked.connect(self.logout)
        top_bar_layout.addWidget(self.logout_button)

        layout.addLayout(top_bar_layout)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        # Load artefacts
        self.load_data()

    # ---------------- Artefacts ----------------
    def load_data(self):
        artefacts = database.get_artefacts()
        self.table.setRowCount(len(artefacts))
        self.table.setColumnCount(13)
        self.set_wrapped_headers()

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)

        for row_idx, row_data in enumerate(artefacts):
            for col_idx, value in enumerate(row_data):
                item = QTableWidgetItem(str(value))
                item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)  # read-only
                self.table.setItem(row_idx, col_idx, item)

            # Image preview
            images = get_images(row_data[0])
            if images and os.path.exists(images[0]):
                pixmap = QPixmap(images[0]).scaled(150, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                label = QLabel()
                label.setPixmap(pixmap)
                label.setAlignment(Qt.AlignCenter)
                self.table.setCellWidget(row_idx, 12, label)
                self.table.setRowHeight(row_idx, 160)
            else:
                placeholder = QPixmap("assets/placeholder.png").scaled(150, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                label = QLabel()
                label.setPixmap(placeholder)
                label.setAlignment(Qt.AlignCenter)
                self.table.setCellWidget(row_idx, 12, label)
                self.table.setRowHeight(row_idx, 160)


    def add_artefact(self):
        dialog = ArtefactForm()
        if dialog.exec_():
            artefact = list(dialog.get_data())
            images = artefact.pop()  # separate images
            artefact_code = artefact[0]

            if not artefact_code.strip():
                QMessageBox.warning(self, "გაფრთხილება", "გთხოვთ შეიყვანოთ კოდი არტეფაქტისთვის.")
                return

            # Check duplicate codes
            if database.artefact_code_exists(artefact_code):
                QMessageBox.warning(self, "გაფრთხილება", f"კოდი '{artefact_code}' უკვე გამოიყენება სხვა არტეფაქტში.")
                return

            database.add_artefact(artefact)
            new_id = database.get_artefacts()[-1][0]
            for img in images:
                database.add_image(new_id, img)
            self.load_data()

    def edit_artefact(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "გაფრთხილება", "აირჩიეთ არტეფაქტი რედაქტირებისთვის.")
            return

        artefact_id = int(self.table.item(row, 0).text())

        # Fetch full artefact row
        conn = sqlite3.connect(database.DB_NAME)
        cur = conn.cursor()
        cur.execute("""SELECT * FROM artefacts WHERE id=?""", (artefact_id,))
        artefact = cur.fetchone()
        conn.close()

        # Open form (form itself preloads images via get_images(artefact[0]))
        dialog = ArtefactForm(artefact)
        if dialog.exec_():
            updated = list(dialog.get_data())
            new_images = updated.pop()   # list of image paths returned by the form

            artefact_code = updated[0]
            if not artefact_code.strip():
                QMessageBox.warning(self, "გაფრთხილება", "გთხოვთ შეიყვანოთ კოდი არტეფაქტისთვის.")
                return

            try:
                database.update_artefact(artefact_id, updated)
            except ValueError as e:
                QMessageBox.warning(self, "შეცდომა", str(e))
                return

            # --- Sync images (safe: do NOT delete files automatically) ---
            # old_images: absolute paths currently referenced by DB
            old_images = database.get_images(artefact_id)  # returns full paths
            # new_images: absolute paths shown in the form (mix of PHOTOS_DIR paths for existing,
            # and original source paths for newly chosen files)
            old_filenames = {os.path.basename(p) for p in old_images}
            new_filenames = {os.path.basename(p) for p in new_images}

            # 1) Remove DB references for images user removed in the form (do NOT delete files)
            removed_filenames = old_filenames - new_filenames
            if removed_filenames:
                conn = sqlite3.connect(database.DB_NAME)
                cur = conn.cursor()
                for fn in removed_filenames:
                    cur.execute(
                        "DELETE FROM artefact_images WHERE artefact_id=? AND image_path=?",
                        (artefact_id, fn)
                    )
                conn.commit()
                conn.close()

            # 2) Add newly added images (copy/compress them into PHOTOS_DIR via database.add_image)
            #    (only add those whose basename wasn't already present in DB)
            added_paths = [p for p in new_images if os.path.basename(p) not in old_filenames]
            for src_path in added_paths:
                # sanity: only add if file exists
                if os.path.exists(src_path):
                    database.add_image(artefact_id, src_path)
                else:
                    # If the path isn't present on disk, try to see if it's already in PHOTOS_DIR
                    candidate = os.path.join(database.PHOTOS_DIR, os.path.basename(src_path))
                    if os.path.exists(candidate):
                        # insert DB reference for existing photo file (no copy)
                        conn = sqlite3.connect(database.DB_NAME)
                        cur = conn.cursor()
                        cur.execute(
                            "INSERT INTO artefact_images (artefact_id, image_path) VALUES (?, ?)",
                            (artefact_id, os.path.basename(candidate))
                        )
                        conn.commit()
                        conn.close()
                    else:
                        # file missing — warn in console (don't crash the app)
                        print(f"⚠ Skipping missing image: {src_path}")

            # 3) Finished — refresh UI
            self.load_data()


    def delete_artefact(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "გაფრთხილება", "აირჩიეთ წასაშლელი არტეფაქტი.")
            return

        artefact_id = int(self.table.item(row, 0).text())
        reply = QMessageBox.question(
            self, "წაშლის დადასტურება", "დარწმუნებული ხართ რომ გინდათ არტეფაქტის წაშლა?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            database.delete_artefact(artefact_id)
            self.load_data()

    # ---------------- Filters ----------------
    def apply_filters(self):
        search_text = self.search_input.text().lower()
        selected_category = self.category_filter.currentText()
        selected_status = self.status_filter.currentText()

        artefacts = database.get_artefacts()
        filtered = []

        for artefact in artefacts:
            searchable_text = " ".join(str(x).lower() for x in artefact[1:])
            if search_text and search_text not in searchable_text:
                continue
            if selected_category != "ყველა კატეგორია" and artefact[3] != selected_category:
                continue
            if selected_status != "ყველა სტატუსი" and artefact[9] != selected_status:
                continue
            filtered.append(artefact)

        self.table.setRowCount(0)
        
        for row_idx, artefact in enumerate(filtered):
            self.table.insertRow(row_idx)
            for col_idx, value in enumerate(artefact):
                item = QTableWidgetItem(str(value))
                item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)  # read-only
                self.table.setItem(row_idx, col_idx, item)


            # Image preview
            images = get_images(artefact[0])
            if images and os.path.exists(images[0]):
                pixmap = QPixmap(images[0]).scaled(150, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                label = QLabel()
                label.setPixmap(pixmap)
                label.setAlignment(Qt.AlignCenter)
                self.table.setCellWidget(row_idx, 12, label)
                self.table.setRowHeight(row_idx, 160)
            else:
                placeholder = QPixmap("assets/placeholder.png").scaled(150, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                label = QLabel()
                label.setPixmap(placeholder)
                label.setAlignment(Qt.AlignCenter)
                self.table.setCellWidget(row_idx, 12, label)
                self.table.setRowHeight(row_idx, 160)


    def clear_filters(self):
        self.search_input.clear()
        self.category_filter.setCurrentIndex(0)
        self.status_filter.setCurrentIndex(0)
        self.load_data()

    # ---------------- Other features ----------------
    def open_gallery(self, row, column):
        if column == 12:
            artefact_id = int(self.table.item(row, 0).text())
            gallery = ImageGallery(artefact_id)
            gallery.exec_()

    def open_manage_users_dialog(self):
        dialog = ManageUsersDialog()
        dialog.exec_()

    def logout(self):
        reply = QMessageBox.question(
            self, "გამოსვლა", "დარწმუნებული ხართ რომ გსურთ გამოსვლა?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.close()
            login = LoginDialog()
            if login.exec_() == QDialog.Accepted:
                new_window = MainWindow(login.username, login.user_role)
                new_window.showMaximized()
                app = QApplication.instance()
                app.main_window = new_window

    def backup_data(self):
        try:
            backup_database_and_photos()
            QMessageBox.information(self, "სარეზერვო ასლი", "სარეზერვო ასლი შექმნილია!")
        except Exception as e:
            QMessageBox.warning(self, "შეცდომა", str(e))

    def sync_data(self):
        """
        Full sync from Google Drive, overwriting all local files.
        """
        try:
            ok = sync_from_drive(overwrite_all=True)
            if ok:
                database.init_db()
                self.load_data()
                QMessageBox.information(self, "სინქრონიზაცია", "სინქრონიზაცია წარმატებით დასრულდა!")
            else:
                QMessageBox.warning(self, "სინქრონიზაცია", "სინქრონიზაცია გაუქმებულია.")
        except Exception as e:
            QMessageBox.warning(self, "შეცდომა", str(e))



    def set_wrapped_headers(self):
        raw = [
            "ID", "კოდი", "ნივთი", "კატეგორია", "აღმოჩენის ადგილი", "აღწერა",
            "პერიოდი", "მდებარეობა", "მდგომარეობა", "სტატუსი", "კურატორი",
            "დამატების თარიღი", "ფოტო"
        ]

        def wrap_label(text, max_len=12):
            words = text.split()
            if len("".join(words)) <= max_len:
                return text
            if len(words) == 1:
                mid = len(text) // 2
                return text[:mid] + "\n" + text[mid:]
            lines, line = [], ""
            for w in words:
                if not line:
                    line = w
                elif len(line) + 1 + len(w) <= max_len:
                    line += " " + w
                else:
                    lines.append(line)
                    line = w
            if line:
                lines.append(line)
            return "\n".join(lines)

        labels = [wrap_label(t) for t in raw]
        self.table.setHorizontalHeaderLabels(labels)
        header = self.table.horizontalHeader()
        header.setDefaultAlignment(Qt.AlignCenter)
        header.setSectionResizeMode(QHeaderView.Stretch)
        header.setFixedHeight(60)

    def export_excel(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Excel", "", "Excel Files (*.xlsx)")
        if path:
            export_to_excel(path)
            QMessageBox.information(self, "ექსპორტი", f"✅ ექსპორტი წარმატებით განხორციელდა {path}")

    def export_pdf(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save PDF", "", "PDF Files (*.pdf)")
        if path:
            export_to_pdf(path)
            QMessageBox.information(self, "ექსპორტი", f"✅ PDF ექსპორტი წარმატებით განხორციელდა {path}")



if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("assets/GEM_logo.png"))

    database.init_db()
    init_users_table()

    if not users_exist():
        created = create_first_admin()
        if not created:
            sys.exit(0)

    login = LoginDialog()
    if login.exec_() == QDialog.Accepted:
        app.main_window = MainWindow(login.username, login.user_role)
        app.main_window.showMaximized()
        sys.exit(app.exec_())
