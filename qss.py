style = """

QWidget {
    background-color: #1e1f22;
    color: #e6e6e6;
}

QMainWindow, QDialog {
    background-color: #1e1f22;
}

QPushButton {
    background-color: #2b2d31;
    border: 1px solid #3a3c40;
    border-radius: 6px;
    padding: 2px;
    color: #e6e6e6;
}

QPushButton:hover {
    background-color: #34363b;
    border: 1px solid #4a90e2;
}

QPushButton:pressed {
    background-color: #1f2023;
    border: 1px solid #3a7bc8;
}

QPushButton:disabled {
    background-color: #232427;
    border: 1px solid #2b2d31;
    color: #5a5c60;
}

QMessageBox QPushButton {
    min-width: 70px;
    padding: 4px 12px;
}

QLineEdit{
    background-color: #2b2d31;
    border: 1px solid #45474c;
    border-radius: 6px;
    padding: 1px 4px;
    color: #e6e6e6;
    selection-background-color: #4a90e2;
    selection-color: #ffffff;
}

QLineEdit:hover{
    border: 1px solid #55575c;
}

QLineEdit:focus{
    border: 1px solid #4a90e2;
    background-color: #2f3136;
}

QLineEdit:disabled{
    background-color: #232427;
    color: #6b6d70;
    border: 1px solid #2b2d31;
}

QGroupBox {
    border: 1px solid #3a3c40;
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 10px;
    color: #e6e6e6;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 6px;
    color: #e6e6e6;
}

QGroupBox:disabled {
    border: 1px solid #2b2d31;
    color: #5a5c60;
}

QGroupBox::title:disabled {
    color: #5a5c60;
}

QCheckBox, QRadioButton {
    spacing: 6px;
    color: #e6e6e6;
}

QCheckBox::indicator, QRadioButton::indicator {
    width: 14px;
    height: 14px;
    border: 1px solid #45474c;
    background-color: #2b2d31;
}

QCheckBox::indicator {
    border-radius: 3px;
}

QRadioButton::indicator {
    border-radius: 7px;
}

QCheckBox::indicator:hover, QRadioButton::indicator:hover {
    border: 1px solid #4a90e2;
}

QCheckBox::indicator:checked {
    background-color: #4a90e2;
    border: 1px solid #4a90e2;
    image: url(:/assets/icons/checkmark.png);
}

QRadioButton::indicator:checked {
    background-color: #4a90e2;
    border: 1px solid #4a90e2;
    image: url(:/assets/icons/radio_dot.png);
}

QCheckBox::indicator:disabled, QRadioButton::indicator:disabled {
    background-color: #232427;
    border-color: #2b2d31;
}

QCheckBox:disabled, QRadioButton:disabled {
    color: #5a5c60;
}

QListView, QListWidget {
    background-color: #232427;
    border: 1px solid #3a3c40;
    border-radius: 6px;
    color: #e6e6e6;
    outline: none;
    padding: 4px;
}

QListView::item:hover, QListWidget::item:hover {
    background-color: #2b2d31;
}

QListView::item:selected, QListWidget::item:selected {
    background-color: #4a90e2;
    color: #ffffff;
}

QListView::item:selected:!active, QListWidget::item:selected:!active {
    background-color: #3a6ea5;
    color: #ffffff;
}

QScrollBar:vertical {
    background: transparent;
    width: 6px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #3a3c40;
    border-radius: 3px;
    min-height: 24px;
}

QScrollBar::handle:vertical:hover {
    background: #4a90e2;
}


QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background: transparent;
    height: 6px;
}

QScrollBar::handle:horizontal {
    background: #3a3c40;
    border-radius: 3px;
    min-width: 24px;
}

QScrollBar::handle:horizontal:hover {
    background: #4a90e2;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

QToolTip {
    background-color: #2b2d31;
    color: #e6e6e6;
    border: 1px solid #4a90e2;
    border-radius: 2px;
    padding: 0px 1px;
    margin: 0px;
}

QProgressBar {
    background-color: #232427;
    border: 1px solid #3a3c40;
    border-radius: 6px;
    text-align: center;
    color: #e6e6e6;
    height: 16px;
}

QProgressBar::chunk {
    background-color: #4a90e2;
    border-radius: 5px;
}

QComboBox {
    background-color: #2b2d31;
    border: 1px solid #45474c;
    border-radius: 6px;
    padding: 2px 6px 2px 24px;
    color: #e6e6e6;
}

QComboBox:hover {
    border: 1px solid #55575c;
}

QComboBox:focus, QComboBox:on {
    border: 1px solid #4a90e2;
    background-color: #2f3136;
}

QComboBox:disabled {
    background-color: #232427;
    color: #6b6d70;
    border: 1px solid #2b2d31;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: left;
    width: 20px;
    border: none;
}

QComboBox::down-arrow {
    image: url(:/assets/icons/arrow_down.png);
    width: 10px;
    height: 10px;
}

QComboBox QAbstractItemView {
    background-color: #2b2d31;
    border: 1px solid #45474c;
    border-radius: 6px;
    selection-background-color: #4a90e2;
    selection-color: #ffffff;
    color: #e6e6e6;
    outline: none;
}

QComboBox QAbstractItemView::item {
    border-radius: 4px;
    padding: 4px 6px;
}

"""