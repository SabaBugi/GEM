from PyQt5.QtWidgets import (
    QDialog, QLineEdit, QLabel, QPushButton, QFormLayout,
    QTextEdit, QComboBox, QFileDialog, QVBoxLayout,
    QListWidget, QListWidgetItem
)
from PyQt5.QtGui import QPixmap, QIcon
from database import CATEGORIES, STATUS_OPTIONS, get_images, artefact_code_exists, artefact_code_exists_for_other


class ArtefactForm(QDialog):
    def __init__(self, artefact=None):
        super().__init__()
        self.setWindowTitle("არტეფაქტის ფორმა")
        self.setMinimumWidth(500)  # wider form

        layout = QFormLayout()

        self.artefact = artefact  # None if adding new

        self.code_input = QLineEdit()  # 🆕 allow manual code entry
        self.name_input = QLineEdit()
        self.category_input = QComboBox()
        self.category_input.addItems(CATEGORIES)
        self.origin_input = QLineEdit()
        self.description_input = QTextEdit()
        self.period_input = QLineEdit()
        self.location_input = QLineEdit()

        self.condition_input = QComboBox()
        self.condition_input.addItems(["კარგი", "საჭიროებს რესტავრაცია-კონსერვაციას"])

        self.status_input = QComboBox()
        self.status_input.addItems(STATUS_OPTIONS)

        self.curator_input = QLineEdit()

        # Image section
        self.image_list = QListWidget()
        self.image_list.setFixedHeight(150)

        self.image_button = QPushButton("ფოტოების დამატება")
        self.image_button.clicked.connect(self.select_images)

        self.remove_button = QPushButton("ფოტოს წაშლა")
        self.remove_button.clicked.connect(self.remove_selected_image)

        image_layout = QVBoxLayout()
        image_layout.addWidget(self.image_button)
        image_layout.addWidget(self.remove_button)
        image_layout.addWidget(self.image_list)


        layout.addRow(QLabel("კოდი:"), self.code_input)
        layout.addRow(QLabel("ნივთი:"), self.name_input)
        layout.addRow(QLabel("კატეგორია:"), self.category_input)
        layout.addRow(QLabel("აღმოჩენის ადგილი:"), self.origin_input)
        layout.addRow(QLabel("აღწერა:"), self.description_input)
        layout.addRow(QLabel("პერიოდი:"), self.period_input)
        layout.addRow(QLabel("მდებარეობა გამოფენაზე:"), self.location_input)
        layout.addRow(QLabel("მდგომარეობა:"), self.condition_input)
        layout.addRow(QLabel("სტატუსი:"), self.status_input)
        layout.addRow(QLabel("კურატორი:"), self.curator_input)
        layout.addRow(QLabel("ფოტოები:"), image_layout)

        # Buttons
        self.save_button = QPushButton("შენახვა")
        self.cancel_button = QPushButton("გაუქმება")
        self.save_button.clicked.connect(self.validate_and_accept)
        self.cancel_button.clicked.connect(self.reject)
        layout.addRow(self.save_button, self.cancel_button)

        self.setLayout(layout)

        # If editing → populate fields
        if artefact:
            # artefact tuple:
            # (id, code, name, category, origin, description,
            #  period, location, condition, status, curator, date_added)
            self.code_input.setText(artefact[1])
            self.name_input.setText(artefact[2])
            self.category_input.setCurrentText(artefact[3])
            self.origin_input.setText(artefact[4])
            self.description_input.setPlainText(artefact[5])
            self.period_input.setText(artefact[6])
            self.location_input.setText(artefact[7])
            self.condition_input.setCurrentText(artefact[8])
            self.status_input.setCurrentText(artefact[9])
            self.curator_input.setText(artefact[10])

            # Load stored images (absolute paths from get_images)
            for img_path in get_images(artefact[0]):
                item = QListWidgetItem(img_path)   # ✅ keep absolute path
                icon = QIcon(QPixmap(img_path).scaled(64, 64))
                item.setIcon(icon)
                self.image_list.addItem(item)


    def get_data(self):
        """
        Return tuple of artefact data + list of image paths selected in form.
        """
        images = [self.image_list.item(i).text() for i in range(self.image_list.count())]
        return (
            self.code_input.text(),        # 🆕 custom code entered manually
            self.name_input.text(),
            self.category_input.currentText(),
            self.origin_input.text(),
            self.description_input.toPlainText(),
            self.period_input.text(),
            self.location_input.text(),
            self.condition_input.currentText(),
            self.status_input.currentText(),
            self.curator_input.text(),
            images
        )

    def select_images(self):
        """
        Let user pick images, preview them in list.
        """
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "აირჩიე ფოტოები", "", "Images (*.png *.jpg *.jpeg *.bmp)"
        )
        for file_path in file_paths:
            item = QListWidgetItem(file_path)
            icon = QIcon(QPixmap(file_path).scaled(64, 64))
            item.setIcon(icon)
            self.image_list.addItem(item)

    def validate_and_accept(self):
        code = self.code_input.text().strip()
        if not code:
            QMessageBox.warning(self, "გაფრთხილება", "გთხოვთ მიუთითოთ არტეფაქტის კოდი.")
            return

        if self.artefact is None:  
            # Adding new
            if artefact_code_exists(code):
                QMessageBox.warning(self, "შეცდომა", f"კოდი '{code}' უკვე არსებობს.")
                return
        else:
            # Editing existing
            artefact_id = self.artefact[0]
            if artefact_code_exists_for_other(code, artefact_id):
                QMessageBox.warning(self, "შეცდომა", f"კოდი '{code}' უკვე არსებობს სხვა არტეფაქტში.")
                return

        self.accept()

    def remove_selected_image(self):
        selected_items = self.image_list.selectedItems()
        if not selected_items:
            return
        for item in selected_items:
            row = self.image_list.row(item)
            self.image_list.takeItem(row)


