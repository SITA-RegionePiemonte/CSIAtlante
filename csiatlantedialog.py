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

 Date                 : 2015-10-28
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

from qgis.PyQt import QtGui, QtCore, QtWidgets
from qgis.PyQt.QtCore import QUrl, QSettings, Qt, QIODevice, QFile
from qgis.PyQt.QtWidgets import QTreeWidgetItem, QTreeWidgetItemIterator
from qgis.PyQt.QtWidgets import QMessageBox
from qgis.PyQt.QtWidgets import QDockWidget
from qgis.PyQt.QtWidgets import QDialog
from qgis.utils import iface
from qgis.gui import QgsMessageBar  # @UnusedImport

from .ui_csiatlante import Ui_CsiAtlante
from .sgatools import ChartMapToolIdentify  # COMMNENTARE OLD! 23/03/2016

import time
import os
import bz2
import binascii
import logging
from collections import OrderedDict

from .newserviceconnectiondialog import NewServiceConnectionDialog
from .newconnectiondialog import NewConnectionDialog
from .aboutdialog import AboutDialog

PROJECT_NAME = "CSIAtlante"
MAIN_MODULE_NAME = "csiatlante"
FOLDER_NAME = __name__.split('.')[0]
MODULE_NAME = __name__.split('.')[1]
MAIN_MODULE = "%s.%s" % (FOLDER_NAME, MAIN_MODULE_NAME)
LOGGER_NAME = MAIN_MODULE
LOGGER = logging.getLogger()

try:
    module = __import__(MAIN_MODULE)
    class_logger = getattr(module, "csiLogger")
    LOGGER = class_logger(LOGGER_NAME)
    LOGGER.debug('### CsiAtlanteDialog logger from: CSIAtlante.csiatlante.csiLogger')
except Exception as ex:
    LOGGER = logging.getLogger()
    LOGGER.debug('### CsiAtlanteDialog logger from: logging.getLogger()')

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


#2to3 class CsiAtlanteDialog(QtGui.QDockWidget):
class CsiAtlanteDialog(QDockWidget):
    """
    Classe GUI principale del plugin
    """
    def __init__(self, csiAtlantePlugin):

        # Initialize singleton Logger and keep reference
        LOGGER = csiAtlantePlugin.logger
        LOGGER.debug('### CsiAtlanteDialog __init__ ### BEGIN')

        QDialog.__init__(self)
        self.csiAtlante = csiAtlantePlugin

        # Set up the user interface from Designer.
        self.ui = Ui_CsiAtlante()
        self.ui.setupUi(self)

        # istanzia gestore configurazioni
        self.gestoreCONF = GestoreTabObject(ConfTabObject(self.ui), self.ui, self.csiAtlante)

        # istanzia gestori dei tab
        self.gestorePROGETTI = GestoreTabObject(ProgettiTabObject(self.ui), self.ui, self.csiAtlante)
        self.gestoreWMS = GestoreTabObject(WmsTabObject(self.ui), self.ui, self.csiAtlante)
        self.gestoreVECTOR = GestoreTabObject(VectorTabObject(self.ui), self.ui, self.csiAtlante)
        self.gestoreRASTER = GestoreTabObject(RasterTabObject(self.ui), self.ui, self.csiAtlante)
        self.gestoreCSW = GestoreTabObject(CswTabObject(self.ui), self.ui, self.csiAtlante)
        self.gestoreINDICA = GestoreTabObject(IndicaTabObject(self.ui), self.ui, self.csiAtlante)

        self.manageGui()

        # activateTab deve agire dopo il manageGui se no fa riferimento a indici inconsistenti
        LOGGER.debug('### CsiAtlanteDialog __init__ ### activateTab ')
        if hasattr(self.ui, 'tabWidget'):
            #QtCore.QObject.connect(self.ui.tabWidget, QtCore.SIGNAL("currentChanged( int )"), self.activateTab)
            self.ui.tabWidget.currentChanged[int].connect(self.activateTab)

#         # Imposta il focus di visualizzazione sul tab di default
#         indexTabDefault = self.ui.tabWidget.indexOf(self.ui.tabPostgis)    # TODO: ricavare da settings
#         QMessageBox.information(None, "__init__", "DEBUG\n indexTabDefault: %d" % (indexTabDefault), QMessageBox.Ok)
#         LOGGER.debug('__init__ indexTabDefault: %d' % (indexTabDefault))
#         self.ui.tabWidget.setCurrentIndex(indexTabDefault)

    def manageGui(self):
        """
        Gestione della GUI e attivazione/disattivazione di componenti
        comportamento del plugin ,  1 = dinamico, 0 = locale (default)
        """
        LOGGER.debug('manageGui BEGIN')

        s = QSettings()
        behaviour = s.value("CSIAtlante/conf/behaviour", 0, type=int)
        self.csiAtlante.behaviour = behaviour

        # imposta il check per il comportamento locale (default) oppure dinamico
        if (behaviour == 0):
            ConfTabObject(self.ui).chkLocale.setCheckState(QtCore.Qt.Checked)
        else:
            ConfTabObject(self.ui).chkLocale.setCheckState(QtCore.Qt.Unchecked)

        # Rimuove *a codice* il tab CSW
        indexTabCSW = self.ui.tabWidget.indexOf(self.ui.tabCSW)
        self.ui.tabWidget.removeTab(indexTabCSW)

#         # Imposta il focus di visualizzazione sul tab di default
#         indexTabDefault = self.ui.tabWidget.indexOf(self.ui.tabPostgis)    # TODO: ricavare da settings
#         QMessageBox.information(None, "manageGui", "DEBUG\n indexTabDefault: %d' % (indexTabDefault)", QMessageBox.Ok)
#         LOGGER.debug('manageGui indexTabDefault: %d' % (indexTabDefault))
#         self.ui.tabWidget.setCurrentIndex(indexTabDefault)

    def disconnect(self):
        """
        disconnect
        """
        # old: QtCore.QObject.disconnect(self.ui.tabWidget, QtCore.SIGNAL("currentChanged ( int )"), self.activateTab)
        self.ui.tabWidget.currentChanged[int].disconnect(self.activateTab)  
        self.gestoreINDICA.disconnect()
        self.gestoreCSW.disconnect()
        self.gestorePROGETTI.disconnect()
        self.gestoreWMS.disconnect()
        self.gestoreRASTER.disconnect()
        self.gestoreVECTOR.disconnect()
        self.gestoreCONF.disconnect()

    def connect(self):
        """
        connect
        """
        # old: QtCore.QObject.connect(self.ui.tabWidget, QtCore.SIGNAL("currentChanged ( int )"), self.activateTab)
        self.ui.tabWidget.currentChanged[int].connect(self.activateTab)  
        self.gestoreCONF.connect()
        self.gestoreVECTOR.connect()
        self.gestoreRASTER.connect()
        self.gestoreWMS.connect()
        self.gestorePROGETTI.connect()
        self.gestoreCSW.connect()
        self.gestoreINDICA.connect()

    def closeEvent(self, evt):
        """
        closeEvent
        deprecated
        """
        # self.disconnect()
        pass

    def deselectAll(self):
        """
        deselectAll
        """
        self.gestoreVECTOR.deselectAll()
        self.gestoreRASTER.deselectAll()
        self.gestoreWMS.deselectAll()
        self.gestorePROGETTI.deselectAll()
        self.gestoreCSW.deselectAll()
        self.gestoreINDICA.deselectAll()

    def deselectAllButIndica(self):
        """
        deselectAll eccetto il tab Indica
        """
        self.gestoreVECTOR.deselectAll()
        self.gestoreRASTER.deselectAll()
        self.gestoreWMS.deselectAll()
        self.gestorePROGETTI.deselectAll()
        self.gestoreCSW.deselectAll()

    def wms_getGeneralSettings(self):
        """
        Restituisce una lista di settaggi generici dalla UI wms
        self.ui.wms_groupedCheck.checkState()
        self.ui.wms_crsCombo.currentText()
        self.ui.wms_formatoCombo.currentText()
        self.ui.wms_ckLayerAbilitati.isChecked()
        not self.ui.wms_ckDescrizione.isChecked()
        self.ui.wms_ckStampabile.isChecked()

        @return: list
        """
        return [self.ui.wms_groupedCheck.checkState(), self.ui.wms_crsCombo.currentText(),
                self.ui.wms_formatoCombo.currentText(), self.ui.wms_ckLayerAbilitati.isChecked(),
                not self.ui.wms_ckDescrizione.isChecked(), self.ui.wms_ckStampabile.isChecked()]

    def dati_getAbilitati(self):
        return self.ui.dati_ckLayerAbilitati.isChecked()

    def indica_getAbilitati(self):
        return self.ui.indica_ckLayerAbilitati.isChecked()

    def indica_getStoricizzati(self):
        return self.ui.indica_ckSerieStorica.isChecked()

    def raster_getAbilitati(self):
        return self.ui.raster_ckLayerAbilitati.isChecked()

    def activateTab(self, id_tab):
        """
        Slot to receive currentChanged signal when switching target tab.
        @param id_tab: the index of the tab, type as int.
        """
        LOGGER.debug('activateTab - id_tab: %d' % (id_tab))

        # ----------------------
        # gestione dinamica GUI
        # ----------------------

        # tabConf --> disabilita i buttons aggiorna e carica
        if self.ui.tabWidget.currentWidget() == self.ui.tabConf:
            self.ui.btAggiorna.setEnabled(False)
            self.ui.btCarica.setEnabled(False)
        else:
            self.ui.btAggiorna.setEnabled(True)
            self.ui.btCarica.setEnabled(True)

        # tabWMS --> cambia text del bottone aggiorna
        if self.ui.tabWidget.currentWidget() == self.ui.tabWMS:
            self.ui.btAggiorna.setText("Aggiorna Cache")
        else:
            self.ui.btAggiorna.setText("Aggiorna Elenco")

        # tabIndica --> abilita il button Ripulisci dati toc
        if self.ui.tabWidget.currentWidget() == self.ui.tabIndica:
            self.ui.btSvuotaToc.setEnabled(True)
        else:
            self.ui.btSvuotaToc.setEnabled(False)

        # ------------------------------
        # gestione dinamica contenitori
        # ------------------------------

        # tabProgetti dopo che il servizio di connessione e' cambiato --> deve aggiornare il contenuto e rimettere il flag del tab a False
        if self.ui.tabWidget.currentWidget() == self.ui.tabProgetti and self.csiAtlante.servicechanged_tabProgetti == True:
            if (self.csiAtlante.servicechanged_not_initial):
                self.csiAtlante.slot_aggiorna_elenco()
                self.csiAtlante.servicechanged_tabProgetti = False

        # tabWMS dopo che il servizio di connessione e' cambiato --> deve aggiornare il contenuto e rimettere il flag del tab a False
        if self.ui.tabWidget.currentWidget() == self.ui.tabWMS and self.csiAtlante.servicechanged_tabWMS == True:
            if (self.csiAtlante.servicechanged_not_initial):
                self.csiAtlante.useWmsCache = True
                self.csiAtlante.slot_aggiorna_elenco()
                self.csiAtlante.servicechanged_tabWMS = False

        # tabPostgis dopo che il servizio di connessione e' cambiato --> deve aggiornare il contenuto e rimettere il flag del tab a False
        if self.ui.tabWidget.currentWidget() == self.ui.tabPostgis and self.csiAtlante.servicechanged_tabPostgis == True:
            if (self.csiAtlante.servicechanged_not_initial):
                self.csiAtlante.slot_aggiorna_elenco()
                self.csiAtlante.servicechanged_tabPostgis = False

        # tabIndica dopo che il servizio di connessione e' cambiato --> deve aggiornare il contenuto e rimettere il flag del tab a False
        if self.ui.tabWidget.currentWidget() == self.ui.tabIndica and self.csiAtlante.servicechanged_tabIndica == True:
            if (self.csiAtlante.servicechanged_not_initial):
                self.csiAtlante.slot_aggiorna_elenco()
                self.csiAtlante.servicechanged_tabIndica = False

        # tabRaster dopo che il servizio di connessione e' cambiato --> deve aggiornare il contenuto e rimettere il flag del tab a False
        if self.ui.tabWidget.currentWidget() == self.ui.tabRaster and self.csiAtlante.servicechanged_tabRaster == True:
            if (self.csiAtlante.servicechanged_not_initial):
                self.csiAtlante.slot_aggiorna_elenco()
                self.csiAtlante.servicechanged_tabRaster = False

    def keyPressEvent(self, e):
        if self.ui.tabWidget.currentWidget() == self.ui.tabWMS:
            self.gestoreWMS.categoryChanged(0)
        if self.ui.tabWidget.currentWidget() == self.ui.tabPostgis:
            self.gestoreVECTOR.categoryChanged(0)
        if self.ui.tabWidget.currentWidget() == self.ui.tabProgetti:
            self.gestorePROGETTI.categoryChanged(0)
        if self.ui.tabWidget.currentWidget() == self.ui.tabCSW:
            self.gestoreCSW.categoryChanged(0)
        if self.ui.tabWidget.currentWidget() == self.ui.tabIndica:
            self.gestoreINDICA.categoryChanged(0)
        if self.ui.tabWidget.currentWidget() == self.ui.tabRaster:
            self.gestoreRASTER.categoryChanged(0)

    def getServiceName(self):
        name = self.gestoreCONF.getServiceName()
        return name

    def getServiceUrlUsrPwd(self):
        url, usr, pwd = self.gestoreCONF.getServiceUrlUsrPwd()
        return url, usr, pwd

    def getServiceReadQmlUrl(self):
        url = self.gestoreCONF.getServiceReadQmlUrl()
        return url

    def getServiceReadProjectUrl(self):
        url = self.gestoreCONF.getServiceReadProjectUrl()
        return url

    def getServiceChartUrl(self):
        url = self.gestoreCONF.getServiceChartUrl()
        return url

    def getServiceGraphUrl(self):
        url = self.gestoreCONF.getServiceGraphUrl()
        return url

    def getServiceWmsCacheValues(self):
        cached, cachedate, cachefile = self.gestoreCONF.getServiceWmsCacheValues()
        return cached, cachedate, cachefile

    def setServiceWmsCacheValues(self, cached, cacheDate, cacheFile):
        self.gestoreCONF.setServiceWmsCacheValues(cached, cacheDate, cacheFile)


