from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QStyle, QStyleOption, QHBoxLayout, QScrollArea, QPushButton
from PyQt5.QtGui import QPainter, QIcon
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from utils.pyqt5_utils.template_thumbnail import TemplateThumbnail
from utils.manager.template_manager import list_templates, delete_template, load_template
from static import back_path, forward_path, background_path, logo_path

STYLE_SHEET = "background-color: transparent; border: none;"

class HomeTab(QWidget):
    template_clicked = pyqtSignal(str)

    def __init__(self, parent=None, templates_per_page=8):
        super().__init__(parent)
        self.templates_per_page = templates_per_page
        self.current_page = 0

        self.settings_tab_layout = QVBoxLayout(self)

        # Add a QLabel for the title
        self.title_label = QLabel(self)
        logo_icon = QIcon(logo_path)
        self.title_label.setPixmap(logo_icon.pixmap(500, 500))
        self.title_label.setAlignment(Qt.AlignCenter)
        self.settings_tab_layout.addWidget(self.title_label)

        # Add a QLineEdit for the search/URL input
        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText(self.tr("Search or write URL"))
        self.search_input.setMinimumWidth(600)
        font = self.search_input.font()
        font.setPointSize(16)
        self.search_input.setFont(font)
        self.settings_tab_layout.addWidget(self.search_input, alignment=Qt.AlignCenter)

        self.templates_grid = QHBoxLayout()
        self.templates_scroll_area = QScrollArea()
        self.templates_scroll_area.setMaximumHeight(200)
        self.templates_scroll_area.setWidgetResizable(True)
        self.templates_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.templates_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.templates_scroll_area.setWidget(QWidget())
        self.templates_scroll_area.widget().setLayout(self.templates_grid)
        self.settings_tab_layout.addWidget(self.templates_scroll_area, alignment=Qt.AlignTop)
        self.templates_scroll_area.setStyleSheet(STYLE_SHEET)

        self.setStyleSheet(f"""
            HomeTab {{
                background-image: url({background_path});
                background-repeat: no-repeat;
                background-position: center;
            }}
        """)

        # Add navigation buttons
        self.nav_buttons_layout = QHBoxLayout()
        self.previous_button = QPushButton()
        back_icon = QIcon(back_path)
        self.previous_button.setIcon(back_icon)
        self.previous_button.clicked.connect(self.previous_page)
        self.previous_button.setFixedSize(QSize(50, 100))
        self.next_button = QPushButton()
        forward_icon = QIcon(forward_path)
        self.next_button.setIcon(forward_icon)
        self.next_button.clicked.connect(self.next_page)
        self.next_button.setFixedSize(QSize(50, 100))
        self.nav_buttons_layout.addWidget(self.previous_button)
        self.nav_buttons_layout.addWidget(self.next_button)
        self.settings_tab_layout.addLayout(self.nav_buttons_layout)

        self.previous_button.setStyleSheet(STYLE_SHEET)
        self.next_button.setStyleSheet(STYLE_SHEET)

        self.templates = []

        templates_list = list_templates()

        if not self.templates:
            for i, template_id in enumerate(templates_list):
                template_thumbnail = TemplateThumbnail(load_template(template_id), i)
                self.templates.append(template_thumbnail)
                self.templates_grid.addWidget(template_thumbnail)
                template_thumbnail.clicked.connect(self.template_thumbnail_clicked)
                template_thumbnail.deleted.connect(self.template_thumbnail_deleted)

        if not self.templates:
            self.templates_scroll_area.hide()
            self.previous_button.hide()
            self.next_button.hide()

        self.change_page()

    def update_templates_list(self):
        self.templates = []
        templates_list = list_templates()

        while self.templates_grid.count():
            item = self.templates_grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        if not self.templates:
            for i, template_id in enumerate(templates_list):
                template_thumbnail = TemplateThumbnail(load_template(template_id), i)
                self.templates.append(template_thumbnail)
                self.templates_grid.addWidget(template_thumbnail)
                template_thumbnail.clicked.connect(self.template_thumbnail_clicked)
                template_thumbnail.deleted.connect(self.template_thumbnail_deleted)

        if not self.templates:
            self.templates_scroll_area.hide()
            self.previous_button.hide()
            self.next_button.hide()
        else:
            self.templates_scroll_area.show()
            self.previous_button.show()
            self.next_button.show()

        self.change_page()

    def template_thumbnail_clicked(self):
        sender = self.sender()
        if isinstance(sender, TemplateThumbnail):
            self.template_clicked.emit(str(sender.template["id"]))

    def change_page(self):
        num_shown_templates = self.get_num_shown_templates()
        start_index = self.current_page * num_shown_templates
        end_index = min(start_index + num_shown_templates, len(self.templates))

        for i, template in enumerate(self.templates):
            if start_index <= i < end_index:
                template.show()
            else:
                template.hide()

        # Update the navigation buttons
        self.previous_button.setEnabled(self.current_page > 0)
        self.next_button.setEnabled(end_index < len(self.templates))

    def get_num_shown_templates(self):
        width = self.width()
        num_templates = len(self.templates)
        if width >= 1750 and num_templates > 7:
            return 8
        if width >= 1500 and num_templates > 6:
            return 7
        if width >= 1200 and num_templates > 5:
            return 6
        if width >= 900 and num_templates > 4:
            return 5
        return 4

    def next_page(self):
        self.current_page += 1
        self.change_page()

    def previous_page(self):
        self.current_page -= 1
        self.change_page()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.change_page()

    def paintEvent(self, event):
        option = QStyleOption()
        option.initFrom(self)
        painter = QPainter(self)
        self.style().drawPrimitive(QStyle.PE_Widget, option, painter, self)

    def template_thumbnail_deleted(self, template_id):
        template = delete_template(template_id)
        if template:
            # Remove the template from the list of templates
            for i, t in enumerate(self.templates):
                if t.template["id"] == template_id:
                    del self.templates[i]
                    break

            # Also remove it from the layout
            for i in reversed(range(self.templates_grid.count())): 
                widget_to_remove = self.templates_grid.itemAt(i).widget()
                if widget_to_remove and widget_to_remove.template["id"] == template_id:
                    # remove it from the layout list
                    self.templates_grid.removeWidget(widget_to_remove)
                    # remove it from the gui
                    widget_to_remove.setParent(None)
                    break

        self.update_templates_list()
