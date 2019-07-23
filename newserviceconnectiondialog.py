# -*- coding: utf-8 -*-
"""
*******************************************
 Copyright: Regione Piemonte 2012-2019
 SPDX-Licene-Identifier: GPL-2.0-or-later
*******************************************
"""
"""
/***************************************************************************
 CSIAtlante
 Accesso organizzato a dati e geoservizi

 A QGIS plugin, designed for an organization where the Administrators of the
 Geographic Information System want to guide end users
 in organized access to the data and geo-services of their interest.

 Date                 : 2014-10-26
 copyright            : (C) 2012-2019 by Regione Piemonte
 author               : Enzo Ciarmoli (CSI Piemonte)
 email                : supporto.gis@csi.it

 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

from PyQt4.QtCore import QSettings, pyqtSignature
from PyQt4.QtGui import QDialog, QMessageBox
from ui_newserviceconnection import Ui_NewServiceConnectionDialog
import csiutils

PROJECT_NAME = "CSIAtlante"

# -----------------------------------------------------------------------------
# Porta di servizio per remote debug in Eclipse
s = QSettings()
REMOTE_DBG = s.value(''.join([PROJECT_NAME, "/debug"]), False, type=bool)
if REMOTE_DBG:
    try:
        import pydevd
    except ImportError:
        PYSRC_PATH = s.value(''.join([PROJECT_NAME, "/pysrc"]), "", type=unicode)
        if PYSRC_PATH != "":
            import sys
            # sys.path.append("c:\\eclipse\\eclipse-jee-juno-win32-x86_64\\plugins\\org.python.pydev_2.8.2.2013090511\\pysrc")
            sys.path.append(PYSRC_PATH)
            try:
                import pydevd  # @UnusedImport
            except ImportError:
                QMessageBox.information(None, "Warning", "Problema nell'import di pysrc per remote debug")
# -----------------------------------------------------------------------------


class NewServiceConnectionDialog(QDialog, Ui_NewServiceConnectionDialog):
    def __init__(self, connectionName=""):
        QDialog.__init__(self)
        self.setupUi(self)
        self.origName = connectionName

    def accept(self):
        s = QSettings()
        connName = self.leName.text()

        #if not connName.isEmpty(): Porting QGIS 2.0
        if connName is not None and connName != "":
            key = "/CSIAtlante/services/" + connName

            # warn if entry was renamed to an existing connection
            if self.origName != connName and s.contains(key + "/url"):
                res = QMessageBox.warning(self,
                                          self.tr("Salva connessione"),
                                          #str(self.tr("Connessione %1 esistente : sovrascrivere?")).arg(connName),
                                          self.tr("Connessione " + connName + " esistente : sovrascrivere?"),
                                          QMessageBox.Ok | QMessageBox.Cancel)
                if res == QMessageBox.Cancel:
                    return

            # on rename delete original entry first
            if self.origName is not None and self.origName != "" and self.origName != connName:
                s.remove("/CSIAtlante/services/" + self.origName)

            s.setValue(key + "/url", self.leURL.text().strip())
            s.setValue(key + "/usr", self.leUser.text().strip())
            s.setValue(key + "/pwd", self.lePassword.text().strip())

            # test su servizio di login per feedback
            url, usr, pwd = self.leURL.text().strip(), self.leUser.text().strip(), self.lePassword.text().strip()
            tab = 'login'
            cod = -1
            msg = ""
            errorCause = ""
            try:
                jsonObj = csiutils.GetGenericJSONObj(url, usr=usr, pwd=pwd, tab=tab)

                if 'cod' in jsonObj.keys():
                    cod = jsonObj['cod']
                if 'msg' in jsonObj.keys():
                    msg = jsonObj['msg']
                if 'errorCause' in jsonObj.keys():
                    errorCause = jsonObj['errorCause']

                if cod == 0:
                    QMessageBox.warning(self, self.tr("Verifica servizio login"), self.tr(msg))
                    pass
                elif cod == 1:
                    # uscita!
                    QMessageBox.warning(self, self.tr("Verifica servizio login"), self.tr(msg))
                    return

            except Exception, ex:
                txt = str(ex)
                QMessageBox.information(None, "Errore", \
                    "Impossibile leggere l'elenco dal servizio:\n%s \ntab: \n%s \nControllare la connessione di rete.\n[%s]" % (url, tab, txt))
                csiutils.Cursor.Restore()
                # no return procede oltre
                return

            #
            QDialog.accept(self)

    @pyqtSignature("reject()")
    def reject(self):
        QDialog.reject(self)