class TabObject(object):
    """
    SuperClasse per oggetto Tab
    """
    def __init__(self, ui):
        self.ui = ui
        self.name = "tab"
        self.treeOnlyOneItemSelected = False
        self.bUpdateClickChildTreeItems = False
#         self.treeWidget = None
#         self.cboCategory = None
#         self.btCerca = None
#         self.btApriAlbero = None
#         self.btChiudiAlbero = None
#         self.btMetadati = None
#         self.crsCombo = None
#         self.formatoCombo = None
#         self.txFiltro = None
#         self.cboServiceConnections = None
#         self.btnAbout = None
#         self.btnServiceNew = None
#         self.btnServiceEdit = None
#         self.btnServiceDelete = None
#         self.btnServiceSaveFile = None
#         self.btnServiceLoadFile = None
#         self.cboConnections = None
#         self.btnNew = None
#         self.btnEdit = None
#         self.btnDelete = None
#         self.btnSaveFile = None
#         self.btnLoadFile = None
#         self.chkLocale = None
#         self.chkTabProgetti = None
#         self.chkTabPostgis = None
#         self.chkTabRaster = None
#         self.chkTabWMS = None
#         self.chkTabCSW = None
#         self.tabProgetti = self.ui.tabProgetti
#         self.tabPostgis = self.ui.tabPostgis
#         self.tabRaster = self.ui.tabRaster
#         self.tabWMS = self.ui.tabWMS
#         self.tabCSW = self.ui.tabCSW
#         self.tableWidgetConnections = None    # future
#
#     def getLayerDescription(self, layer):
#         return ''
#
#     def getLayerChildren(self, layer):
#         return None
#
#     def getLayerMetadataURL(self, layer):
#         return None
#
#     def getLayerCategory(self, layer):
#         return None

    def objectName(self):
        return self.name


class WmsTabObject(TabObject):
    """
    Classe WmsTabObject che estende TabObject
    """
    def __init__(self, ui):
        super(WmsTabObject, self).__init__(ui)
        self.name = self.ui.tabWMS.objectName()
        self.treeWidget = self.ui.wms_treeWidget
        self.cboCategory = self.ui.wms_cboCategory
        self.btCerca = self.ui.wms_btCerca
        self.btApriAlbero = self.ui.wms_btApriAlbero
        self.btChiudiAlbero = self.ui.wms_btChiudiAlbero
        self.btMetadati = self.ui.wms_btMetadati
        self.crsCombo = self.ui.wms_crsCombo
        self.formatoCombo = self.ui.wms_formatoCombo
        self.bUpdateClickChildTreeItems = True
        self.txFiltro = self.ui.wms_txFiltro

    def getLayerDescription(self, layer):
        try:
            return layer.title
        except:
            return layer.name

    def getLayerChildren(self, layer):
        return layer.layers

    def getLayerMetadataURL(self, layer):
        return layer.getMetadataURL()

    def getLayerCategory(self, layer):
        return layer.category


class VectorTabObject(TabObject):
    """
    Classe VectorTabObject che estende TabObject
    """
    def __init__(self, ui):
        super(VectorTabObject, self).__init__(ui)
        self.name = self.ui.tabPostgis.objectName()
        self.treeWidget = self.ui.dati_treeWidget
        self.cboCategory = self.ui.dati_cboCategory
        self.btCerca = self.ui.dati_btCerca
        self.btApriAlbero = self.ui.dati_btApriAlbero
        self.btChiudiAlbero = self.ui.dati_btChiudiAlbero
        self.btMetadati = self.ui.dati_btMetadati
        self.bUpdateClickChildTreeItems = True
        self.txFiltro = self.ui.dati_txFiltro

    def getLayerDescription(self, layer):
        return layer.nome

    def getLayerChildren(self, layer):
        return layer.children

    def getLayerMetadataURL(self, layer):
        return layer.urlmetadati

    def getLayerCategory(self, layer):
        return layer.category


class IndicaTabObject(TabObject):
    """
    Classe IndicaTabObject che estende TabObject
    """
    def __init__(self, ui):
        super(IndicaTabObject, self).__init__(ui)
        self.name = self.ui.tabIndica.objectName()
        self.treeWidget = self.ui.indica_treeWidget
        self.cboCategory = self.ui.indica_cboCategory
        self.cboUnita = self.ui.indica_cboUnita
        self.cboPeriodicita = self.ui.indica_cboPeriodicita
        #self.btSerieStorica = self.ui.indica_btSerieStorica
        self.btDeseleziona = self.ui.indica_btDeseleziona
        self.btCerca = self.ui.indica_btCerca
        self.btApriAlbero = self.ui.indica_btApriAlbero
        self.btChiudiAlbero = self.ui.indica_btChiudiAlbero
        self.btMetadati = self.ui.indica_btMetadati
        self.bUpdateClickChildTreeItems = True
        self.txFiltro = self.ui.indica_txFiltro
        self.ckSerieStorica = self.ui.indica_ckSerieStorica
        self.ckLayerAbilitati = self.ui.indica_ckLayerAbilitati

    def getLayerDescription(self, layer):
        return layer.nome

    def getLayerUnita(self, layer):
        return layer.unita

    def getLayerPeriodicita(self, layer):
        return layer.periodicita

    def getLayerChildren(self, layer):
        ret = None
        if hasattr(layer, 'children'):
            ret = layer.children
        return ret

    def getLayerMetadataURL(self, layer):
        return layer.urlmetadati

    def getLayerCategory(self, layer):
        return layer.category

#    def getLayerUnita(self, layer):
#         ret = None
#         if hasattr(layer, 'unita'):
#             ret = layer.unita
#         return ret


class RasterTabObject(TabObject):
    """
    Classe RasterTabObject che estende TabObject
    """
    def __init__(self, ui):
        super(RasterTabObject, self).__init__(ui)
        self.name = self.ui.tabRaster.objectName()
        self.treeWidget = self.ui.raster_treeWidget
        self.cboCategory = self.ui.raster_cboCategory
        self.btCerca = self.ui.raster_btCerca
        self.btApriAlbero = self.ui.raster_btApriAlbero
        self.btChiudiAlbero = self.ui.raster_btChiudiAlbero
        self.btMetadati = self.ui.raster_btMetadati
        self.bUpdateClickChildTreeItems = True
        self.txFiltro = self.ui.raster_txFiltro

    def getLayerDescription(self, layer):
        return layer.nome

    def getLayerChildren(self, layer):
        return layer.children

    def getLayerMetadataURL(self, layer):
        return layer.urlmetadati

    def getLayerCategory(self, layer):
        return layer.category


class ProgettiTabObject(TabObject):
    """
    Classe ProgettiTabObject che estende TabObject
    """
    def __init__(self, ui):
        super(ProgettiTabObject, self).__init__(ui)
        self.name = self.ui.tabProgetti.objectName()
        self.treeWidget = self.ui.prj_treeWidget
        self.treeOnlyOneItemSelected = True
        self.cboCategory = self.ui.prj_cboCategory
        self.btCerca = self.ui.prj_btCerca
        self.btApriAlbero = self.ui.prj_btApriAlbero
        self.btChiudiAlbero = self.ui.prj_btChiudiAlbero

        self.bUpdateClickChildTreeItems = True
        self.txFiltro = self.ui.prj_txFiltro

    def getLayerDescription(self, layer):
        return layer.nome

    def getLayerChildren(self, layer):
        return layer.children

    def getLayerCategory(self, layer):
        return layer.category


class CswTabObject(TabObject):
    """
    Classe CswTabObject che estende TabObject
    """
    def __init__(self, ui):
        super(CswTabObject, self).__init__(ui)
        self.name = self.ui.tabCSW.objectName()
        self.treeWidget = self.ui.csw_treeWidget
        self.cboCategory = self.ui.csw_cboCategory
        self.btCerca = self.ui.csw_btCerca
        self.btApriAlbero = self.ui.csw_btApriAlbero
        self.btChiudiAlbero = self.ui.csw_btChiudiAlbero
        self.btMetadati = self.ui.csw_btMetadati
        self.bUpdateClickChildTreeItems = True
        self.txFiltro = self.ui.csw_txFiltro

    def getLayerDescription(self, layer):
        try:
            return layer.title
        except:
            return layer.name

    def getLayerChildren(self, layer):
        return layer.layers

    def getLayerMetadataURL(self, layer):
        return layer.getMetadataURL()

    def getLayerCategory(self, layer):
        return layer.category


class ConfTabObject(TabObject):
    """
    Classe ConfTabObject che estende TabObject
    """
    def __init__(self, ui):
        super(ConfTabObject, self).__init__(ui)
        self.cboServiceConnections = self.ui.conf_cboServiceConnections
        self.btnAbout = self.ui.conf_btnAbout
        self.btnServiceNew = self.ui.conf_btnServiceNew
        self.btnServiceEdit = self.ui.conf_btnServiceEdit
        self.btnServiceDelete = self.ui.conf_btnServiceDelete
        self.btnServiceSaveFile = self.ui.conf_btnServiceSaveFile
        self.btnServiceLoadFile = self.ui.conf_btnServiceLoadFile
        self.cboConnections = self.ui.conf_cboConnections
        self.btnNew = self.ui.conf_btnNew
        self.btnEdit = self.ui.conf_btnEdit
        self.btnDelete = self.ui.conf_btnDelete
        self.btnSaveFile = self.ui.conf_btnSaveFile
        self.btnLoadFile = self.ui.conf_btnLoadFile
        self.chkLocale = self.ui.conf_chkLocale
        self.groupBoxServiceConnections = self.ui.groupBoxServiceConnections
        self.groupBoxConnections = self.ui.groupBoxConnections
#         self.groupBoxCheckTab = self.ui.groupBoxCheckTab
#         self.chkTabProgetti = self.ui.conf_chkTabProgetti
#         self.chkTabPostgis = self.ui.conf_chkTabPostgis
#         self.chkTabRaster = self.ui.conf_chkTabRaster
#         self.chkTabWMS = self.ui.conf_chkTabWMS
#         self.chkTabCSW = self.ui.conf_chkTabCSW
#         self.chkTabIndica = self.ui.conf_chkTabIndica


