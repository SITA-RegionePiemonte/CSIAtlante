# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_graphidentify.ui'
#
# Created: Thu Mar 31 11:25:06 2016
#      by: PyQt4 UI code generator 4.11.3
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class Ui_GraphIdentifyDialog(object):
    def setupUi(self, GraphIdentifyDialog):
        GraphIdentifyDialog.setObjectName(_fromUtf8("GraphIdentifyDialog"))
        GraphIdentifyDialog.resize(824, 618)
        GraphIdentifyDialog.setCursor(QtGui.QCursor(QtCore.Qt.CrossCursor))
        self.formLayout = QtGui.QFormLayout(GraphIdentifyDialog)
        self.formLayout.setObjectName(_fromUtf8("formLayout"))
        self.webView = QtWebKit.QWebView(GraphIdentifyDialog)
        self.webView.setMinimumSize(QtCore.QSize(800, 600))
        self.webView.setMaximumSize(QtCore.QSize(800, 600))
        self.webView.setUrl(QtCore.QUrl(_fromUtf8("about:blank")))
        self.webView.setObjectName(_fromUtf8("webView"))
        self.formLayout.setWidget(0, QtGui.QFormLayout.FieldRole, self.webView)

        self.retranslateUi(GraphIdentifyDialog)
        QtCore.QMetaObject.connectSlotsByName(GraphIdentifyDialog)

    def retranslateUi(self, GraphIdentifyDialog):
        GraphIdentifyDialog.setWindowTitle(_translate("GraphIdentifyDialog", "Informazioni serie storica con Grafico", None))

from PyQt4 import QtWebKit
