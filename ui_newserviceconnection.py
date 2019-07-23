# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_newserviceconnection.ui'
#
# Created: Thu Mar 31 11:25:05 2016
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

class Ui_NewServiceConnectionDialog(object):
    def setupUi(self, NewServiceConnectionDialog):
        NewServiceConnectionDialog.setObjectName(_fromUtf8("NewServiceConnectionDialog"))
        NewServiceConnectionDialog.resize(400, 212)
        self.layoutWidget = QtGui.QWidget(NewServiceConnectionDialog)
        self.layoutWidget.setGeometry(QtCore.QRect(9, 9, 371, 191))
        self.layoutWidget.setObjectName(_fromUtf8("layoutWidget"))
        self.verticalLayout = QtGui.QVBoxLayout(self.layoutWidget)
        self.verticalLayout.setMargin(0)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.groupBox = QtGui.QGroupBox(self.layoutWidget)
        self.groupBox.setObjectName(_fromUtf8("groupBox"))
        self.formLayout = QtGui.QFormLayout(self.groupBox)
        self.formLayout.setObjectName(_fromUtf8("formLayout"))
        self.label = QtGui.QLabel(self.groupBox)
        self.label.setObjectName(_fromUtf8("label"))
        self.formLayout.setWidget(0, QtGui.QFormLayout.LabelRole, self.label)
        self.leName = QtGui.QLineEdit(self.groupBox)
        self.leName.setObjectName(_fromUtf8("leName"))
        self.formLayout.setWidget(0, QtGui.QFormLayout.FieldRole, self.leName)
        self.label_2 = QtGui.QLabel(self.groupBox)
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.formLayout.setWidget(1, QtGui.QFormLayout.LabelRole, self.label_2)
        self.leURL = QtGui.QLineEdit(self.groupBox)
        self.leURL.setObjectName(_fromUtf8("leURL"))
        self.formLayout.setWidget(1, QtGui.QFormLayout.FieldRole, self.leURL)
        self.leUser = QtGui.QLineEdit(self.groupBox)
        self.leUser.setObjectName(_fromUtf8("leUser"))
        self.formLayout.setWidget(2, QtGui.QFormLayout.FieldRole, self.leUser)
        self.label_3 = QtGui.QLabel(self.groupBox)
        self.label_3.setObjectName(_fromUtf8("label_3"))
        self.formLayout.setWidget(2, QtGui.QFormLayout.LabelRole, self.label_3)
        self.label_4 = QtGui.QLabel(self.groupBox)
        self.label_4.setObjectName(_fromUtf8("label_4"))
        self.formLayout.setWidget(3, QtGui.QFormLayout.LabelRole, self.label_4)
        self.lePassword = QtGui.QLineEdit(self.groupBox)
        self.lePassword.setEchoMode(QtGui.QLineEdit.Password)
        self.lePassword.setObjectName(_fromUtf8("lePassword"))
        self.formLayout.setWidget(3, QtGui.QFormLayout.FieldRole, self.lePassword)
        self.verticalLayout.addWidget(self.groupBox)
        self.buttonBox = QtGui.QDialogButtonBox(self.layoutWidget)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName(_fromUtf8("buttonBox"))
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(NewServiceConnectionDialog)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("accepted()")), NewServiceConnectionDialog.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("rejected()")), NewServiceConnectionDialog.reject)
        QtCore.QMetaObject.connectSlotsByName(NewServiceConnectionDialog)

    def retranslateUi(self, NewServiceConnectionDialog):
        NewServiceConnectionDialog.setWindowTitle(_translate("NewServiceConnectionDialog", "Crea una nuova connessione ad un json web service", None))
        self.groupBox.setTitle(_translate("NewServiceConnectionDialog", "Dettagli del web service", None))
        self.label.setText(_translate("NewServiceConnectionDialog", "Nome", None))
        self.label_2.setText(_translate("NewServiceConnectionDialog", "URL", None))
        self.label_3.setText(_translate("NewServiceConnectionDialog", "Gruppo", None))
        self.label_4.setText(_translate("NewServiceConnectionDialog", "Password", None))