class GestoreTabObject(object):
    """
    Classe gestore di un tabObject
    """
    def __init__(self, tabObject, ui, csiAtlantePlugin):
        """
        @param tabObject
        @param ui
        @param csiAtlantePlugin
        """
        LOGGER.debug('GestoreTabObject __init__ - %s' % (tabObject.objectName()))
        self.ui = ui
        self.tabObj = tabObject
        self.csiAtlante = csiAtlantePlugin
        self.nextClick = 0
        # i dictionary devono essere allineati con quanto presente in ui
        # l'ordine e' importamte ne definisce anche la posizione assoluta
        # la key dei dictionary è anche il nome dell'oggetto ui -->es : self.ui.tabPostgis
        # i dictionary sono ridondanti, poteva bastarne anche solo uno o una lista di tuple, ma cosi' e' più leggibile
        #
        # @TODO:
        # valutare se mantenere i dictionary assoluti o se ridefinirli in base alla risposta del servizio di conf
        #
        #self.indexTabDict = {'tabProgetti': 0, 'tabPostgis': 1, 'tabRaster': 2, 'tabWMS': 3, 'tabIndica': 4, 'tabIndicaGeo': 5, 'tabWFS': 6, 'tabTMS': 7, 'tabConf': 8, 'tabCSW': 9}
        #self.nameTabDict = {'tabProgetti': 'Progetti', 'tabPostgis': 'Vector', 'tabRaster': 'Raster', 'tabWMS': 'WMS', 'tabIndica': 'Indicatori', 'tabIndicaGeo': 'IndicatoriGeo', 'tabWFS': 'WFS', 'tabTMS': 'TMS', 'tabConf': 'Impostazioni', 'tabCSW': 'CSW'}
        self.indexTabDict = OrderedDict([('tabProgetti', 0), ('tabPostgis', 1), ('tabRaster', 2), ('tabWMS', 3), ('tabIndica', 4), ('tabIndicaGeo', 5), ('tabWFS', 6), ('tabTMS', 7), ('tabConf', 8), ('tabCSW', 9)])
        self.nameTabDict = OrderedDict([('tabProgetti', 'Progetti'), ('tabPostgis', 'Vector'), ('tabRaster', 'Raster'), ('tabWMS', 'WMS'), ('tabIndica', 'Indicatori'), ('tabIndicaGeo', 'IndicatoriGeo'), ('tabWFS', 'WFS'), ('tabTMS', 'TMS'), ('tabConf', 'Impostazioni'), ('tabCSW', 'CSW')])

        self.serviceName = None
        self.serviceUrl = None
        self.serviceUsr = None
        self.servicePwd = None
        self.serviceWmsCached = None
        self.serviceWmsCacheDate = None
        self.serviceWmsCacheFile = None
        self.serviceReadQmlUrl = None
        self.serviceReadProjectUrl = None
        self.connect()

    def connect(self):
        """ Connecting signals and slots with PyQt
        old style:    QtCore.QObject.connect(self.tabObj.cboServiceConnections, QtCore.SIGNAL("activated(int)"), self.selectedServiceConnections)
        new style:    self.tabObj.cboServiceConnections.activated[int].connect(self.selectedServiceConnections)
        """
        if hasattr(self.tabObj, 'cboServiceConnections'):
            # old: QtCore.QObject.connect(self.tabObj.cboServiceConnections, QtCore.SIGNAL("activated(int)"), self.selectedServiceConnections)
            self.tabObj.cboServiceConnections.activated[int].connect(self.selectedServiceConnections)
        if hasattr(self.tabObj, 'cboServiceConnections'):
            # old: QtCore.QObject.connect(self.tabObj.cboServiceConnections, QtCore.SIGNAL("currentIndexChanged(int)"), self.changedServiceConnections)
            self.tabObj.cboServiceConnections.currentIndexChanged[int].connect(self.changedServiceConnections)
        if hasattr(self.tabObj, 'btnAbout'):
            # old: QtCore.QObject.connect(self.tabObj.btnAbout, QtCore.SIGNAL("clicked()"), self.showAbout)
            self.tabObj.btnAbout.clicked.connect(self.showAbout)
        if hasattr(self.tabObj, 'btnServiceNew'):
            # old: QtCore.QObject.connect(self.tabObj.btnServiceNew, QtCore.SIGNAL("clicked()"), self.newServiceConnection)
            self.tabObj.btnServiceNew.clicked.connect(self.newServiceConnection)
        if hasattr(self.tabObj, 'btnServiceEdit'):
            # old: QtCore.QObject.connect(self.tabObj.btnServiceEdit, QtCore.SIGNAL("clicked()"), self.editServiceConnection)
            self.tabObj.btnServiceEdit.clicked.connect(self.editServiceConnection)
        if hasattr(self.tabObj, 'btnServiceDelete'):
            # old: QtCore.QObject.connect(self.tabObj.btnServiceDelete, QtCore.SIGNAL("clicked()"), self.deleteServiceConnection)
            self.tabObj.btnServiceDelete.clicked.connect(self.deleteServiceConnection)
        if hasattr(self.tabObj, 'btnServiceLoadFile'):
            # old: QtCore.QObject.connect(self.tabObj.btnServiceLoadFile, QtCore.SIGNAL("clicked()"), self.importServiceConnections)
            self.tabObj.btnServiceLoadFile.clicked.connect(self.importServiceConnections)
        if hasattr(self.tabObj, 'btnServiceSaveFile'):
            # old: QtCore.QObject.connect(self.tabObj.btnServiceSaveFile, QtCore.SIGNAL("clicked()"), self.exportServiceConnections)
            self.tabObj.btnServiceSaveFile.clicked.connect(self.exportServiceConnections)
        if hasattr(self.tabObj, 'chkLocale'):
            # old: QtCore.QObject.connect(self.tabObj.chkLocale, QtCore.SIGNAL("stateChanged(int)"), self.changeBehaviour)
            self.tabObj.chkLocale.stateChanged[int].connect(self.changeBehaviour)
        if hasattr(self.tabObj, 'cboConnections'):
            # old: QtCore.QObject.connect(self.tabObj.cboConnections, QtCore.SIGNAL("activated(int)"), self.selectedConnections)
            self.tabObj.cboConnections.activated[int].connect(self.selectedConnections) 
        if hasattr(self.tabObj, 'btnNew'):
            # old: QtCore.QObject.connect(self.tabObj.btnNew, QtCore.SIGNAL("clicked()"), self.newConnection)
            self.tabObj.btnNew.clicked.connect(self.newConnection)
        if hasattr(self.tabObj, 'btnEdit'):
            # old: QtCore.QObject.connect(self.tabObj.btnEdit, QtCore.SIGNAL("clicked()"), self.editConnection)
            self.tabObj.btnEdit.clicked.connect(self.editConnection)
        if hasattr(self.tabObj, 'btnDelete'):
            # old: QtCore.QObject.connect(self.tabObj.btnDelete, QtCore.SIGNAL("clicked()"), self.deleteConnection)
            self.tabObj.btnDelete.clicked.connect(self.deleteConnection)
        if hasattr(self.tabObj, 'btnLoadFile'):
            # old: QtCore.QObject.connect(self.tabObj.btnLoadFile, QtCore.SIGNAL("clicked()"), self.importConnections)
            self.tabObj.btnLoadFile.clicked.connect(self.importConnections)
        if hasattr(self.tabObj, 'btnSaveFile'):
            # old: QtCore.QObject.connect(self.tabObj.btnSaveFile, QtCore.SIGNAL("clicked()"), self.exportConnections)
            self.tabObj.btnSaveFile.clicked.connect(self.exportConnections)

        # altri tab
        if hasattr(self.tabObj, 'treeWidget'):
            # OLD STYLE
            # QtCore.QObject.connect(self.tabObj.treeWidget, QtCore.SIGNAL("itemClicked(QTreeWidgetItem*,int)"), self.__tree_itemClicked)
            #if self.tabObj.treeWidget != None:
            # http://stackoverflow.com/questions/13662020/how-to-implement-itemchecked-and-itemunchecked-signals-for-qtreewidget-in-pyqt4
            #self.tabObj.treeWidget.itemClicked[QTreeWidgetItem, int].connect(self.__tree_itemClicked)
            self.tabObj.treeWidget.itemClicked.connect(self.__tree_itemClicked)

        if hasattr(self.tabObj, 'cboCategory'):
            # old: QtCore.QObject.connect(self.tabObj.cboCategory, QtCore.SIGNAL("currentIndexChanged(int)"), self.categoryChanged)
            self.tabObj.cboCategory.currentIndexChanged[int].connect(self.categoryChanged)
        if hasattr(self.tabObj, 'cboUnita'):
            # old: QtCore.QObject.connect(self.tabObj.cboUnita, QtCore.SIGNAL("currentIndexChanged(int)"), self.unitaChanged)
            self.tabObj.cboUnita.currentIndexChanged[int].connect(self.unitaChanged)
        if hasattr(self.tabObj, 'cboPeriodicita'):
            # old: QtCore.QObject.connect(self.tabObj.cboPeriodicita, QtCore.SIGNAL("currentIndexChanged(int)"), self.periodicitaChanged)
            self.tabObj.cboPeriodicita.currentIndexChanged[int].connect(self.periodicitaChanged)
        if hasattr(self.tabObj, 'btCerca'):
            # old: QtCore.QObject.connect(self.tabObj.btCerca, QtCore.SIGNAL("released ()"), self.__filterChanged)
            self.tabObj.btCerca.released.connect(self.__filterChanged)
        if hasattr(self.tabObj, 'btApriAlbero'):
            # old: QtCore.QObject.connect(self.tabObj.btApriAlbero, QtCore.SIGNAL("clicked()"), self.__onApriAlbero)
            self.tabObj.btApriAlbero.clicked.connect(self.__onApriAlbero)
        if hasattr(self.tabObj, 'btDeseleziona'):
            # old: QtCore.QObject.connect(self.tabObj.btDeseleziona, QtCore.SIGNAL("clicked()"), self.__onDeselezionaAlbero)
            self.tabObj.btDeseleziona.clicked.connect(self.__onDeselezionaAlbero)
        if hasattr(self.tabObj, 'btChiudiAlbero'):
            # old: QtCore.QObject.connect(self.tabObj.btChiudiAlbero, QtCore.SIGNAL("clicked()"), self.__onChiudiAlbero)
            self.tabObj.btChiudiAlbero.clicked.connect(self.__onChiudiAlbero)
        if hasattr(self.tabObj, 'btMetadati'):
            # old: QtCore.QObject.connect(self.tabObj.btMetadati, QtCore.SIGNAL("clicked()"), self.__onMetadati)
            self.tabObj.btMetadati.clicked.connect(self.__onMetadati)
        if hasattr(self.tabObj, 'ckSerieStorica'):
            # old: QtCore.QObject.connect(self.tabObj.ckSerieStorica, QtCore.SIGNAL("stateChanged(int)"), self.changeStateSerieStorica)
            self.tabObj.ckSerieStorica.stateChanged[int].connect(self.changeStateSerieStorica)
        # carica le connessioni services
        if hasattr(self.tabObj, 'cboServiceConnections'):
            self.populateServiceConnectionList()
            self.selectedServiceConnections()

        # carica il portafoglio connessioni db in un tableWidget
        if hasattr(self.tabObj, 'tableWidgetConnections'):
            # TODO:
            # self.populateConnectionsPortfolio()
            pass

        # carica le connessioni db
        if hasattr(self.tabObj, 'cboConnections'):
            self.populateConnectionList()
            self.selectedConnections()

    def disconnect(self):
        # altri tab
        if hasattr(self.tabObj, 'treeWidget'):
            # old: QtCore.QObject.disconnect(self.tabObj.treeWidget, QtCore.SIGNAL("itemClicked(QTreeWidgetItem*,int)"), self.__tree_itemClicked)
            #self.tabObj.treeWidget.itemClicked[QTreeWidgetItem, int].disconnect(self.__tree_itemClicked)
            self.tabObj.treeWidget.itemClicked.disconnect(self.__tree_itemClicked)

        if hasattr(self.tabObj, 'cboCategory'):
            # old: QtCore.QObject.disconnect(self.tabObj.cboCategory, QtCore.SIGNAL("currentIndexChanged(int)"), self.categoryChanged)
            self.tabObj.cboCategory.currentIndexChanged[int].disconnect(self.categoryChanged)  
        if hasattr(self.tabObj, 'cboUnita'):
            # old: QtCore.QObject.disconnect(self.tabObj.cboUnita, QtCore.SIGNAL("currentIndexChanged(int)"), self.unitaChanged)
            self.tabObj.cboUnita.currentIndexChanged[int].disconnect(self.unitaChanged)
        if hasattr(self.tabObj, 'cboPeriodicita'):
            # old: QtCore.QObject.disconnect(self.tabObj.cboPeriodicita, QtCore.SIGNAL("currentIndexChanged(int)"), self.periodicitaChanged)
            self.tabObj.cboPeriodicita.currentIndexChanged[int].disconnect(self.periodicitaChanged)
        if hasattr(self.tabObj, 'btCerca'):
            # old: QtCore.QObject.disconnect(self.tabObj.btCerca, QtCore.SIGNAL("released ()"), self.__filterChanged)
            self.tabObj.btCerca.released.disconnect(self.__filterChanged)
        if hasattr(self.tabObj, 'btApriAlbero'):
            # old: QtCore.QObject.disconnect(self.tabObj.btApriAlbero, QtCore.SIGNAL("clicked()"), self.__onApriAlbero)
            self.tabObj.btApriAlbero.clicked.disconnect(self.__onApriAlbero)
        if hasattr(self.tabObj, 'btDeseleziona'):
            # old: QtCore.QObject.disconnect(self.tabObj.btDeseleziona, QtCore.SIGNAL("clicked()"), self.__onDeselezionaAlbero)
            self.tabObj.btDeseleziona.clicked.disconnect(self.__onDeselezionaAlbero)
        if hasattr(self.tabObj, 'btChiudiAlbero'):
            # old: QtCore.QObject.disconnect(self.tabObj.btChiudiAlbero, QtCore.SIGNAL("clicked()"), self.__onChiudiAlbero)
            self.tabObj.btChiudiAlbero.clicked.disconnect(self.__onChiudiAlbero)
        if hasattr(self.tabObj, 'btMetadati'):
            # old: QtCore.QObject.disconnect(self.tabObj.btMetadati, QtCore.SIGNAL("clicked()"), self.__onMetadati)
            self.tabObj.btMetadati.clicked.disconnect(self.__onMetadati)
        if hasattr(self.tabObj, 'ckSerieStorica'):
            # old: QtCore.QObject.disconnect(self.tabObj.ckSerieStorica, QtCore.SIGNAL("stateChanged(int)"), self.changeStateSerieStorica)
            self.tabObj.ckSerieStorica.stateChanged[int].disconnect(self.changeStateSerieStorica)

        # tab di configurazione
        if hasattr(self.tabObj, 'btnAbout'):
            # old: QtCore.QObject.disconnect(self.tabObj.btnAbout, QtCore.SIGNAL("clicked()"), self.showAbout)
            self.tabObj.btnAbout.clicked.disconnect(self.showAbout)
        if hasattr(self.tabObj, 'cboServiceConnections'):
            # old: QtCore.QObject.disconnect(self.tabObj.cboServiceConnections, QtCore.SIGNAL("activated( int )"), self.selectedServiceConnections)
            self.tabObj.cboServiceConnections.activated[int].disconnect(self.selectedServiceConnections)
        if hasattr(self.tabObj, 'cboServiceConnections'):
            # old: QtCore.QObject.disconnect(self.tabObj.cboServiceConnections, QtCore.SIGNAL("currentIndexChanged(int)"), self.changedServiceConnections)
            self.tabObj.cboServiceConnections.currentIndexChanged[int].disconnect(self.changedServiceConnections)
        if hasattr(self.tabObj, 'btnServiceNew'):
            # old: QtCore.QObject.disconnect(self.tabObj.btnServiceNew, QtCore.SIGNAL("clicked()"), self.newServiceConnection)
            self.tabObj.btnServiceNew.clicked.disconnect(self.newServiceConnection)
        if hasattr(self.tabObj, 'btnServiceEdit'):
            # old: QtCore.QObject.disconnect(self.tabObj.btnServiceEdit, QtCore.SIGNAL("clicked()"), self.editServiceConnection)
            self.tabObj.btnServiceEdit.clicked.disconnect(self.editServiceConnection)
        if hasattr(self.tabObj, 'btnServiceDelete'):
            # old: QtCore.QObject.disconnect(self.tabObj.btnServiceDelete, QtCore.SIGNAL("clicked()"), self.deleteServiceConnection)
            self.tabObj.btnServiceDelete.clicked.disconnect(self.deleteServiceConnection)
        if hasattr(self.tabObj, 'btnServiceLoadFile'):
            # old: QtCore.QObject.disconnect(self.tabObj.btnServiceLoadFile, QtCore.SIGNAL("clicked()"), self.importServiceConnections)
            self.tabObj.btnServiceLoadFile.clicked.disconnect(self.importServiceConnections)
        if hasattr(self.tabObj, 'btnServiceSaveFile'):
            # old: QtCore.QObject.disconnect(self.tabObj.btnServiceSaveFile, QtCore.SIGNAL("clicked()"), self.exportServiceConnections)
            self.tabObj.btnServiceSaveFile.clicked.disconnect(self.exportServiceConnections)
        if hasattr(self.tabObj, 'chkLocale'):
            # old: QtCore.QObject.disconnect(self.tabObj.chkLocale, QtCore.SIGNAL("stateChanged(int)"), self.changeBehaviour)
            self.tabObj.chkLocale.stateChanged[int].disconnect(self.changeBehaviour)
  
    def getCountTabFromConfig(self, uiObjectName):
        """
        Restituisce il count dei tab all'interno della configurazione predefinita nel dictionary di GestoreTab
        @param uiObjectName : nome dell'oggetto tab in ui
        @return: count : integer 0..n in caso di errore restituisce -1
        """
        count = 0
        try:
            count = len(self.indexTabDict)
        except:
            count = -1
        finally:
            return count

    def getIndexTabFromConfig(self, uiObjectName):
        """
        Restituisce l'index del tab all'interno della configurazione predefinita nel dictionary di GestoreTab
        @param uiObjectName : nome dell'oggetto tab in ui
        @return: index : integer 0..n per la posizione nel widget, restituisce -1 in caso di nullo o errore
        """
        index = -1
        try:
            index = self.indexTabDict[uiObjectName]
        except:
            index = -1
        finally:
            return index

    def getNameTabFromConfig(self, uiObjectName):
        """
        Restituisce il nome del tab all'interno della configurazione predefinita nel dictionary di GestoreTab
        @param uiObjectName : nome dell'oggetto tab in ui
        @return: name: la stringa da visualizzare in ui
        """
        name = uiObjectName
        try:
            name = self.nameTabDict[uiObjectName]
        except:
            name = uiObjectName + "(!)"
        finally:
            return name

    def __setItemAndChildrenCheck(self, widget, eCheckState):
        widget.setCheckState(0, eCheckState)
        for i in range(widget.childCount()):
            self.__setItemAndChildrenCheck(widget.child(i), eCheckState)

    def __treeFilterIndica(self, item, txt, txt1, txt2):
        """
        Applica il filtro sull'item di un tree "asciugandolo" in modo ricorsivo
        Estende il __treeFilter per il caso d'uso del tab indicatori
        Refactoring introdotto in 1.0.13
        @return: int: esito filtro su item: 0 = nascosto , 1..n = non nascosto
        """
        try:
            nome_text = str(item.text(0)).lower()
            unita_text = str(item.text(1)).lower()
            periodicita_text = str(item.text(2)).lower()
        except:
            return 0

        #LOGGER.debug('__treeFilterIndica: widget | %s | %s | %s |' % (nome_text, unita_text, periodicita_text))

        childCount = item.childCount()
        if childCount == 0:
