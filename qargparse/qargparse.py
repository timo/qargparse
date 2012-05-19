try:
    from PySide.QtCore import *
    from PySide.QtGui import *
except ImportError:
    import sip
    sip.setapi('QVariant', 2)
    sip.setapi('QString', 2)

    from PyQt4.QtCore import *
    from PyQt4.QtGui import *

import argparse as ap


class ArgparseWindow(QDialog):
    """This dialog takes an argparser as initialiser and returns an args
    object just like argparse does."""

    action_widgets = {}
    """A dictionary mapping an argparse action object to a tuple of
    1. either None or a QCheckBox, that can toggle the switch
    2. a QLineEdit or QCheckbox, that can set the value of the switch
    """

    taken_dests = set()
    """What "dest" values are already taken."""

    arguments = {}
    """What the commandline looked like the last time it was updated."""

    _last_changed_obj = None

    def __init__(self, argparser, arguments=None, columns=3, **kwargs):
        super(ArgparseWindow, self).__init__(**kwargs)

        self.argp = argparser
        if arguments:
            self.arguments = arguments
        else:
            self.arguments = {}

        self.action_widgets = {}
        self.taken_dests = set()
        self.columns = columns
        self.setup_ui()

    def _widget_with_checkbox(self, widget, action):
        cont = QWidget(parent=self)
        box = QCheckBox(action.dest, parent=self)

        box.setObjectName("%s_active" % action.dest)
        widget.setObjectName("%s_widget" % action.dest)

        def set_last_changed_obj(*a):
            self._last_changed_obj = box

        box.toggled.connect(set_last_changed_obj)
        box.toggled.connect(widget.setEnabled)
        box.toggled.connect(self.update_cmdline)

        widget.setEnabled(False)

        outer = QVBoxLayout()

        layout = QHBoxLayout()
        layout.addWidget(box)
        layout.addWidget(widget)

        outer.addLayout(layout)
        label = QLabel(action.help)
        label.setWordWrap(True)
        outer.addWidget(label)

        cont.setLayout(outer)

        return cont, box

    def build_action_widget(self, action):
        if isinstance(action, (ap._StoreTrueAction, ap._StoreFalseAction)):
            w = QWidget(parent=self)
            cont, box = self._widget_with_checkbox(w, action)
            if action.dest in self.arguments:
                box.setChecked(self.arguments[action.dest])
            else:
                box.setChecked(action.default)

        elif isinstance(action, ap._StoreAction):
            w = QLineEdit()

            if action.type == int or action.type == long:
                w.setValidator(QIntValidator(w))
            elif action.type == float:
                w.setValidator(QDoubleValidator(w))

            def set_last_changed_obj(*a):
                self._last_changed_obj = w

            if action.dest in self.arguments:
                w.setText(unicode(self.arguments[action.dest]))
            if action.default:
                w.setText(unicode(action.default))
            cont, box = self._widget_with_checkbox(w, action)
            w.textChanged.connect(set_last_changed_obj)
            w.textChanged.connect(self.update_cmdline)

        elif isinstance(action, ap._HelpAction):
            return None

        else:
            print "error"
            print "could not build a widget for ", action
            return None


        self.action_widgets[action] = (box, w)
        self.taken_dests.update([action.dest])
        return cont

    def build_action_group(self, ag):
        w = QGroupBox(ag.title)

        widgets = []

        for action in ag._actions:
            if action in self.action_widgets or action.dest in self.taken_dests:
                continue
            widget = self.build_action_widget(action)
            if widget:
                widgets.append(widget)

        layout = QGridLayout()

        for index, widget in enumerate(widgets):
            layout.addWidget(widget, index / self.columns, index % self.columns)

        w.setLayout(layout)

        if not widgets:
            w.deleteLater()
            return None
        return w

    def setup_ui(self):
        layout = QVBoxLayout()

        self.cmdline = QLineEdit()
        # XXX this could 'easily' be set to false with appropriate calls to
        #     self.argp.parse_args etc.
        self.cmdline.setReadOnly(True)
        layout.addWidget(self.cmdline)

        for group in self.argp._action_groups:
            group = self.build_action_group(group)
            if group:
                layout.addWidget(group)

        buttonbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttonbox.accepted.connect(self.try_accept)
        buttonbox.rejected.connect(self.reject)

        layout.addWidget(buttonbox)

        self.setLayout(layout)

    def update_cmdline(self):
        arguments = []
        for action, (box, widget) in self.action_widgets.iteritems():
            checked = box.isChecked()
            if isinstance(action, ap._StoreFalseAction):
                active = not checked
            else:
                active = checked

            if active:
                if isinstance(widget, QLineEdit):
                    arguments.extend([action.option_strings[-1], widget.text()])
                else:
                    arguments.extend([action.option_strings[-1]])

                # FIXME try validating against the argument parsers validators, too

                try:
                    if not widget.hasAcceptableInput():
                        return
                except AttributeError:
                    pass

        self.arguments = arguments
        self.cmdline.setText(" ".join(
            [arg if " " not in arg else arg.replace(" ", '" "') for arg in self.arguments]))

        try:
            self.args = self.argp.parse_args(self.arguments)
        except SystemExit:
            self._last_changed_obj.setVisible(False)


    def try_accept(self):
        self.update_cmdline() # be extra sure, that this is up to date

        self.accept()

