# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_graphidentify.ui'
#
# Created by: PyQt5 UI code generator 5.9
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_GraphIdentifyDialog(object):
    def setupUi(self, GraphIdentifyDialog):
        GraphIdentifyDialog.setObjectName("GraphIdentifyDialog")
        GraphIdentifyDialog.resize(824, 618)
        GraphIdentifyDialog.setCursor(QtGui.QCursor(QtCore.Qt.CrossCursor))
        self.formLayout = QtWidgets.QFormLayout(GraphIdentifyDialog)
        self.formLayout.setObjectName("formLayout")
        self.webView = QtWebKitWidgets.QWebView(GraphIdentifyDialog)
        self.webView.setMinimumSize(QtCore.QSize(800, 600))
        self.webView.setMaximumSize(QtCore.QSize(800, 600))
        self.webView.setUrl(QtCore.QUrl("about:blank"))
        self.webView.setObjectName("webView")
        self.formLayout.setWidget(0, QtWidgets.QFormLayout.FieldRole, self.webView)

        self.retranslateUi(GraphIdentifyDialog)
        QtCore.QMetaObject.connectSlotsByName(GraphIdentifyDialog)

    def retranslateUi(self, GraphIdentifyDialog):
        _translate = QtCore.QCoreApplication.translate
        GraphIdentifyDialog.setWindowTitle(_translate("GraphIdentifyDialog", "Informazioni serie storica con Grafico"))

from PyQt5 import QtWebKitWidgets