#             if txt == '' or txt in nome_text or txt1 == '' or txt1 in unita_text or txt2 == '' or txt2 in periodicita_text:
#                 """ non nasconde item """
#                 item.setHidden(False)
#                 return 1
            if txt == '' or txt in nome_text:
                if (txt1 == '' or txt1 in unita_text) and (txt2 == '' or txt2 in periodicita_text):
                    """ non nasconde item """
                    item.setHidden(False)
                    return 1
                else:
                    """ nasconde item """
                    item.setHidden(True)
                    return 0
            else:
                """ nasconde item """
                item.setHidden(True)
                return 0
        else:
            n = 0
            if txt in nome_text:
                txt = ''
            if txt1 in unita_text:
                txt1 = ''
            if txt2 in periodicita_text:
                txt2 = ''

            for i in range(item.childCount()):
                n += self.__treeFilterIndica(item.child(i), txt, txt1, txt2)

            if n > 0:
                """ non nasconde item """
                item.setHidden(False)
                return n
            else:
                """ nasconde item """
                item.setHidden(True)
                return 0

    def __treeFilter(self, item, txt):
        """
        Applica il filtro sull'item di un tree "asciugandolo" in modo ricorsivo
        Refactoring introdotto in 1.0.13
        @return: int: esito filtro su item: 0 = nascosto , 1..n = non nascosto
        """
        try:
            nome_text = str(item.text(0)).lower()
        except:
            return 0

        childCount = item.childCount()
        if childCount == 0:
            if txt == '' or txt in nome_text:
                """ non nasconde item """
                item.setHidden(False)
                return 1
            else:
                """ nasconde item """
                item.setHidden(True)
                return 0
        else:
            n = 0
            if txt in nome_text:
                txt = ''

            for i in range(item.childCount()):
                n += self.__treeFilter(item.child(i), txt)

            if n > 0:
                """ non nasconde item """
                item.setHidden(False)
                return n
            else:
                """ nasconde item """
                item.setHidden(True)
                return 0

    def __filterChanged(self):
        self.categoryChanged(0)

    def __onApriAlbero(self):
        self.tabObj.treeWidget.expandAll()

    def __onChiudiAlbero(self):
        self.tabObj.treeWidget.collapseAll()

    def __onDeselezionaAlbero(self):
        self.deselectAll()

    def __onMetadati(self):
        if self.nextClick > time.time():
            return
        self.nextClick = time.time() + 1

        selitms = self.tabObj.treeWidget.selectedItems()
        for item in selitms:
            data = item.data(0, QtCore.Qt.UserRole)
            try:
                md = self.tabObj.getLayerMetadataURL(data)
                if md != None and md != '':
                    QDesktopServices.openUrl(QUrl.fromUserInput(md))
                else:
                    """ e.c@20151028: patch per polimorfismo dei tab 'vector' || 'geoservizi' """
                    nowname = ''
                    if hasattr(data, 'nome'):
                        nowname = getattr(data, 'nome')
                    elif hasattr(data, 'name'):
                        nowname = getattr(data, 'name')

                    nowtitle = ''
                    if hasattr(data, 'title'):
                        nowtitle = getattr(data, 'title')

                    msg = ''.join(['Metadati non disponibili!', '\n', '\n', nowname, '\n', nowtitle])
                    QMessageBox.information(None, "Metadati", msg, QMessageBox.Ok)
            except Exception as ex:
                msg = str(ex)
                QMessageBox.information(None, "Metadati", msg)
            return

    def categoryChangedOLD(self, n):
        mfilter = str(self.tabObj.txFiltro.text()).lower()
        tx = self.tabObj.cboCategory.currentText()
        tw = self.tabObj.treeWidget
        for i in range(tw.topLevelItemCount()):
            item = tw.topLevelItem(i)
            data = item.data(0, QtCore.Qt.UserRole)
            b = self.tabObj.getLayerCategory(data) == tx
            if b == True:
                if mfilter != '' and  mfilter in self.tabObj.getLayerDescription(data).lower():
                    item.setHidden(False)
                    self.__treeFilter(item, '')
                else:
                    if self.__treeFilter(item, mfilter) == 0:
                        item.setHidden(True)
                    else:
                        item.setHidden(False)
            else:
                item.setHidden(True)
        tw.collapseAll()

    def categoryChanged(self, n):
        additionalFiltersIndica = self.tabObj.name == 'tabIndica'

        if (additionalFiltersIndica):
            filterUnita = str(self.tabObj.cboUnita.currentText()).lower()
            filterPeriodicita = str(self.tabObj.cboPeriodicita.currentText()).lower()

        mfilter = str(self.tabObj.txFiltro.text()).lower()
        textCategory = self.tabObj.cboCategory.currentText()
        treeWidget = self.tabObj.treeWidget
        for i in range(treeWidget.topLevelItemCount()):
            item = treeWidget.topLevelItem(i)
            data = item.data(0, QtCore.Qt.UserRole)
            b = self.tabObj.getLayerCategory(data) == textCategory
            if b == True:
                if (additionalFiltersIndica):
                    # specializzazione per tab indicatori con filtri aggiuntivi
                    if mfilter != '' and  mfilter in self.tabObj.getLayerDescription(data).lower():
                        item.setHidden(False)
                        self.__treeFilterIndica(item, '', filterUnita, filterPeriodicita)
                    else:
                        #LOGGER.debug('categoryChanged: -------------------------------------------------------------------')
                        #LOGGER.debug('categoryChanged: filtri | %s | %s | %s |' % (mfilter, filterUnita, filterPeriodicita))
                        if self.__treeFilterIndica(item, mfilter, filterUnita, filterPeriodicita) == 0:
                            item.setHidden(True)
                        else:
                            item.setHidden(False)
                else:
                    # specializzazione per tab con un solo filtro (comportamento precedente a introduzione indicatori)
                    if mfilter != '' and  mfilter in self.tabObj.getLayerDescription(data).lower():
                        item.setHidden(False)
                        self.__treeFilter(item, '')
                    else:
                        if self.__treeFilter(item, mfilter) == 0:
                            item.setHidden(True)
                        else:
                            item.setHidden(False)
            else:
                item.setHidden(True)
        if (additionalFiltersIndica):
            treeWidget.collapseAll()
            #treeWidget.expandAll()
        else:
            treeWidget.collapseAll()

    def unitaChanged(self, n):
        treeWidget = self.tabObj.treeWidget
#         currentText = self.tabObj.cboUnita.currentText()
#         self.tabObj.txFiltro.setText(currentText)
        self.categoryChanged(0)
        treeWidget.collapseAll()

    def periodicitaChanged(self, n):
        treeWidget = self.tabObj.treeWidget
#         currentText = self.tabObj.cboPeriodicita.currentText()
#         self.tabObj.txFiltro.setText(currentText)
        self.categoryChanged(0)
        treeWidget.collapseAll()

