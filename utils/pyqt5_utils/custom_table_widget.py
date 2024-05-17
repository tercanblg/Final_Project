from PyQt5.QtWidgets import QTableWidget
from PyQt5.QtCore import QEvent
from PyQt5.QtWidgets import QToolTip

class CustomTableWidget(QTableWidget):
    def __init__(self, parent=None):
        super(CustomTableWidget, self).__init__(parent)

    def viewportEvent(self, event):
        return self.handle_tool_tip_event(event) or super(CustomTableWidget, self).viewportEvent(event)

    def handle_tool_tip_event(self, event):
        if event.type() == QEvent.ToolTip:
            pos = event.pos()
            item = self.itemAt(pos)
            if item:
                QToolTip.showText(event.globalPos(), item.text())
            else:
                QToolTip.hideText()
            return True
        return False