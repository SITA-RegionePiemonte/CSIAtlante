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

 Date                 : 2014-04-11
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
from ui_newconnection import Ui_NewConnectionDialog

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


class NewConnectionDialog(QDialog, Ui_NewConnectionDialog):
    def __init__(self, connectionName=""):
        QDialog.__init__(self)
        self.setupUi(self)
        self.origName = connectionName

    def accept(self):
        s = QSettings()
        self.leName.setText(self.formatConnectionName(self.leUsername.text(), self.leHost.text(), self.lePort.text(), self.leDatabase.text()))

        connName = self.leName.text()
        #if not connName.isEmpty(): Porting QGIS 2.0
        if connName is not None and connName != "":
            key = "/CSIAtlante/connections/" + connName

            # warn if entry was renamed to an existing connection
            if self.origName != connName and s.contains(key + "/host"):
                res = QMessageBox.warning(self,
                                          self.tr("Salva connessione"),
                                          #str(self.tr("Connessione %1 esistente : sovrascrivere?")).arg(connName),
                                          self.tr("Connessione " + connName + " esistente : sovrascrivere?"),
                                          QMessageBox.Ok | QMessageBox.Cancel)
                if res == QMessageBox.Cancel:
                    return

            # on rename delete original entry first
            #if not self.origName.isEmpty() and self.origName != connName: Porting QGIS 2.0
            if self.origName is not None and self.origName != "" and self.origName != connName:
                s.remove("/CSIAtlante/connections/" + self.origName)

            s.setValue(key + "/host", self.leHost.text().strip())  # trimmed()) Porting QGIS 2.0
            s.setValue(key + "/port", self.lePort.text().strip())  # trimmed()) Porting QGIS 2.0
            s.setValue(key + "/database", self.leDatabase.text().strip())  # trimmed()) Porting QGIS 2.0
            s.setValue(key + "/username", self.leUsername.text().strip())  # trimmed()) Porting QGIS 2.0
            s.setValue(key + "/password", self.lePassword.text().strip())  # trimmed()) Porting QGIS 2.0

            QDialog.accept(self)

    @pyqtSignature("reject()")
    def reject(self):
        QDialog.reject(self)

    def formatConnectionName(self, username, host, port, database):
        """
        Metodo che restituisce il nome di una connessione formattata come: user@host:port:DATABASE
        tutto lowercase eccetto il database che e' case sensitive
        @param username
        @param host
        @param port
        @param database
        """
        aux = "%s@%s:%s" % (username, host, port)
        aux = aux.lower()
        fcname = "%s:%s" % (aux, database)
        #fcname.encode('ascii', 'replace')
        #fcname = "%s@%s:%s\/%s" % (username, host, port, database)
        return str(fcname)