#     def getSelectedForGraficiSerieStorica(self):
#         """
#         considera i nodi selezionati nel TreeWidget del tab Indicatori
#         e ricava i valori necessari per il tool dei Grafici Serie Storica,
#         richiamato solo nel tab indica quindi non ci sono controlli sul tab
# 
#         @return: dictionary dictForGraficiSerieStorica
#         """
#         dictForGraficiSerieStorica = dict()
#         pgisList = self.treeWidgetGetSelectedList()
# 
#         if len(pgisList) > 1 and len(pgisList) <= 8:
#             #abilitati = self.dlg.indica_getAbilitati()
# 
#             dimensione = u''
#             idealpoint = u''
#             indicatore = u''
#             periodi = list()  # ['2010','2011'] oppure ['1_2010','2_2010'] oppure ['51_2013','52_2013']
#             periodicita = u''
#             unitamisura = u''
# 
#             tcon = [t for t in pgisList if t.host != '']
#             i = 0
#             for info in tcon:
#                 i = i + 1
#                 if (i == 1):
#                     dimensione = info.desc_dimensione
#                     idealpoint = info.ideal_point
#                     indicatore = info.nome_indicatore
#                     periodicita = info.periodicita
#                     unitamisura = info.des_unita_misura
# 
#                 s = info.nome
#                 if (periodicita == "Annuale"):
#                     s = s.replace('Anno ', '')
#                 elif (periodicita == "Semestrale"):
#                     s = s.replace(' Semestre ', '_')
#                 elif (periodicita == "Quadrimestrale"):
#                     s = s.replace(' Quadrimestre ', '_')
#                 elif (periodicita == "Trimestrale"):
#                     s = s.replace(' Trimestre ', '_')
#                 elif (periodicita == "Mensile"):
#                     s = s.replace(' Mese ', '_')
#                 elif (periodicita == "Settimanale"):
#                     s = s.replace(' Settimana ', '_')
#                 else:
#                     LOGGER.debug('getSelectedForGraficiSerieStorica: periodicita non prevista: %s' % (periodicita))
#                 periodi.append(s)
# 
#             dictForGraficiSerieStorica['dimensione'] = dimensione
#             dictForGraficiSerieStorica['idealpoint'] = idealpoint
#             dictForGraficiSerieStorica['indicatore'] = indicatore
#             dictForGraficiSerieStorica['periodi'] = periodi
#             dictForGraficiSerieStorica['periodicita'] = periodicita
#             dictForGraficiSerieStorica['unitamisura'] = unitamisura
# 
#         return dictForGraficiSerieStorica

#     def graficiSerieStorica(self):
#         """
#         slot associato al button Grafici Serie Storica nel tab Indica:
#         raccoglie le informazioni sui nodi selezionati nel widget tree e 
#         sulle altre informazioni presenti nelle custom properties del layer attivo.
#         Se le informazioni sono consistenti, le passa e istanzia il tool toolChartSerieStorica
#         """
#         LOGGER.debug('graficiSerieStorica setMapTool(self.csiAtlante.toolChartSerieStorica')
# 
#         dictForGraficiSerieStorica = self.getSelectedForGraficiSerieStorica()
#         dimensione = dictForGraficiSerieStorica.get('dimensione', '')
#         idealpoint = dictForGraficiSerieStorica.get('idealpoint', '')
#         indicatore = dictForGraficiSerieStorica.get('indicatore', '')
#         periodi = dictForGraficiSerieStorica.get('periodi', [])
#         periodicita = dictForGraficiSerieStorica.get('periodicita', '')
#         unitamisura = dictForGraficiSerieStorica.get('unitamisura', '')
# 
#         LOGGER.debug('graficiSerieStorica dimensione: %s' % (dimensione))
#         LOGGER.debug('graficiSerieStorica idealpoint: %s' % (idealpoint))
#         LOGGER.debug('graficiSerieStorica indicatore: %s' % (indicatore))
#         LOGGER.debug('graficiSerieStorica periodicita: %s' % (periodicita))
#         LOGGER.debug('graficiSerieStorica periodi: %s' % (periodi))
#         LOGGER.debug('graficiSerieStorica unitamisura: %s' % (unitamisura))
# 
#         # patch per http://jiraprod.csi.it:8083/browse/CSIATLANTE-6
#         self.csiAtlante.toolChartSerieStorica = ChartMapToolIdentify(self.csiAtlante.iface, self.csiAtlante)
#         if len(periodi) > 0:
#             self.csiAtlante.toolChartSerieStorica.setDimensione(dimensione)
#             self.csiAtlante.toolChartSerieStorica.setIdealPoint(idealpoint)
#             self.csiAtlante.toolChartSerieStorica.setIndicatore(indicatore)
#             self.csiAtlante.toolChartSerieStorica.setPeriodicita(periodicita)
#             self.csiAtlante.toolChartSerieStorica.setPeriodi(periodi)
#             self.csiAtlante.toolChartSerieStorica.setUnitaMisura(unitamisura)
#             #
#             self.csiAtlante.canvas.setMapTool(self.csiAtlante.toolChartSerieStorica)
#         else:
#             # ------------------------------------------------
#             # http://jiraprod.csi.it:8083/browse/CSIATLANTE-6
#             # Il puntatore dei grafi, una volta attivato non c'è modo di disattivarlo
#             # ------------------------------------------------
#             self.csiAtlante.canvas.unsetMapTool(self.csiAtlante.toolChartSerieStorica)
#         pass
#         periodi = self.csiAtlante.toolChartSerieStorica.getPeriodi()
#         periodistringa = ''.join(periodi)
#         LOGGER.debug('graficiSerieStorica getPeriodi(): %s' % (periodistringa))

    def __tree_itemClicked(self, widget, item):
        if self.nextClick < time.time():
            try:
                eCheckState = widget.checkState(0)
                if self.tabObj.treeOnlyOneItemSelected:
                    root = self.tabObj.treeWidget.invisibleRootItem()
                    for i in range(root.childCount()):
                        self.__setItemAndChildrenCheck(root.child(i), 0)
                    widget.setCheckState(0, eCheckState)
                else:
                    if self.tabObj.bUpdateClickChildTreeItems:
                        for i in range(widget.childCount()):
                            self.__setItemAndChildrenCheck(widget.child(i), eCheckState)

                    parent = widget.parent()
                    while parent != None:
                        parent.setCheckState(0, 0)
                        parent = parent.parent()

                    self.__UpdateCRSandSRS()
            finally:
                self.nextClick = time.time() + 0.1

    def __UpdateCRSandSRS(self):
        # if self.tabObj.crsCombo != None and self.tabObj.formatoCombo != None:
        if hasattr(self.tabObj, 'crsCombo') and hasattr(self.tabObj, 'formatoCombo'):
            try:
                self.tabObj.crsCombo.clear()
                self.tabObj.formatoCombo.clear()
                wlist = self.treeWidgetGetSelectedList()
                if len(wlist) > 0:
                    msrs = []
                    formats = []
                    for wl in wlist:
                        try:
                            if len(wl.srs) > 0:
                                if len(msrs) == 0:
                                    msrs = wl.srs[:]
                                else:
                                    for srs in msrs:
                                        if not srs in wl.srs:
                                            msrs.remove(srs)
                        except:
                            pass
                        try:
                            tr = wl.parentTree
                            afmt = tr.aformat
                            if len(formats) == 0:
                                formats = afmt[:]
                            else:
                                for fm in afmt:
                                    if fm not in formats:
                                        formats.remove(fm)
                        except:
                            pass
                    self.tabObj.crsCombo.addItems(msrs)
                    self.tabObj.formatoCombo.addItems(formats)
                    try:
                        self.tabObj.formatoCombo.setCurrentIndex(self.tabObj.formatoCombo.findText('image/png'))
                    except:
                        pass

                    # e.c@20140722
                    # QgsMapCanvas.mapRenderer() is deprecated
                    #actual_crs = iface.mapCanvas().mapRenderer().destinationCrs()
                    actual_crs = iface.mapCanvas().mapSettings().destinationCrs()
                    descr = 'EPSG:' + str(actual_crs.epsg())
                    if descr in msrs:
                        self.tabObj.crsCombo.setCurrentIndex(self.tabObj.crsCombo.findText(descr))
            except:
                pass

    def __newTreeWidgetItem(self, qtreeWidget, topTree, hide):
        """
        Crea e aggiunge un top level qitem al treewidget

        @param qtreeWidget: QTreeWidget
        @param topTree: tree di primo livello
        @return: qItem: QTreeWidgetItem
        """
        if self.tabObj.objectName() == 'tabIndica':
            qItem = QTreeWidgetItem([self.tabObj.getLayerDescription(topTree), self.tabObj.getLayerUnita(topTree), self.tabObj.getLayerPeriodicita(topTree)])
            qItem.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            qItem.setCheckState(0, QtCore.Qt.Unchecked)      # column 0
            qItem.setData(0, QtCore.Qt.UserRole, topTree)    # column 0
            qItem.setCheckState(1, QtCore.Qt.Unchecked)      # column 1
            qItem.setData(1, QtCore.Qt.UserRole, topTree)    # column 1
            qItem.setCheckState(2, QtCore.Qt.Unchecked)      # column 2
            qItem.setData(2, QtCore.Qt.UserRole, topTree)    # column 2
        else:
            qItem = QTreeWidgetItem([self.tabObj.getLayerDescription(topTree)])
            qItem.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            qItem.setCheckState(0, QtCore.Qt.Unchecked)      # column 0
            qItem.setData(0, QtCore.Qt.UserRole, topTree)    # column 0

        qItem.setHidden(hide)

        qtreeWidget.addTopLevelItem(qItem)
        return qItem

    def __addLayer(self, qparentItem, layer):
        """
        Converte un layer tree in un QTreeWidgetItem e lo assegna come figlio del parentItem

        @param qparentItem: QTreeWidgetItem
        @param layer: layer tree
        """
        if self.tabObj.objectName() == 'tabIndica':
            qchildItem = QTreeWidgetItem([self.tabObj.getLayerDescription(layer), self.tabObj.getLayerUnita(layer), self.tabObj.getLayerPeriodicita(layer)])
            #tmp = self.tabObj.getLayerDescription(layer) + ' ' + self.tabObj.getLayerUnita(layer) + ' ' + self.tabObj.getLayerPeriodicita(layer)
            #LOGGER.debug('%s.%s - qchildItem: %s columncount: %d' % (self.tabObj.__class__.__name__, '__addLayer', tmp, qchildItem.columnCount()))
            qchildItem.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            qchildItem.setCheckState(0, QtCore.Qt.Unchecked)    # column 0
            qchildItem.setData(0, QtCore.Qt.UserRole, layer)    # column 0
            qchildItem.setCheckState(1, QtCore.Qt.Unchecked)    # column 1
            qchildItem.setData(1, QtCore.Qt.UserRole, layer)    # column 1
            qchildItem.setCheckState(2, QtCore.Qt.Unchecked)    # column 2
            qchildItem.setData(2, QtCore.Qt.UserRole, layer)    # column 2
        else:
            qchildItem = QTreeWidgetItem([self.tabObj.getLayerDescription(layer)])
            qchildItem.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            qchildItem.setCheckState(0, QtCore.Qt.Unchecked)    # column 0
            qchildItem.setData(0, QtCore.Qt.UserRole, layer)    # column 0

        qparentItem.addChild(qchildItem)
        children = self.tabObj.getLayerChildren(layer)
        if children != None:
            for tlayer in children:
                self.__addLayer(qchildItem, tlayer)

    def clearTreeWidget(self):
        self.tabObj.treeWidget.clear()
        self.tabObj.txFiltro.setText('')

    def clearCombo(self):
        self.tabObj.cboCategory.clear()

    def loadCombo(self, valori):
        self.tabObj.cboCategory.clear()
        a = []
        for t in valori:
            if not t in a:
                a.append(t)
        # a.sort()
        self.tabObj.cboCategory.addItems(a)
        self.tabObj.cboCategory.setCurrentIndex(0)

    def clearComboUnita(self):
        self.tabObj.cboUnita.clear()

    def loadComboUnita(self, tvalori):
        """
        Carica combo delle unita territoriali con la lista di valori passati,
        i valori sono delle tuple anche ripetute, dunque vengono eseguite operazioni di
        unique e poi di sort sul secondo valore della tupla

        @param tvalori: lista di tuple [(valore, ordinamento), (valore, ordinamento), ...]
        """
        self.tabObj.cboUnita.clear()
        unici = []
        for t in tvalori:
            if not t in unici:
                unici.append(t)

        ordinati = sorted(unici, key=lambda ordine: ordine[1])

        a = []
        for t in ordinati:
            a.append(t[0])

        self.tabObj.cboUnita.addItems(a)
        self.tabObj.cboUnita.setCurrentIndex(0)

    def clearComboPeriodicita(self):
        self.tabObj.cboPeriodicita.clear()

    def loadComboPeriodicita(self, tvalori):
        """
        Carica combo delle periodicita con la lista di valori passati,
        i valori sono delle tuple anche ripetute, dunque vengono eseguite operazioni di
        unique e poi di sort sul secondo valore della tupla

        @param tvalori: lista di tuple [(valore, ordinamento), (valore, ordinamento), ...]
        """
        self.tabObj.cboPeriodicita.clear()
        unici = []
        for t in tvalori:
            if not t in unici:
                unici.append(t)

        ordinati = sorted(unici, key=lambda ordine: ordine[1])

        a = []
        for t in ordinati:
            a.append(t[0])

        self.tabObj.cboPeriodicita.addItems(a)
        self.tabObj.cboPeriodicita.setCurrentIndex(0)

    def getValoriUnita(self, infoTree):
        #val = [i.unita for i in infoTree]
        val = []
        for i in infoTree:
            val.append((i.unita, i.ord_unita))
            childrenList = self.tabObj.getLayerChildren(i)
            if childrenList != None:
                childrenVal = self.getValoriUnita(childrenList)
                val.extend(childrenVal)
        return val

    def getValoriPeriodicita(self, infoTree):
        #val = [i.unita for i in infoTree]
        val = []
        for i in infoTree:
            val.append((i.periodicita, i.ord_periodicita))
            childrenList = self.tabObj.getLayerChildren(i)
            if childrenList != None:
                childrenVal = self.getValoriPeriodicita(childrenList)
                val.extend(childrenVal)
        return val

    def loadTreeWidget(self, topTree):
        """
        Converte un top tree (di primo livello) in un QTreeWidgetItem e lo carica nel QTreeWidget del tab corrente

        @param topTree: tree di primo livello
        """
        tx = self.tabObj.cboCategory.currentText()
        b = self.tabObj.getLayerCategory(topTree) == tx
        bHide = not b

        #LOGGER.debug('%s.%s - getLayerCategory=%s tx=%s' % (self.__class__.__name__, 'loadTreeWidget', str(b), tx))
        #LOGGER.debug('%s.%s - getLayerCategory=%s tx=%s' % (self.tabObj.__class__.__name__, 'loadTreeWidget', str(b), tx))

        qItem = self.__newTreeWidgetItem(self.tabObj.treeWidget, topTree, bHide)
        children = self.tabObj.getLayerChildren(topTree)
        if children != None:
            for layer in children:
                self.__addLayer(qItem, layer)

        self.categoryChanged(0)
        self.__onChiudiAlbero()

    def treeWidgetGetItemsList(self):
        """
        Metodo che ricava dal TreeWidget tutti gli elementi e
        li restituisce in una lista

        @return: mlist
        """
        miter = QTreeWidgetItemIterator(self.tabObj.treeWidget)
        mlist = []
        while miter.value():
            item = miter.value()
            mlist.append(item.data(0, QtCore.Qt.UserRole))
            miter += 1
        return mlist

    def treeWidgetGetSelectedList(self):
        """
        Metodo che ricava dal TreeWidget gli elementi selezionati e
        li restituisce in una lista

        @return: mlist
        """
        miter = QTreeWidgetItemIterator(self.tabObj.treeWidget)
        mlist = []
        while miter.value():
            item = miter.value()
            if item.checkState(0):
                mlist.append(item.data(0, QtCore.Qt.UserRole))
            miter += 1
        return mlist

    def deselectAll(self):
        miter = QTreeWidgetItemIterator(self.tabObj.treeWidget)
        while miter.value():
            miter.value().setCheckState(0, 0)
            miter += 1

    def __getServiceName(self):
        return self.serviceName

    def __getServiceUrl(self):
        return self.serviceUrl

    def __getServiceUsr(self):
        return self.serviceUsr

    def __getServicePwd(self):
        return self.servicePwd

    def __setServiceUrl(self, url):
        self.serviceUrl = url

    def __setServiceUsr(self, usr):
        self.serviceUsr = usr

    def __setServicePwd(self, pwd):
        self.servicePwd = pwd

    def getServiceName(self):
        name = self.__getServiceName()
        return name

    def getServiceUrlUsrPwd(self):
        url = self.__getServiceUrl()
        usr = self.__getServiceUsr()
        pwd = self.__getServicePwd()
        return url, usr, pwd

    def setServiceUrlUsrPwd(self, url, usr, pwd):
        self.__setServiceUrl(url)
        self.__setServiceUsr(usr)
        self.__setServicePwd(pwd)

    def __getServiceWmsCached(self):
        return self.serviceWmsCached

    def __getServiceWmsCacheDate(self):
        return self.serviceWmsCacheDate

    def __getServiceWmsCacheFile(self):
        return self.serviceWmsCacheFile

    def __setServiceWmsCached(self, cached):
        self.serviceWmsCached = cached

    def __setServiceWmsCacheDate(self, cachedate):
        self.serviceWmsCacheDate = cachedate

    def __setServiceWmsCacheFile(self, cachefile):
        self.serviceWmsCacheFile = cachefile

    def getServiceWmsCacheValues(self):
        cached = self.__getServiceWmsCached()
        cachedate = self.__getServiceWmsCacheDate()
        cachefile = self.__getServiceWmsCacheFile()
        return cached, cachedate, cachefile

    def setServiceWmsCacheValues(self, cached, cachedate, cachefile):
        self.__setServiceWmsCached(cached)
        self.__setServiceWmsCacheDate(cachedate)
        self.__setServiceWmsCacheFile(cachefile)
        s = QSettings()
        key = "/CSIAtlante/services"
        connName = s.value(key + '/selected', u'', type=unicode)
        s.setValue(key + '/' + connName + '/' + 'wmsCached', cached)
        s.setValue(key + '/' + connName + '/' + 'wmsCacheDate', cachedate)
        s.setValue(key + '/' + connName + '/' + 'wmsCacheFile', cachefile)

    def setTabVisibility(self):
        """
        Gestisce quali schede visualizzare come attive e quali nascondere
        in base a input che arrivano dal servizio.
        Richiamata nella selectedServiceConnections garantisce che viene eseguita sempre prima di manageGui
        dato che i gestori dei tab sono istanziati prima di richiamare la manageGui
        """
