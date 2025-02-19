from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QGridLayout, QWidget, QTabWidget, QSpinBox, QLineEdit, QDoubleSpinBox, \
    QCheckBox, QComboBox, QTableWidget, QTableWidgetItem, QGroupBox, QLabel, QHBoxLayout, QVBoxLayout, QTextEdit

from PyQt5.QtCore import pyqtSlot

import numpy as np

class QtPanelInfo(QTabWidget):

    def __init__(self, parent=None):
        super(QtPanelInfo, self).__init__(parent)

        self.fragment = None
        self.fields = {}
        self.attributes = []

        self.addTab(self.regionInfo(), "Properties")

        self.setAutoFillBackground(True)

        self.setStyleSheet("QTabWidget::pane {border: 1px solid white; padding: 4px}"
                           "QTabBar::tab:!selected {background: rgb(49,51,53); border: 0px solid #AAAAAA; "
                           "border-bottom-color: #C2C7CB; border-top-left-radius: 4px; "
                           "border-top-right-radius: 4px;"
                           "min-width: 8ex; padding: 2px;}"
                           "QTabBar::tab:selected {background: rgb(90,90,90); border: 0px solid #AAAAAA; "
                           "border-bottom-color: #C2C7CB; border-top-left-radius: 4px; "
                           "border-top-right-radius: 4px;"
                           "min-width: 8ex; padding: 2px;}")

    def regionInfo(self):

        layout = QGridLayout()

        fields = { 'id': 'Id:', 'group_id': 'Group:', 'name': 'Name:', 'note': 'Note:' }

        self.fields = {}
        row = 0
        col = 0
        for field in fields:

            label = QLabel(fields[field])
            layout.addWidget(label, row, col)
            if row == 1:
                # the value of this field is editable
                value = self.fields[field] = QLineEdit('')
                value.textChanged.connect(self.updateFragmentInfo)
            else:
                value = self.fields[field] = QLabel('')

            layout.addWidget(value, row, col+1)
            col += 2
            if col == 4:
                row += 1
                col = 0

        layout.setRowStretch(layout.rowCount(), 1)
        widget = QWidget()
        widget.setLayout(layout)
        return widget

    @pyqtSlot()
    def updateFragmentInfo(self):

        if self.fragment:
            self.fragment.name = self.fields['name'].text()
            self.fragment.note = self.fields['note'].text()

    def clear(self):

        self.blob = None
        for field in self.fields:
            self.fields[field].blockSignals(True)
            self.fields[field].setText("")
            self.fields[field].blockSignals(False)

    def update(self, fragment):
        self.clear()

        self.fragment = fragment

        for field in self.fields:
            self.fields[field].blockSignals(True)

            value = getattr(fragment, field)
            if value == -1:
                self.fields[field].setText("")
            else:
                self.fields[field].setText(str(value))

            self.fields[field].blockSignals(False)
