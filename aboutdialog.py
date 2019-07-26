# -*- coding: utf-8 -*-
"""
*******************************************
 Copyright: Regione Piemonte 2012-2019
 SPDX-License-Identifier: GPL-2.0-or-later
*******************************************
"""
"""
/***************************************************************************
 CSIAtlante
 Accesso organizzato a dati e geoservizi

 A QGIS plugin, designed for an organization where the Administrators of the
 Geographic Information System want to guide end users
 in organized access to the data and geo-services of their interest.

 Date                 : 2015-02-05
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

from qgis.PyQt.QtCore import QSettings
from qgis.PyQt.QtWidgets import QMessageBox, QDialog
from qgis.PyQt.QtGui import QPixmap
from .ui_about import Ui_AboutDialog
import os

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


class AboutDialog(QDialog, Ui_AboutDialog):
    """
    Classe di specializzazione del dialogo ui_about.ui creato con Qt Designer
    """
    def __init__(self, parent=None):
        """
        Estende QDialog
        """
        QDialog.__init__(self, parent)
        self.setupUi(self)

        metadatafile = os.path.join(os.path.abspath(os.path.dirname(__file__)), "metadata.txt")
        s = QSettings(metadatafile, QSettings.IniFormat)
        s.setIniCodec('UTF-8')
        s.sync()

        version = s.value("version")
        name = s.value("name")
        description = s.value("description")

        self.title.setText(name)
        fulldescription = ''.join([description, '\n\n', 'versione: ', version])
        self.description.setText(fulldescription)

        self.logo.setPixmap(QPixmap(":/csi/logo"))