#         msg = "setTabVisibility"
#         QMessageBox.information(None, "Import services da file", msg, QMessageBox.Ok)
        self.csiAtlante.schede_visibili()

    def setDependentServices(self):
        s = QSettings()
        service_name_readproject = s.value("/CSIAtlante/service_readproject", "qgsreadprogetto.php", type=unicode)
        service_name_readqml = s.value("/CSIAtlante/service_readqml", "qgsreadqml.php", type=unicode)

        preurlstring = os.path.split(self.serviceUrl)[0]
        self.serviceReadQmlUrl = ''.join([preurlstring, '/', str(service_name_readqml)])
        self.serviceReadProjectUrl = ''.join([preurlstring, '/', str(service_name_readproject)])

    def setGraphServices(self):
        s = QSettings()
        self.serviceChartUrl = s.value("/CSIAtlante/service_chart", "http://osgis2.csi.it/graph/sga/graph_stream.php", type=unicode)
        self.serviceGraphUrl = s.value("/CSIAtlante/service_graph", "http://osgis2.csi.it/identigraph2/graph.php", type=unicode)

    def setServiceReadQmlUrl(self, url):
        self.serviceReadQmlUrl = url

    def setServiceReadProjectUrl(self, url):
        self.serviceReadProjectUrl = url

    def getServiceReadQmlUrl(self):
        return self.serviceReadQmlUrl

    def getServiceReadProjectUrl(self):
        return self.serviceReadProjectUrl

    def getServiceChartUrl(self):
        return self.serviceChartUrl

    def getServiceGraphUrl(self):
        return self.serviceGraphUrl

    def showAbout(self):
        """
        Crea una nuova connessione nel portafoglio servizi mostrando un dialogo di inserimento
        """
        dlgNew = AboutDialog()
        dlgNew.setWindowTitle('About')
        if dlgNew.exec_() == QDialog.Accepted:
            pass

    def selectedServiceConnections(self):
        """
        Imposta il riferimento globale del plugin al servizio selezionato nella combobox
        Il riferimento e' nel setting: "/CSIAtlante/services/selected"
        In coda setta anche tutti gli altri servizi dipendenti dal servizio selezionato
        """
        s = QSettings()
        connName = self.tabObj.cboServiceConnections.currentText()
        s.setValue("/CSIAtlante/services/selected", connName)
        key = "/CSIAtlante/services/" + connName
        self.serviceName = connName
        self.serviceUrl = s.value(key + '/url', u'', type=unicode)
        self.serviceUsr = s.value(key + '/usr', u'', type=unicode)
        self.servicePwd = s.value(key + '/pwd', u'', type=unicode)
        self.serviceWmsCached = s.value(key + '/wmsCached', False, type=bool)
        self.serviceWmsCacheDate = s.value(key + '/wmsCacheDate', u'', type=unicode)
        
        # patch ***PUR*** e.c
        self.serviceWmsCacheFile = s.value(key + '/wmsCacheFile', u'', type=unicode)
        last = self.serviceWmsCacheFile.split("/")[-1]
        self.serviceWmsCacheFile = last
