from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt
from database import get_images

class ImageGallery(QDialog):
    def __init__(self, artefact_id):
        super().__init__()
        self.setWindowTitle("ფოტოების გალერეა")
        self.resize(800, 600)

        self.artefact_id = artefact_id
        self.images = get_images(artefact_id)
        self.current_index = 0

        layout = QVBoxLayout()

        # Image display
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.image_label)

        # Navigation buttons
        nav_layout = QHBoxLayout()
        self.prev_button = QPushButton("← წინა")
        self.prev_button.clicked.connect(self.show_prev)
        self.next_button = QPushButton("შემდეგი →")
        self.next_button.clicked.connect(self.show_next)
        nav_layout.addWidget(self.prev_button)
        nav_layout.addWidget(self.next_button)

        layout.addLayout(nav_layout)
        self.setLayout(layout)

        if self.images:
            self.show_image(0)
        else:
            self.image_label.setText("ფოტოები არ არის")

    def show_image(self, index):
        if 0 <= index < len(self.images):
            pixmap = QPixmap(self.images[index])
            if not pixmap.isNull():
                self.image_label.setPixmap(pixmap.scaled(750, 550, aspectRatioMode=True))
            else:
                self.image_label.setText("ფოტოს ჩატვირთვა ვერ მოხერხდა")
            self.current_index = index

    def show_prev(self):
        if self.images and self.current_index > 0:
            self.show_image(self.current_index - 1)

    def show_next(self):
        if self.images and self.current_index < len(self.images) - 1:
            self.show_image(self.current_index + 1)
