import sqlite3
import os
import bcrypt
from PyQt5.QtWidgets import (
    QDialog, QFormLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QHeaderView, 
    QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QComboBox, QInputDialog
)
from PyQt5.QtCore import Qt


# ----------------------
# Users database
# ----------------------
APP_DIR = os.path.dirname(os.path.abspath(__file__))
USERS_DB = os.path.join(APP_DIR, "users.db")

# ----------------------
# Role translations
# ----------------------
ROLE_TRANSLATIONS = {
    "admin": "ადმინისტრატორი",
    "curator": "კურატორი",
    "viewer": "დამთვალიერებელი"
}
ROLE_REVERSE = {v: k for k, v in ROLE_TRANSLATIONS.items()}


# ----------------------
# Database functions
# ----------------------
def init_users_table():
    conn = sqlite3.connect(USERS_DB)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash BLOB NOT NULL,
            role TEXT NOT NULL DEFAULT 'viewer',
            created_at DATE DEFAULT (DATE('now'))
        )
    """)
    conn.commit()
    conn.close()


def users_exist():
    conn = sqlite3.connect(USERS_DB)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users")
    count = cur.fetchone()[0]
    conn.close()
    return count > 0


def create_first_admin():
    """Prompt to create the first admin user if none exist (role fixed to admin)."""
    dlg = NewUserDialog(force_admin=True)
    if dlg.exec_() == QDialog.Accepted:
        username, password, role = dlg.get_data()
        add_user(username, password, role)
        QMessageBox.information(None, "წარმატება", f"ადმინისტრატორი '{username}' წარმატებით შეიქმნა!")
        return True
    return False


def add_user(username, password, role="viewer"):
    conn = sqlite3.connect(USERS_DB)
    cur = conn.cursor()
    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    try:
        cur.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                    (username, password_hash, role))
        conn.commit()
    except sqlite3.IntegrityError:
        QMessageBox.warning(None, "შეცდომა", f"მომხმარებელი '{username}' უკვე არსებობს.")
    conn.close()


def get_user(username):
    conn = sqlite3.connect(USERS_DB)
    cur = conn.cursor()
    cur.execute("SELECT id, username, password_hash, role FROM users WHERE username=?", (username,))
    row = cur.fetchone()
    conn.close()
    return row


def list_users():
    conn = sqlite3.connect(USERS_DB)
    cur = conn.cursor()
    cur.execute("SELECT id, username, role, created_at FROM users ORDER BY id")
    rows = cur.fetchall()
    conn.close()
    return rows


def delete_user(user_id):
    conn = sqlite3.connect(USERS_DB)
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    conn.close()


# ----------------------
# Custom New User Dialog
# ----------------------
class NewUserDialog(QDialog):
    def __init__(self, force_admin=False):
        super().__init__()
        self.setWindowTitle("ახალი მომხმარებელი")
        self.resize(500, 200)

        layout = QFormLayout()

        self.username_input = QLineEdit()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)

        self.role_combo = QComboBox()
        self.role_combo.addItems(list(ROLE_TRANSLATIONS.values()))

        if force_admin:
            self.role_combo.setCurrentText(ROLE_TRANSLATIONS["admin"])
            self.role_combo.setEnabled(False)

        layout.addRow(QLabel("მომხმარებელი:"), self.username_input)
        layout.addRow(QLabel("პაროლი:"), self.password_input)
        layout.addRow(QLabel("როლი:"), self.role_combo)

        # Buttons
        button_layout = QHBoxLayout()
        self.ok_button = QPushButton("შექმნა")
        self.cancel_button = QPushButton("გაუქმება")
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)

        main_layout = QVBoxLayout()
        main_layout.addLayout(layout)
        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)

    def get_data(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        role_geo = self.role_combo.currentText()
        role = ROLE_REVERSE[role_geo]
        return username, password, role


# ----------------------
# Login dialog
# ----------------------
class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("მომხმარებლის შესვლა")
        self.resize(450, 150)

        layout = QFormLayout()
        self.username_input = QLineEdit()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)

        self.login_button = QPushButton("შესვლა")
        self.login_button.clicked.connect(self.handle_login)

        layout.addRow(QLabel("მომხმარებელი:"), self.username_input)
        layout.addRow(QLabel("პაროლი:"), self.password_input)
        layout.addRow(self.login_button)

        self.setLayout(layout)
        self.user_role = None
        self.username = None

    def handle_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        user = get_user(username)
        if not user:
            QMessageBox.warning(self, "შეცდომა", "მომხმარებელი არ მოიძებნა.")
            return

        user_id, uname, password_hash, role = user
        if bcrypt.checkpw(password.encode("utf-8"), password_hash):
            self.user_role = role
            self.username = uname
            self.accept()
        else:
            QMessageBox.warning(self, "შეცდომა", "არასწორი პაროლი.")


# ----------------------
# Manage Users dialog
# ----------------------

class ManageUsersDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("მომხმარებლების მართვა")
        self.resize(800, 500)

        layout = QVBoxLayout()

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "მომხმარებელი", "როლი", "შექმნის თარიღი"])
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

        # Buttons
        button_layout = QHBoxLayout()
        self.add_button = QPushButton("ახალი მომხმარებელი")
        self.edit_button = QPushButton("რედაქტირება")
        self.delete_button = QPushButton("წაშლა")
        self.add_button.clicked.connect(self.add_user_dialog)
        self.edit_button.clicked.connect(self.edit_user_dialog)
        self.delete_button.clicked.connect(self.remove_user)
        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.edit_button)
        button_layout.addWidget(self.delete_button)
        layout.addLayout(button_layout)
        self.setLayout(layout)

        self.load_users()

        # 🔹 Make table dynamic on resize
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setDefaultSectionSize(100)
        self.table.resizeEvent = self.on_table_resize

    def load_users(self):
        self.table.setRowCount(0)
        for row_idx, row in enumerate(list_users()):
            self.table.insertRow(row_idx)
            for col_idx, value in enumerate(row):
                if col_idx == 2:  # role column
                    value = ROLE_TRANSLATIONS.get(value, value)
                self.table.setItem(row_idx, col_idx, QTableWidgetItem(str(value)))

        # Resize columns to content + extra padding
        self.adjust_columns()

    def adjust_columns(self):
        """Resize columns to fit content with extra space."""
        self.table.resizeColumnsToContents()
        for col in range(self.table.columnCount() - 1):
            self.table.setColumnWidth(col, self.table.columnWidth(col) + 20)

    def on_table_resize(self, event):
        """Keep last column stretched and maintain extra padding on others."""
        self.adjust_columns()
        QTableWidget.resizeEvent(self.table, event)


    def add_user_dialog(self):
        dlg = NewUserDialog()
        if dlg.exec_() == QDialog.Accepted:
            username, password, role = dlg.get_data()
            if username and password:
                add_user(username, password, role)
                self.load_users()

    # (edit_user_dialog and remove_user stay same as before)


    def edit_user_dialog(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "გაფრთხილება", "აირჩიეთ მომხმარებელი.")
            return

        user_id = int(self.table.item(row, 0).text())
        conn = sqlite3.connect(USERS_DB)
        cur = conn.cursor()
        cur.execute("SELECT role FROM users WHERE id=?", (user_id,))
        result = cur.fetchone()
        conn.close()
        if not result:
            QMessageBox.warning(self, "შეცდომა", "მომხმარებელი ვერ მოიძებნა.")
            return
        current_role = result[0]

        # Convert to Georgian for display
        current_role_geo = ROLE_TRANSLATIONS.get(current_role, current_role)
        roles_geo = list(ROLE_TRANSLATIONS.values())
        index = roles_geo.index(current_role_geo) if current_role_geo in roles_geo else 0

        new_role_geo, ok = QInputDialog.getItem(
            self, "როლის რედაქტირება", "აირჩიეთ როლი:", roles_geo, index, False
        )
        if ok:
            new_role = ROLE_REVERSE[new_role_geo]

            # Prevent demoting last admin
            if current_role == "admin" and new_role != "admin":
                conn = sqlite3.connect(USERS_DB)
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM users WHERE role='admin'")
                admin_count = cur.fetchone()[0]
                conn.close()
                if admin_count <= 1:
                    QMessageBox.warning(self, "შეცდომა", "ვერ შეცვლით ბოლო ადმინისტრატორის როლს!")
                    return

            conn = sqlite3.connect(USERS_DB)
            cur = conn.cursor()
            cur.execute("UPDATE users SET role=? WHERE id=?", (new_role, user_id))
            conn.commit()
            conn.close()

        # Optional password reset
        reset, ok = QInputDialog.getText(self, "პაროლის განახლება", "ახალი პაროლი (დატოვე ცარიელი თუ არ გინდა შეცვლა):")
        if ok and reset.strip():
            password_hash = bcrypt.hashpw(reset.encode("utf-8"), bcrypt.gensalt())
            conn = sqlite3.connect(USERS_DB)
            cur = conn.cursor()
            cur.execute("UPDATE users SET password_hash=? WHERE id=?", (password_hash, user_id))
            conn.commit()
            conn.close()
            QMessageBox.information(self, "პაროლი განახლდა", "პაროლი წარმატებით შეიცვალა.")

        self.load_users()

    def remove_user(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "გაფრთხილება", "აირჩიეთ წასაშლელი მომხმარებელი.")
            return

        user_id = int(self.table.item(row, 0).text())
        conn = sqlite3.connect(USERS_DB)
        cur = conn.cursor()
        cur.execute("SELECT role, username FROM users WHERE id=?", (user_id,))
        result = cur.fetchone()
        if not result:
            QMessageBox.warning(self, "შეცდომა", "მომხმარებელი ვერ მოიძებნა.")
            conn.close()
            return
        role, username = result

        if role == "admin":
            cur.execute("SELECT COUNT(*) FROM users WHERE role='admin'")
            admin_count = cur.fetchone()[0]
            if admin_count <= 1:
                QMessageBox.warning(self, "შეცდომა", "ვერ წაშლით ბოლო ადმინისტრატორს!")
                conn.close()
                return

        conn.close()

        reply = QMessageBox.question(
            self, "დადასტურება", f"დარწმუნებული ხართ რომ გინდათ მომხმარებლის ('{username}') წაშლა?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            delete_user(user_id)
            self.load_users()