#         msg = "selezionato: %s " % (connName)
#         iface.messageBar().pushMessage("Attenzione", msg, level=QgsMessageBar.CRITICAL)
        self.setDependentServices()
        self.setGraphServices()
        self.setTabVisibility()

    def changedServiceConnections(self, index):
        """
        Slot che riceve il cambio del servizio di connessione nella combo
        e riporta l'informazione per tutti i tab nei flag generali di plugin: servicechanged_tab*
        I flag vengono discriminati e rivalorizzati in CsiAtlanteDialog.activateTab
        @param index: the index, type as int.
        """
        self.csiAtlante.servicechanged_tabProgetti = True
        self.csiAtlante.servicechanged_tabPostgis = True
        self.csiAtlante.servicechanged_tabRaster = True
        self.csiAtlante.servicechanged_tabWMS = True
        self.csiAtlante.servicechanged_tabIndica = True

    def newServiceConnection(self):
        """
        Crea una nuova connessione nel portafoglio servizi mostrando un dialogo di inserimento
        """
        dlgNew = NewServiceConnectionDialog()
        dlgNew.setWindowTitle('Nuova connessione')
        if dlgNew.exec_() == QDialog.Accepted:
            self.populateServiceConnectionList()

    def editServiceConnection(self):
        """
        Modifica i dati della connessione al servizio selezionata nella combobox
        """
        s = QSettings()
        connName = self.tabObj.cboServiceConnections.currentText()
        url = s.value('/CSIAtlante/services/' + connName + '/url', u'', type=unicode)
        usr = s.value('/CSIAtlante/services/' + connName + '/usr', u'', type=unicode)
        pwd = s.value('/CSIAtlante/services/' + connName + '/pwd', u'', type=unicode)
        dlgEdit = NewServiceConnectionDialog()
        dlgEdit.setWindowTitle('Modifica della connessione')
        dlgEdit.leName.setText(connName)
        dlgEdit.leURL.setText(url)
        dlgEdit.leUser.setText(usr)
        dlgEdit.lePassword.setText(pwd)
        if dlgEdit.exec_() == QDialog.Accepted:
            self.populateServiceConnectionList()

    def deleteServiceConnection(self):
        """
        Elimina dal portafoglio il servizio selezionato nella combobox
        """
        s = QSettings()
        key = '/CSIAtlante/services/' + self.tabObj.cboServiceConnections.currentText()
        msg = 'Rimuovere la connessione \n {0} \n e tutte le sue impostazioni?'.format(self.tabObj.cboServiceConnections.currentText())
        result = QMessageBox.information(None, "Conferma elimina", msg, QMessageBox.Ok | QMessageBox.Cancel)
        if result == QMessageBox.Ok:
            s.remove(key)
            self.tabObj.cboServiceConnections.removeItem(self.tabObj.cboServiceConnections.currentIndex())
            self.setServiceConnectionListPosition()

    def importServiceConnections(self):
        """
        Importa da un file XML le connessioni ai servizi da mettere nel portafoglio del plugin
        """
        self.fileName = QFileDialog.getOpenFileName(None, 'Importa da file le connessioni ai servizi service', '.', '(*.xml *.XML)')
        if self.fileName is None:
            return

        error = None
        xmlFile = None
        try:
            xmlFile = QFile(self.fileName)
            if not xmlFile.open(QIODevice.ReadOnly):
                raise (IOError, unicode(xmlFile.errorString()))
        except (IOError, OSError, ValueError) as e:
            error = "Failed to open or import xml: %s" % e
        finally:
            if xmlFile is not None:
                # xmlFile.close()
                pass
            if error is not None:
                return False, error

        try:
            xml = QXmlStreamReader(xmlFile)
        except (IOError, OSError, ValueError) as e:
            error = "Failed to read xml: %s" % e
        finally:
            if error is not None:
                return False, error
            s = QSettings()
            while(not xml.atEnd() and not xml.hasError()):
                xml.readNext()
                token = xml.tokenType()
                if (token == QXmlStreamReader.StartDocument):
                    xml.readNext()
                    pass
                if xml.isStartElement():
                    if (xml.name() == 'service'):
                        cname = ''
                        curl = ''
                        cusr = ''
                        cpwd = ''
                        attr = xml.attributes()
                        if (attr.hasAttribute('name')):
                            cname = attr.value('name')
                        if (attr.hasAttribute('url')):
                            curl = attr.value('url')
                        if (attr.hasAttribute('usr')):
                            cusr = attr.value('usr')
                        if (attr.hasAttribute('pwd') and attr.hasAttribute('name')):
                            cpwd = self.csiAtlante.servicesportfolio.decompress(attr.value('pwd'), attr.value('name'))

                        if cname is not None and cname != "":
                            key = "/CSIAtlante/services/" + cname
                            # se cname gia' esiste: sovrascrive senza chiedere!
                            s.setValue(key + "/url", curl)
                            s.setValue(key + "/usr", cusr)
                            s.setValue(key + "/pwd", cpwd)

            xml.clear()

            # aggiornare la lista servizi
            self.populateServiceConnectionList()

            msg = "Importato!"
            QMessageBox.information(None, "Import services da file", msg, QMessageBox.Ok)

            if (xml.hasError()):
                QMessageBox.information(None, "Import services da file", 'xml.hasError()', QMessageBox.Ok)
                pass

    def exportServiceConnections(self):
        """
        Esporta su un file XML le connessioni ai servizi dal portafoglio
        """
        self.fileName = QFileDialog.getSaveFileName(None, "Salva su file le connessioni ai servizi service", ".", "(*.xml *.XML)")
        if self.fileName is None:
            return

        if not str(self.fileName.lower()).endswith(".xml"):  # .toLower().endsWith(".xml"): Porting QGIS 2.0
            self.fileName += ".xml"

        # export di tutti i services
        xmlWriter = QXmlStreamWriter()
        xmlWriter.setAutoFormatting(True)
        xmlFile = QFile(self.fileName)

        if (xmlFile.open(QIODevice.WriteOnly) == False):
            QMessageBox.warning(0, "Error!", "Error opening file")
        else:
            xmlWriter.setDevice(xmlFile)
            xmlWriter.writeStartDocument()
            xmlWriter.writeStartElement("csiServices")

            portfolio = self.csiAtlante.servicesportfolio
            dictServices = {}
            dictServices = portfolio.getServices()

            i = 0
            for c in dictServices.values():
                xmlWriter.writeStartElement("service")
                xmlWriter.writeAttribute("name", c.name)
                xmlWriter.writeAttribute("url", c.url)
                xmlWriter.writeAttribute("usr", c.usr)
                xmlWriter.writeAttribute("pwd", c.compressed)
                #xmlWriter.writeCharacters("abcdefg")
                xmlWriter.writeEndElement()
                i += 1

            xmlWriter.writeEndElement()  # </csiServices>
            xmlWriter.writeEndDocument()

            msg = "Esportato!"
            QMessageBox.information(None, "Salvataggio services su file", msg, QMessageBox.Ok)

    def populateServiceConnectionList(self):
        """
        Metodo che popola la lista delle connessioni servizi e
        garantisce la sincronizzazione del dictionary col portafoglio dei servizi
        """
        s = QSettings()
        s.beginGroup("/CSIAtlante/services/")
        self.tabObj.cboServiceConnections.clear()
        self.tabObj.cboServiceConnections.addItems(s.childGroups())
        s.endGroup()

        self.setServiceConnectionListPosition()

        if self.tabObj.cboServiceConnections.count() == 0:
            # non ci sono connessioni: si deve disabilitare alcuni bottoni
            self.tabObj.btnServiceEdit.setEnabled(False)
            self.tabObj.btnServiceDelete.setEnabled(False)
            self.tabObj.btnServiceSaveFile.setEnabled(False)
        else:
            # ci sono connessioni: bisogna abilitare alcuni bottoni
            self.tabObj.btnServiceEdit.setEnabled(True)
            self.tabObj.btnServiceDelete.setEnabled(True)

    def setServiceConnectionListPosition(self):
        """
        Cerca e imposta l'indice posizionale nella lista della combobox delle connessioni ai servizi:
        cerca il servizio selected nella combo e ne prende l'indice,
        se non lo trova prende considera l'ultimo elemento della combo
        """
        s = QSettings()
        storedSelected = s.value('/CSIAtlante/services/selected', u'', type=unicode)

        found = False
        for i in range(self.tabObj.cboServiceConnections.count()):
            if self.tabObj.cboServiceConnections.itemText(i) == storedSelected:
                self.tabObj.cboServiceConnections.setCurrentIndex(i)
                found = True
                break

        if not found and self.tabObj.cboServiceConnections.count() > 0:
            # if storedSelected.isEmpty(): Porting QGIS 2.0
            if storedSelected is None:
                self.tabObj.cboServiceConnections.setCurrentIndex(0)
            else:
                self.tabObj.cboServiceConnections.setCurrentIndex(self.tabObj.cboServiceConnections.count() - 1)

    def selectedConnections(self):
        """
        Imposta il riferimento globale del plugin alla connessione selezionata nella combobox
        Il riferimento e' nel setting: "/CSIAtlante/connections/selected"
        """
        s = QSettings()
        connName = self.tabObj.cboConnections.currentText()
        s.setValue("/CSIAtlante/connections/selected", connName)

    def newConnection(self):
        """
        Crea una nuova connessione nel portafoglio DB mostrando un dialogo di inserimento
        """
        dlgNew = NewConnectionDialog()
        dlgNew.setWindowTitle("Nuova connessione db")
        if dlgNew.exec_() == QDialog.Accepted:
            self.populateConnectionList()

    def editConnection(self):
        """
        Modifica i dati della connessione DB selezionata nella combobox
        """
        s = QSettings()
        connName = self.tabObj.cboConnections.currentText()
        username = s.value("/CSIAtlante/connections/" + connName + "/username", u'', type=unicode)
        host = s.value("/CSIAtlante/connections/" + connName + "/host", u'', type=unicode)
        port = s.value("/CSIAtlante/connections/" + connName + "/port", u'', type=unicode)
        database = s.value("/CSIAtlante/connections/" + connName + "/database", u'', type=unicode)
        password = s.value("/CSIAtlante/connections/" + connName + "/password", u'', type=unicode)

        dlgEdit = NewConnectionDialog()
        dlgEdit.setWindowTitle("Modifica della connessione")
        dlgEdit.leName.setText(connName)
        dlgEdit.leHost.setText(host)
        dlgEdit.lePort.setText(port)
        dlgEdit.leDatabase.setText(database)
        dlgEdit.leUsername.setText(username)
        dlgEdit.lePassword.setText(password)

        if dlgEdit.exec_() == QDialog.Accepted:
            self.populateConnectionList()

    def modConnection(self, host, port, database, username, password):
        """
        Modifica i dati di una connessione DB

        @param host : host
        @param port : port
        @param database : database
        @param username : username
        @param password : password
        """
        if host != '':
            dlgNew = NewConnectionDialog()
            dlgNew.setWindowTitle("Modifica connessione db")
            # dlgNew.leName.setText("%s@%s:%s/%s" % (self.schema, self.host, self.porta, self.dbname))  #user@host:port/database
            cname = dlgNew.formatConnectionName(username, host, port, database)
            dlgNew.leName.setText(cname)

            dlgNew.leHost.setText(host)
            dlgNew.lePort.setText(port)
            dlgNew.leDatabase.setText(database)
            dlgNew.leUsername.setText(username)
            if dlgNew.exec_() == QDialog.Accepted:
                # pwdCoax = dlgNew.lePassword.text()
                QMessageBox.information(None, "TODO:", "Da implementare")

    def deleteConnection(self):
        """
        Elimina dal portafoglio la connessione DB selezionata nella combobox
        """
        s = QSettings()
        key = "/CSIAtlante/connections/" + self.tabObj.cboConnections.currentText()
        msg = "Rimuovere la connessione \n {0} \n e tutte le sue impostazioni?".format(self.tabObj.cboConnections.currentText())
        result = QMessageBox.information(None, "Conferma elimina", msg, QMessageBox.Ok | QMessageBox.Cancel)

        if result == QMessageBox.Ok:
            s.remove(key)
            self.tabObj.cboConnections.removeItem(self.tabObj.cboConnections.currentIndex())
            self.setServiceConnectionListPosition()

    def importConnections(self):
        """
        Importa da un file XML le connessioni DB da mettere nel portafoglio del plugin
        """
        self.fileName = QFileDialog.getOpenFileName(None, "Importa da file le connessioni ai DB", ".", "(*.xml *.XML)")

        if self.fileName is None:
            return

        error = None
        xmlFile = None
        try:
            xmlFile = QFile(self.fileName)
            if not xmlFile.open(QIODevice.ReadOnly):
                raise (IOError, unicode(xmlFile.errorString()))
