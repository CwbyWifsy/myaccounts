import sys
import os
import json
import base64
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QScrollArea, QFrame, QLabel, QPushButton, QMessageBox,
    QDialog, QFormLayout, QDialogButtonBox, QFileDialog,
    QInputDialog, QLineEdit
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPalette, QColor
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.fernet import Fernet

from vault import decrypt_vault, load_vault_file


# Utility to derive a Fernet key from a password and salt
def derive_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100_000,
        backend=default_backend()
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))

class AddEntryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New Entry")

        self.name_input = QLineEdit()
        self.username_input = QLineEdit()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)

        layout = QFormLayout()
        layout.addRow("Name:", self.name_input)
        layout.addRow("Username:", self.username_input)
        layout.addRow("Password:", self.password_input)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        layout.addWidget(self.buttons)
        self.setLayout(layout)

    def get_data(self) -> dict:
        return {
            "name": self.name_input.text(),
            "username": self.username_input.text(),
            "password": self.password_input.text()
        }

class PasswordManager(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Password Vault")
        self.entries = []

        # Controls
        self.open_button = QPushButton("Open Vault")
        self.open_button.clicked.connect(self.open_vault)
        self.save_button = QPushButton("Save Vault")
        self.save_button.clicked.connect(self.save_vault)
        self.add_button = QPushButton("Add Entry")
        self.add_button.clicked.connect(self.add_entry)

        # Card container inside scroll area
        self.card_container = QVBoxLayout()
        self.card_container.setAlignment(Qt.AlignTop)
        card_widget = QWidget()
        card_widget.setLayout(self.card_container)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(card_widget)

        # Layout
        top_layout = QHBoxLayout()
        top_layout.addWidget(self.open_button)
        top_layout.addWidget(self.save_button)
        top_layout.addWidget(self.add_button)

        main_layout = QVBoxLayout()
        main_layout.addLayout(top_layout)
        main_layout.addWidget(self.scroll_area)
        self.setLayout(main_layout)

    def add_entry(self):
        dialog = AddEntryDialog(self)
        if dialog.exec_():
            data = dialog.get_data()
            if data["name"]:
                self.entries.append(data)
                self._refresh_cards()
            else:
                QMessageBox.warning(self, "Warning", "Name cannot be empty.")

    def _refresh_cards(self):
        # Clear existing cards
        for i in reversed(range(self.card_container.count())):
            widget = self.card_container.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        # Add card per entry
        for entry in self.entries:
            card = QFrame()
            card.setFrameShape(QFrame.Box)
            card.setLineWidth(1)
            card.setMidLineWidth(0)
            card.setStyleSheet("QFrame { border-radius: 5px; padding: 10px; background: #f9f9f9; }")

            name_lbl = QLabel(entry.get('name', '<Unnamed>'))
            name_lbl.setFont(QFont('Arial', 12, QFont.Bold))

            user_lbl = QLabel(f"Username: {entry.get('username')}")
            pass_lbl = QLabel(f"Password: {entry.get('password')}")

            vbox = QVBoxLayout()
            vbox.addWidget(name_lbl)
            vbox.addWidget(user_lbl)
            vbox.addWidget(pass_lbl)

            card.setLayout(vbox)
            self.card_container.addWidget(card)

    def save_vault(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Vault File", "", "Vault Files (*.vault);;All Files (*)"
        )
        if not path:
            return
        password, ok = QInputDialog.getText(
            self, "Master Password", "Enter master password:", QLineEdit.Password
        )
        if not ok or not password:
            return
        try:
            salt = os.urandom(16)
            key = derive_key(password, salt)
            fernet = Fernet(key)
            data_bytes = json.dumps(self.entries).encode('utf-8')
            token = fernet.encrypt(data_bytes)
            vault_obj = {
                'salt': base64.b64encode(salt).decode('utf-8'),
                'data': token.decode('utf-8')
            }
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(vault_obj, f)
            QMessageBox.information(self, "Success", "Vault saved successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save vault:\n{e}")

    def open_vault(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Vault File", "", "Vault Files (*.vault);;All Files (*)"
        )
        if not path:
            return
        try:
            password, ok = QInputDialog.getText(
                self, "Master Password", "Enter master password:", QLineEdit.Password
            )
            data = decrypt_vault(password, load_vault_file(path))
            # 验证格式：应为列表
            # if not isinstance(data, list):
            #     raise ValueError("Vault file format invalid")
            print(data)
            # 更新 entries 和列表显示
            self.entries = data["entries"]
            for entry in self.entries:
                # 每个条目必须包含 name
                name = entry.get("name", "<Unnamed>")
                self._refresh_cards()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open vault:\n{e}")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = PasswordManager()
    window.resize(900, 600)
    window.show()
    sys.exit(app.exec_())
