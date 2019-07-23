# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_newconnection.ui'
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

class Ui_NewConnectionDialog(object):
    def setupUi(self, NewConnectionDialog):
        NewConnectionDialog.setObjectName(_fromUtf8("NewConnectionDialog"))
        NewConnectionDialog.resize(329, 332)
        self.layoutWidget = QtGui.QWidget(NewConnectionDialog)
        self.layoutWidget.setGeometry(QtCore.QRect(10, 10, 291, 251))
        self.layoutWidget.setObjectName(_fromUtf8("layoutWidget"))
        self.gridLayout = QtGui.QGridLayout(self.layoutWidget)
        self.gridLayout.setMargin(0)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.groupBox = QtGui.QGroupBox(self.layoutWidget)
        self.groupBox.setObjectName(_fromUtf8("groupBox"))
        self.layoutWidget1 = QtGui.QWidget(self.groupBox)
        self.layoutWidget1.setGeometry(QtCore.QRect(10, 23, 261, 164))
        self.layoutWidget1.setObjectName(_fromUtf8("layoutWidget1"))
        self.verticalLayout = QtGui.QVBoxLayout(self.layoutWidget1)
        self.verticalLayout.setMargin(0)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.label = QtGui.QLabel(self.layoutWidget1)
        self.label.setMinimumSize(QtCore.QSize(50, 0))
        self.label.setObjectName(_fromUtf8("label"))
        self.horizontalLayout.addWidget(self.label)
        self.leName = QtGui.QLineEdit(self.layoutWidget1)
        self.leName.setEnabled(False)
        self.leName.setObjectName(_fromUtf8("leName"))
        self.horizontalLayout.addWidget(self.leName)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.horizontalLayout_2 = QtGui.QHBoxLayout()
        self.horizontalLayout_2.setObjectName(_fromUtf8("horizontalLayout_2"))
        self.label_2 = QtGui.QLabel(self.layoutWidget1)
        self.label_2.setMinimumSize(QtCore.QSize(50, 0))
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.horizontalLayout_2.addWidget(self.label_2)
        self.leHost = QtGui.QLineEdit(self.layoutWidget1)
        self.leHost.setObjectName(_fromUtf8("leHost"))
        self.horizontalLayout_2.addWidget(self.leHost)
        self.verticalLayout.addLayout(self.horizontalLayout_2)
        self.horizontalLayout_3 = QtGui.QHBoxLayout()
        self.horizontalLayout_3.setObjectName(_fromUtf8("horizontalLayout_3"))
        self.label_3 = QtGui.QLabel(self.layoutWidget1)
        self.label_3.setMinimumSize(QtCore.QSize(50, 0))
        self.label_3.setObjectName(_fromUtf8("label_3"))
        self.horizontalLayout_3.addWidget(self.label_3)
        self.lePort = QtGui.QLineEdit(self.layoutWidget1)
        self.lePort.setObjectName(_fromUtf8("lePort"))
        self.horizontalLayout_3.addWidget(self.lePort)
        self.verticalLayout.addLayout(self.horizontalLayout_3)
        self.horizontalLayout_4 = QtGui.QHBoxLayout()
        self.horizontalLayout_4.setObjectName(_fromUtf8("horizontalLayout_4"))
        self.label_4 = QtGui.QLabel(self.layoutWidget1)
        self.label_4.setMinimumSize(QtCore.QSize(50, 0))
        self.label_4.setObjectName(_fromUtf8("label_4"))
        self.horizontalLayout_4.addWidget(self.label_4)
        self.leDatabase = QtGui.QLineEdit(self.layoutWidget1)
        self.leDatabase.setEchoMode(QtGui.QLineEdit.Normal)
        self.leDatabase.setObjectName(_fromUtf8("leDatabase"))
        self.horizontalLayout_4.addWidget(self.leDatabase)
        self.verticalLayout.addLayout(self.horizontalLayout_4)
        self.horizontalLayout_5 = QtGui.QHBoxLayout()
        self.horizontalLayout_5.setObjectName(_fromUtf8("horizontalLayout_5"))
        self.label_5 = QtGui.QLabel(self.layoutWidget1)
        self.label_5.setMinimumSize(QtCore.QSize(50, 0))
        self.label_5.setObjectName(_fromUtf8("label_5"))
        self.horizontalLayout_5.addWidget(self.label_5)
        self.leUsername = QtGui.QLineEdit(self.layoutWidget1)
        self.leUsername.setEchoMode(QtGui.QLineEdit.Normal)
        self.leUsername.setObjectName(_fromUtf8("leUsername"))
        self.horizontalLayout_5.addWidget(self.leUsername)
        self.verticalLayout.addLayout(self.horizontalLayout_5)
        self.horizontalLayout_6 = QtGui.QHBoxLayout()
        self.horizontalLayout_6.setObjectName(_fromUtf8("horizontalLayout_6"))
        self.label_6 = QtGui.QLabel(self.layoutWidget1)
        self.label_6.setMinimumSize(QtCore.QSize(50, 0))
        self.label_6.setObjectName(_fromUtf8("label_6"))
        self.horizontalLayout_6.addWidget(self.label_6)
        self.lePassword = QtGui.QLineEdit(self.layoutWidget1)
        self.lePassword.setEchoMode(QtGui.QLineEdit.Password)
        self.lePassword.setObjectName(_fromUtf8("lePassword"))
        self.horizontalLayout_6.addWidget(self.lePassword)
        self.verticalLayout.addLayout(self.horizontalLayout_6)
        self.gridLayout.addWidget(self.groupBox, 0, 0, 1, 1)
        self.buttonBox = QtGui.QDialogButtonBox(self.layoutWidget)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName(_fromUtf8("buttonBox"))
        self.gridLayout.addWidget(self.buttonBox, 1, 0, 1, 1)

        self.retranslateUi(NewConnectionDialog)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("accepted()")), NewConnectionDialog.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("rejected()")), NewConnectionDialog.reject)
        QtCore.QMetaObject.connectSlotsByName(NewConnectionDialog)

    def retranslateUi(self, NewConnectionDialog):
        NewConnectionDialog.setWindowTitle(_translate("NewConnectionDialog", "Crea una nuova connessione ad un db postgre", None))
        self.groupBox.setTitle(_translate("NewConnectionDialog", "Dettagli della connessione DB", None))
        self.label.setText(_translate("NewConnectionDialog", "Nome", None))
        self.label_2.setText(_translate("NewConnectionDialog", "Host", None))
        self.label_3.setText(_translate("NewConnectionDialog", "Port", None))
        self.label_4.setText(_translate("NewConnectionDialog", "Database", None))
        self.label_5.setText(_translate("NewConnectionDialog", "Username", None))
        self.label_6.setText(_translate("NewConnectionDialog", "Password", None))