#             if not dom.setContet(xmlFile):
#                 raise (ValueError, "could not parse XML")
        except (IOError, OSError, ValueError) as e:
            error = "Failed to open or import xml: %s" % e
        finally:
            if xmlFile is not None:
                # xmlFile.close()
                pass
            if error is not None:
                return False, error

        try:
            xml = QXmlStreamReader(xmlFile)
        except (IOError, OSError, ValueError) as e:
            error = "Failed to read xml: %s" % e
        finally:
            if error is not None:
                return False, error
            s = QSettings()
            while(not xml.atEnd() and not xml.hasError()):
                xml.readNext()
                token = xml.tokenType()
                if (token == QXmlStreamReader.StartDocument):
                    xml.readNext()
                    pass
                # if (token == QXmlStreamReader.StartElement):
                if xml.isStartElement():
                    if (xml.name() == 'postgis'):
                        cname = ''
                        cport = ''
                        cpassword = ''
                        cusername = ''
                        chost = ''
                        cdatabase = ''

                        attr = xml.attributes()
                        if (attr.hasAttribute('name')):
                            cname = attr.value('name')
                        if (attr.hasAttribute('port')):
                            cport = attr.value('port')
                        if (attr.hasAttribute('password') and attr.hasAttribute('name')):
                            cpassword = self.csiAtlante.connectionsportfolio.decompress(attr.value('password'), attr.value('name'))
                        if (attr.hasAttribute('username')):
                            cusername = attr.value('username')
                        if (attr.hasAttribute('host')):
                            chost = attr.value('host')
                        if (attr.hasAttribute('database')):
                            cdatabase = attr.value('database')

                        if cname is not None and cname != "":
                            key = "/CSIAtlante/connections/" + cname
                            # se cname gia' esiste: sovrascrive senza chiedere!
                            s.setValue(key + "/port", cport)
                            s.setValue(key + "/password", cpassword)
                            s.setValue(key + "/username", cusername)
                            s.setValue(key + "/host", chost)
                            s.setValue(key + "/database", cdatabase)

            xml.clear()

            # aggiornare lista connessioni
            self.populateConnectionList()

            msg = "Importato!"
            QMessageBox.information(None, "Import connessioni DB da file", msg, QMessageBox.Ok)

            if (xml.hasError()):
                QMessageBox.information(None, "Import connessioni DB da file", 'xml.hasError()', QMessageBox.Ok)
                pass

    def exportConnections(self):
        """
        Esporta su un file XML le connessioni del portafoglio DB
        """
        self.fileName = QFileDialog.getSaveFileName(None, "Salva su file le connessioni del portafoglio DB", ".", "eXtensible Markup Language (*.xml *.XML)")

        if self.fileName is None:
            return

        if not str(self.fileName.lower()).endswith(".xml"):
            self.fileName += ".xml"

        # export di tutti i services
        xmlWriter = QXmlStreamWriter()
        xmlWriter.setAutoFormatting(True)
        xmlFile = QFile(self.fileName)

        if (xmlFile.open(QIODevice.WriteOnly) == False):
            QMessageBox.warning(0, "Error!", "Error opening file")
        else:
            xmlWriter.setDevice(xmlFile)
            xmlWriter.writeStartDocument()
            xmlWriter.writeStartElement("qgsPgConnections")

            portfolio = self.csiAtlante.connectionsportfolio
            dictConnections = {}
            dictConnections = portfolio.getConnections()

            i = 0
            for c in dictConnections.values():
                xmlWriter.writeStartElement("postgis")
                xmlWriter.writeAttribute("port", c.port)
                xmlWriter.writeAttribute("saveUsername", "true")
                xmlWriter.writeAttribute("password", c.compressed)
                xmlWriter.writeAttribute("savePassword", "true")
                xmlWriter.writeAttribute("sslmode", "1")
                xmlWriter.writeAttribute("service", "")
                xmlWriter.writeAttribute("username", c.username)
                xmlWriter.writeAttribute("host", c.host)
                xmlWriter.writeAttribute("database", c.database)
                xmlWriter.writeAttribute("name", c.name)
                xmlWriter.writeAttribute("estimatedMetadata", "false")
                xmlWriter.writeEndElement()
                i += 1

            xmlWriter.writeEndElement()  # </qgsPgConnections>
            xmlWriter.writeEndDocument()

            msg = "Esportato!"
            QMessageBox.information(None, "Salvataggio connessioni su file", msg, QMessageBox.Ok)

    def populateConnectionList(self):
        """
        Metodo che popola la lista delle connessioni DB e
        garantisce la sincronizzazione del dictionary col portafoglio delle connessioni
        """
        s = QSettings()
        s.beginGroup("/CSIAtlante/connections/")
        self.tabObj.cboConnections.clear()
        self.tabObj.cboConnections.addItems(s.childGroups())
        s.endGroup()

        self.setConnectionListPosition()

        if self.tabObj.cboConnections.count() == 0:
            pass

    def setConnectionListPosition(self):
        """
        Cerca e imposta l'indice posizionale nella lista della combobox delle connessioni DB:
        cerca la connessione selected nella combo e ne prende l'indice,
        se non la trova prende considera l'ultimo elemento della combo
        """
        s = QSettings()
        storedSelected = s.value('/CSIAtlante/connections/selected', u'', type=unicode)

        found = False
        for i in range(self.tabObj.cboConnections.count()):
            if self.tabObj.cboConnections.itemText(i) == storedSelected:
                self.tabObj.cboConnections.setCurrentIndex(i)
                found = True
                break

        if not found and self.tabObj.cboConnections.count() > 0:
            if storedSelected is None:
                self.tabObj.cboConnections.setCurrentIndex(0)
            else:
                self.tabObj.cboConnections.setCurrentIndex(self.tabObj.cboConnections.count() - 1)

    def changeBehaviour(self, state):
        """Slot che riceve il segnale di cambio stato sul checkbox del comportamento locale del plugin:
        in base allo stato deve attivare il comportamento locale o dinamico del plugin
        @param self: checkbox
        @param state: Qt.Checked : locale | Qt.Unchecked : dinamico
        """
        s = QSettings()
        if (state == Qt.Checked):
            s.setValue("/CSIAtlante/conf/behaviour", 0)
            self.csiAtlante.behaviour = 0
            self.tabObj.groupBoxServiceConnections.setEnabled(False)
            self.tabObj.groupBoxConnections.setEnabled(False)
        else:
            s.setValue("/CSIAtlante/conf/behaviour", 1)
            self.csiAtlante.behaviour = 1
            self.tabObj.groupBoxServiceConnections.setEnabled(True)
            self.tabObj.groupBoxConnections.setEnabled(True)

    def changeStateTabFromConf(self, dictConf):
        """
        Metodo generico che rimuove o mantiene i tab indicati nel dictionary in input
        {
        flg_vector: 0,
        flg_progetti: 0,
        flg_raster: 0,
        flg_wms: 1,
        flg_tms: 0,
        flg_wfs: 0,
        flg_indica: 0,
        flg_indica_geo: 0
        }
        """
        #2to3 for key, value in dictConf.iteritems():
        for key, value in dictConf.items():
            LOGGER.debug("changeStateTabFromConf - %s: %d" % (key, value))
            if (value == 0):
                state = Qt.Unchecked
            else:
                state = Qt.Checked

            if (key == 'flg_vector'):
                self.changeStateTabPostgis(state)
            elif (key == 'flg_progetti'):
                self.changeStateTabProgetti(state)
            elif (key == 'flg_raster'):
                self.changeStateTabRaster(state)
            elif (key == 'flg_wms'):
                self.changeStateTabWMS(state)
            elif (key == 'flg_tms'):
                self.changeStateTabTMS(state)
            elif (key == 'flg_wfs'):
                self.changeStateTabWFS(state)
            elif (key == 'flg_indica'):
                self.changeStateTabIndica(state)
            elif (key == 'flg_indica_geo'):
                self.changeStateTabIndicaGeo(state)
            else:
                pass
        self.setTabDefault()

    def setTabDefault(self):
        """
        Imposta il focus sul tab di default: conf o se c'è va su postgis
        """
        indexTabDefault = self.ui.tabWidget.indexOf(self.ui.tabConf)
        if hasattr(self.ui, 'tabPostgis'):
            indexTabDefault = self.ui.tabWidget.indexOf(self.ui.tabPostgis)
        self.ui.tabWidget.setCurrentIndex(indexTabDefault)

    def changeStateTabProgetti(self, state):
        """Slot che riceve il segnale di cambio stato sul checkbox funzionalmente collegato al tab Progetti:
        in base allo stato deve abilitare o disabilitare (rimuovere) il tab
        @param self: checkbox
        @param state: Qt.Checked | Qt.Unchecked
        """
        if hasattr(self.ui, 'tabProgetti'):
            self.changeStateTab(self.ui.tabProgetti, state)

    def changeStateTabPostgis(self, state):
        """Slot che riceve il segnale di cambio stato sul checkbox funzionalmente collegato al tab Postgis:
        in base allo stato deve abilitare o disabilitare (rimuovere) il tab
        @param self: checkbox
        @param state: Qt.Checked | Qt.Unchecked
        """
        if hasattr(self.ui, 'tabPostgis'):
            self.changeStateTab(self.ui.tabPostgis, state)

    def changeStateTabRaster(self, state):
        """Slot che riceve il segnale di cambio stato sul checkbox funzionalmente collegato al tab Raster:
        in base allo stato deve abilitare o disabilitare (rimuovere) il tab
        @param self: checkbox
        @param state: Qt.Checked | Qt.Unchecked
        """
        if hasattr(self.ui, 'tabRaster'):
            self.changeStateTab(self.ui.tabRaster, state)

    def changeStateTabWMS(self, state):
        """Slot che riceve il segnale di cambio stato sul checkbox funzionalmente collegato al tab WMS:
        in base allo stato deve abilitare o disabilitare (rimuovere) il tab
        @param self: checkbox
        @param state: Qt.Checked | Qt.Unchecked
        """
        if hasattr(self.ui, 'tabWMS'):
            self.changeStateTab(self.ui.tabWMS, state)

    def changeStateTabCSW(self, state):
        """Slot che riceve il segnale di cambio stato sul checkbox funzionalmente collegato al tab CSW:
        in base allo stato deve abilitare o disabilitare (rimuovere) il tab
        @param self: checkbox
        @param state: Qt.Checked | Qt.Unchecked
        """
        if hasattr(self.ui, 'tabCSW'):
            self.changeStateTab(self.ui.tabCSW, state)

    def changeStateTabWFS(self, state):
        """Slot che riceve il segnale di cambio stato sul checkbox funzionalmente collegato al tab WFS:
        in base allo stato deve abilitare o disabilitare (rimuovere) il tab
        @param self: checkbox
        @param state: Qt.Checked | Qt.Unchecked
        """
        if hasattr(self.ui, 'tabWFS'):
            self.changeStateTab(self.ui.tabWFS, state)

    def changeStateTabTMS(self, state):
        """Slot che riceve il segnale di cambio stato sul checkbox funzionalmente collegato al tab TMS:
        in base allo stato deve abilitare o disabilitare (rimuovere) il tab
        @param self: checkbox
        @param state: Qt.Checked | Qt.Unchecked
        """
        if hasattr(self.ui, 'tabTMS'):
            self.changeStateTab(self.ui.tabTMS, state)

    def changeStateTabIndica(self, state):
        """Slot che riceve il segnale di cambio stato sul checkbox funzionalmente collegato al tab Indica:
        in base allo stato deve abilitare o disabilitare il tab
        @param self: checkbox
        @param state: Qt.Checked | Qt.Unchecked
        """
        if hasattr(self.ui, 'tabIndica'):
            self.changeStateTab(self.ui.tabIndica, state)

    def changeStateTabIndicaGeo(self, state):
        """Slot che riceve il segnale di cambio stato sul checkbox funzionalmente collegato al tab IndicaGeo:
        in base allo stato deve abilitare o disabilitare il tab
        @param self: checkbox
        @param state: Qt.Checked | Qt.Unchecked
        """
        if hasattr(self.ui, 'tabIndicaGeo'):
            self.changeStateTab(self.ui.tabIndicaGeo, state)

    def changeStateTabDisable(self, uiTabObj, state):
        """ Abilita o disabilita (grigio) un tab
        @param self: checkbox
        @param uiTabObj: puntatore all'oggetto tab da abilitare/disabilitare
        @param state: Qt.Checked | Qt.Unchecked
        """
        s = QSettings()
        if (state == Qt.Checked):
            uiTabObj.setEnabled(True)
            s.setValue("/CSIAtlante/conf/" + uiTabObj.objectName(), True)
        else:
            uiTabObj.setEnabled(False)
            s.setValue("/CSIAtlante/conf/" + uiTabObj.objectName(), False)

    def changeStateTab(self, uiTabObj, state):
        """ Abilita o disabilita (nasconde) un tab
        @param self: checkbox
        @param uiTabObj: puntatore all'oggetto tab da abilitare/disabilitare
        @param state: Qt.Checked | Qt.Unchecked
        """
        s = QSettings()
        uiObjectName = uiTabObj.objectName()

        if (state == Qt.Checked):
            # Inserisce *a codice* il tab indicato
            index = self.getIndexTabFromConfig(uiObjectName)
            name = self.getNameTabFromConfig(uiObjectName)
            #count = self.getCountTabFromConfig(uiObjectName)  # @UnusedVariable
            #countnow = self.ui.tabWidget.count()  # @UnusedVariable
            LOGGER.debug('changeStateTab INSERT TAB - CONFIG index: %d - name: %s - uiObjectName: %s' % (index, name, uiObjectName))

            absIndexTabDict = OrderedDict(self.indexTabDict)
            nowIndexTabDict = OrderedDict()
            for k in self.indexTabDict.keys():
                if hasattr(self.ui, k):
                    nowTabObj = getattr(self.ui, k)
                    nowObjectName = nowTabObj.objectName()
                    nowIndex = self.ui.tabWidget.indexOf(nowTabObj)
                    nowIndexTabDict[nowObjectName] = nowIndex
                    LOGGER.debug('k: %s - nowObjectName: %s - nowIndex: %d' % (k, nowObjectName, nowIndex))
                else:
                    del absIndexTabDict[k]
                    LOGGER.debug('k: %s ### DELETE ###' % (k))

            """
            OrderedDict([('tabProgetti', 0), ('tabPostgis', 1), ('tabRaster', 3), ('tabWMS', -1), ('tabIndica', -1), ('tabConf', 2), ('tabCSW', -1)])
            OrderedDict([('tabWMS', -1), ('tabIndica', -1), ('tabCSW', -1), ('tabProgetti', 0), ('tabPostgis', 1), ('tabConf', 2), ('tabRaster', 3)])
            !!!
            bug:
            questo nowIndexTabDict['tabRaster'] restuisce -1
            in console python: nowIndexTabDict['tabRaster'] restituisce 3
            !!!
            risolvere rimuovendo i ripetuti -1
            """
            import operator
            nowSortedList = sorted(nowIndexTabDict.items(), key=operator.itemgetter(1))
            nowIndexTabDict = OrderedDict(nowSortedList)
            for k, v in nowIndexTabDict.items():
                if v == -1:
                    del absIndexTabDict[k]

            msg = "ABS = {"
            for k, v in absIndexTabDict.items():
                msg = "%s(%s: %d), " % (msg, k, v)
                pass
            msg = "%s}" % (msg)
            LOGGER.debug(msg)

            msg = "NOW = {"
            for k, v in nowIndexTabDict.items():
                msg = "%s(%s: %d)," % (msg, k, v)
                pass
            msg = "%s}" % (msg)
            LOGGER.debug(msg)

            """
            now = {'tabWMS': 0, 'tabIndica': 1, 'tabConf': 2}
            abs = {'tabWMS': 3, 'tabIndica': 4, 'tabConf': 8}

            voglio inserire tabTMS che ha indice assoluto index: 7
            guardo dentro abs, ciclo ...
            devo inserirlo prima di 'tabConf': 8
            quindi in posizione now=2 (rubando la posizione a tabConf)

            for i in xrange(8, -1, -1):
                print i

            8 7 6 5 4 3 2 1 0
            """

            kfound = 'tabConf'
            for t in absIndexTabDict.items():
                if t[1] < index:
                    kfound = t[0]
                    LOGGER.debug('kfound t[0]: %s - t[1]: %d - index: %d' % (kfound, t[1], index))
                else:
                    kfound = t[0]
                    LOGGER.debug('kfound t[0]: %s - t[1]: %d - index: %d ### BREAK ###' % (kfound, t[1], index))
                    break

            LOGGER.debug('dopo BREAK - kfound: %s' % (kfound))
            nowIndex = nowIndexTabDict[kfound]
            LOGGER.debug('dopo BREAK - nowIndex: %d' % (nowIndex))
            self.ui.tabWidget.insertTab(nowIndex, uiTabObj, name)
            LOGGER.debug('insertTab nowIndex: %d - name: %s)' % (nowIndex, name))

            # riconnette segnale di attivazione tab
            #self.ui.tabWidget.currentChanged[int].connect(.......activateTab)

            uiTabObj.setEnabled(True)
            s.setValue("/CSIAtlante/conf/" + uiObjectName, True)
        else:
            # Rimuove *a codice* il tab indicato
            indexTab = self.ui.tabWidget.indexOf(uiTabObj)
            self.ui.tabWidget.removeTab(indexTab)
            LOGGER.debug('changeStateTab REMOVE TAB indexTab: %d uiObjectName: %s' % (indexTab, uiObjectName))
            uiTabObj.setEnabled(False)
            s.setValue("/CSIAtlante/conf/" + uiObjectName, False)

    def changeStateSerieStorica(self, state):
        """Slot che riceve il segnale di cambio stato sul checkbox della funzione Serie Storica nel tab Indicatori:
        in base allo stato deve abilitare o disabilitare anche il checkbox della visibilita' dei layer caricati
        @param self: checkbox
        @param state: Qt.Checked | Qt.Unchecked
        """
        self.tabObj.ckLayerAbilitati.setCheckState(state)
