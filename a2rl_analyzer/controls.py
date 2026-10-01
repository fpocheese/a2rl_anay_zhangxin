"""Qt controls created from the original App Designer component metadata."""
from pathlib import Path
import re

from .qt import (Qt, QtCore, QtGui, QtWidgets, QFont, QPixmap, QPainter, QComboBox, QLabel, QLineEdit, QPushButton,
                 QSizePolicy, QSlider, QSpinBox, QWidget)


def matlab_text(value):
    """Decode literal strings and multiline MATLAB cell-string labels."""
    if value is None:
        return ''
    value = str(value)
    if value.startswith('{'):
        return '\n'.join(re.findall(r"'((?:[^']|'')*)'", value)).replace("''", "'")
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1].replace("''", "'")
    return value


def numbers(value, default=()):
    try:
        return [float(v) for v in re.findall(r'-?\d+(?:\.\d+)?|Inf', value)]
    except (TypeError, ValueError):
        return list(default)


def grid_span(value):
    values = numbers(value, [1])
    return int(values[0]) - 1, int(values[-1] - values[0]) + 1


class Logo(QLabel):
    def __init__(self, path):
        super().__init__()
        self._image = QPixmap(str(path))
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(10, 10)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)

    def resizeEvent(self, event):
        if not self._image.isNull():
            self.setPixmap(self._image.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio,
                                             Qt.TransformationMode.SmoothTransformation))
        super().resizeEvent(event)


class IndexSlider(QSlider):
    """Integer slider with visible index ticks like the MATLAB slider."""
    def __init__(self):
        super().__init__(Qt.Orientation.Horizontal)
        self.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.setTracking(True)
        self.setMinimumHeight(35)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.valueChanged.connect(self.update)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setPen(self.palette().windowText().color())
        font = self.font()
        font.setPixelSize(10)
        painter.setFont(font)
        span = self.maximum() - self.minimum()
        if span <= 0:
            return
        count = max(2, min(9, self.width() // 55))
        tick_y = self.height() // 2 + 6
        painter.setPen(QtGui.QColor('#aaaaaa'))
        for i in range((count - 1) * 5 + 1):
            x = round(9 + (self.width() - 18) * i / ((count - 1) * 5))
            painter.drawLine(x, tick_y, x, tick_y + (6 if i % 5 == 0 else 3))
        painter.setPen(self.palette().windowText().color())
        for i in range(count):
            value = round(self.minimum() + span * i / (count - 1))
            x = 9 + (self.width() - 18) * i / (count - 1)
            label = str(value)
            width = painter.fontMetrics().horizontalAdvance(label)
            painter.drawText(round(max(0, min(self.width()-width, x-width/2))),
                             min(self.height()-1, self.height()//2+23), label)


class IndexSpinBox(QSpinBox):
    """Draw visible MATLAB-style arrow glyphs consistently in Qt5/Qt6 themes."""
    def paintEvent(self, event):
        super().paintEvent(event)
        option = QtWidgets.QStyleOptionSpinBox()
        self.initStyleOption(option)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self.palette().windowText().color() if self.isEnabled()
                         else QtGui.QColor('#b0b0b0'))
        style = QtWidgets.QStyle
        for control, direction in ((style.SubControl.SC_SpinBoxUp, -1),
                                   (style.SubControl.SC_SpinBoxDown, 1)):
            rect = self.style().subControlRect(style.ComplexControl.CC_SpinBox,
                                               option, control, self)
            x, y = rect.center().x(), rect.center().y()
            painter.drawPolygon(QtGui.QPolygonF([
                QtCore.QPointF(x-3.5, y-direction*1.5),
                QtCore.QPointF(x+3.5, y-direction*1.5),
                QtCore.QPointF(x, y+direction*2)]))


class Dropdown(QComboBox):
    """Keep the popup indicator visible under the app's flat Qt stylesheet."""
    def paintEvent(self, event):
        super().paintEvent(event)
        option = QtWidgets.QStyleOptionComboBox()
        self.initStyleOption(option)
        style = QtWidgets.QStyle
        rect = self.style().subControlRect(style.ComplexControl.CC_ComboBox,
                                           option, style.SubControl.SC_ComboBoxArrow, self)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self.palette().windowText().color() if self.isEnabled()
                         else QtGui.QColor('#b0b0b0'))
        x, y = rect.center().x(), rect.center().y()
        painter.drawPolygon(QtGui.QPolygonF([QtCore.QPointF(x-3.5, y-2),
                                            QtCore.QPointF(x+3.5, y-2),
                                            QtCore.QPointF(x, y+2)]))


def make_control(name, entry, root):
    kind, props = entry['kind'], entry['props']
    label = matlab_text(props.get('Text', ''))
    if kind == 'uilabel':
        widget = QLabel(label)
        widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        widget.setWordWrap(props.get('WordWrap') == "'on'" or '\n' in label)
        if props.get('VerticalAlignment') == "'top'":
            widget.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        widget.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
    elif kind == 'uibutton':
        widget = QPushButton(label)
    elif kind == 'uieditfield':
        widget = QLineEdit(matlab_text(props.get('Value', '')))
        widget.setReadOnly(name != 'Text_s')
        widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        widget.setMinimumWidth(0)
    elif kind == 'uispinner':
        widget = IndexSpinBox()
        limits = numbers(props.get('Limits', '[0 Inf]'), [0, float('inf')])
        upper = 2_000_000_000 if len(limits) < 2 or limits[1] == float('inf') else int(limits[1])
        widget.setRange(int(limits[0]), upper)
        widget.setSingleStep(int(props.get('Step', 1)))
        widget.setValue(int(props.get('Value', 1)))
        widget.setAlignment(Qt.AlignmentFlag.AlignRight)
        widget.setKeyboardTracking(False)
        widget.setMinimumWidth(0)
    elif kind == 'uislider':
        widget = IndexSlider()
        limits = numbers(props.get('Limits', '[1 101]'))
        widget.setRange(int(limits[0]), int(limits[1]))
        widget.setValue(int(props.get('Value', 1)))
        widget.setTickInterval(max(1, (widget.maximum()-widget.minimum()) // 20))
    elif kind == 'uidropdown':
        widget = Dropdown()
        widget.addItems(re.findall(r"'([^']*)'", props.get('Items', '')))
        widget.setCurrentText(matlab_text(props.get('Value', '')))
        widget.setMinimumWidth(0)
    elif kind == 'uiimage':
        matches = re.findall(r"'([^']*)'", props.get('ImageSource', ''))
        widget = Logo(Path(root) / matches[-1])
    else:
        widget = QWidget()
    widget.setObjectName(name)
    if kind in ('uilabel', 'uieditfield', 'uispinner'):
        alignment = matlab_text(props.get('HorizontalAlignment',
                                         "'right'" if kind == 'uispinner' else "'left'"))
        horizontal = {'left': Qt.AlignmentFlag.AlignLeft,
                      'center': Qt.AlignmentFlag.AlignHCenter,
                      'right': Qt.AlignmentFlag.AlignRight}[alignment]
        vertical = (Qt.AlignmentFlag.AlignTop if props.get('VerticalAlignment') == "'top'"
                    else Qt.AlignmentFlag.AlignVCenter)
        widget.setAlignment(horizontal | vertical)
    font = QFont(widget.font())
    font.setPixelSize(int(props.get('FontSize', 12)))
    font.setBold(props.get('FontWeight') == "'bold'")
    widget.setFont(font)
    if kind in ('uibutton', 'uieditfield', 'uispinner', 'uidropdown'):
        widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    return widget
