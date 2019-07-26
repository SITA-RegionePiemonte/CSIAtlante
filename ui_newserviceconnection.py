# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_newserviceconnection.ui'
#
# Created by: PyQt5 UI code generator 5.9
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_NewServiceConnectionDialog(object):
    def setupUi(self, NewServiceConnectionDialog):
        NewServiceConnectionDialog.setObjectName("NewServiceConnectionDialog")
        NewServiceConnectionDialog.resize(400, 212)
        self.layoutWidget = QtWidgets.QWidget(NewServiceConnectionDialog)
        self.layoutWidget.setGeometry(QtCore.QRect(9, 9, 371, 191))
        self.layoutWidget.setObjectName("layoutWidget")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.layoutWidget)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.groupBox = QtWidgets.QGroupBox(self.layoutWidget)
        self.groupBox.setObjectName("groupBox")
        self.formLayout = QtWidgets.QFormLayout(self.groupBox)
        self.formLayout.setObjectName("formLayout")
        self.label = QtWidgets.QLabel(self.groupBox)
        self.label.setObjectName("label")
        self.formLayout.setWidget(0, QtWidgets.QFormLayout.LabelRole, self.label)
        self.leName = QtWidgets.QLineEdit(self.groupBox)
        self.leName.setObjectName("leName")
        self.formLayout.setWidget(0, QtWidgets.QFormLayout.FieldRole, self.leName)
        self.label_2 = QtWidgets.QLabel(self.groupBox)
        self.label_2.setObjectName("label_2")
        self.formLayout.setWidget(1, QtWidgets.QFormLayout.LabelRole, self.label_2)
        self.leURL = QtWidgets.QLineEdit(self.groupBox)
        self.leURL.setObjectName("leURL")
        self.formLayout.setWidget(1, QtWidgets.QFormLayout.FieldRole, self.leURL)
        self.leUser = QtWidgets.QLineEdit(self.groupBox)
        self.leUser.setObjectName("leUser")
        self.formLayout.setWidget(2, QtWidgets.QFormLayout.FieldRole, self.leUser)
        self.label_3 = QtWidgets.QLabel(self.groupBox)
        self.label_3.setObjectName("label_3")
        self.formLayout.setWidget(2, QtWidgets.QFormLayout.LabelRole, self.label_3)
        self.label_4 = QtWidgets.QLabel(self.groupBox)
        self.label_4.setObjectName("label_4")
        self.formLayout.setWidget(3, QtWidgets.QFormLayout.LabelRole, self.label_4)
        self.lePassword = QtWidgets.QLineEdit(self.groupBox)
        self.lePassword.setEchoMode(QtWidgets.QLineEdit.Password)
        self.lePassword.setObjectName("lePassword")
        self.formLayout.setWidget(3, QtWidgets.QFormLayout.FieldRole, self.lePassword)
        self.verticalLayout.addWidget(self.groupBox)
        self.buttonBox = QtWidgets.QDialogButtonBox(self.layoutWidget)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(NewServiceConnectionDialog)
        self.buttonBox.accepted.connect(NewServiceConnectionDialog.accept)
        self.buttonBox.rejected.connect(NewServiceConnectionDialog.reject)
        QtCore.QMetaObject.connectSlotsByName(NewServiceConnectionDialog)

    def retranslateUi(self, NewServiceConnectionDialog):
        _translate = QtCore.QCoreApplication.translate
        NewServiceConnectionDialog.setWindowTitle(_translate("NewServiceConnectionDialog", "Crea una nuova connessione ad un json web service"))
        self.groupBox.setTitle(_translate("NewServiceConnectionDialog", "Dettagli del web service"))
        self.label.setText(_translate("NewServiceConnectionDialog", "Nome"))
        self.label_2.setText(_translate("NewServiceConnectionDialog", "URL"))
        self.label_3.setText(_translate("NewServiceConnectionDialog", "Gruppo"))
        self.label_4.setText(_translate("NewServiceConnectionDialog", "Password"))

