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

 Date                 : 2015-10-26
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

# Import the PyQt and QGIS libraries
from PyQt4.QtCore import *  # @UnusedWildImport
from PyQt4.QtGui import *  # @UnusedWildImport
from qgis.core import *  # @UnusedWildImport
from qgis.gui import QgsMessageBar

# import logging
# from logging.handlers import RotatingFileHandler
import os
import bz2
import binascii
import copy
import datetime
import pickle

# Initialize Qt resources from file resources.py
import resources_rc  # @UnusedImport

# Import the code for the dialog
from csiatlantedialog import CsiAtlanteDialog
from newconnectiondialog import NewConnectionDialog
from aboutdialog import AboutDialog

import csiutils
from sgatools import GraphMapToolIdentify
from sgatools import ChartMapToolIdentify
import logging
from logging.handlers import RotatingFileHandler
#from __init__ import version
import wmstree
import urllib
import urllib2
import json
import threading
import time
import tempfile
from postgis_utils import CSIPostGisDBConnector

PROJECT_NAME = "CSIAtlante"

#LOG_PATH = ''.join([str(QFileInfo(os.path.realpath(__file__)).path()), '/logs'])
LOG_PATH = ''.join([tempfile.gettempdir(), '/CSI'])  # c:\users\xxx\appdata\local\temp\CSI
LOG_FILENAME = ''.join([LOG_PATH, '/', 'csiatlante.log'])
LOGGER_NAME = __name__   # 'CSIAtlante.csiatlante'

if __name__ == 'CSIAtlante.csiatlante':
    try:
        for name, data in inspect.getmembers("CSIAtlante.csiatlante", inspect.isclass):
            if (name == "csiLogger"):
                QMessageBox.information(None, "inspect CSIAtlante.csiatlante", "trovata class csiLogger")

        module = __import__("CSIAtlante.csiatlante")
        class_logger = getattr(module, "csiLogger")
        LOGGER = class_logger(LOGGER_NAME)
    except Exception, ex:
        LOGGER = logging.getLogger()
        LOGGER.setLevel(logging.DEBUG)
        LOGGER.debug("!!! Exception in try to import class: csiLogger !!!")

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

cache_json = ''
cache_rows = ''


def getJSONObj(url, usr, pwd, tab):
    """
    Restituisce un json ricavandolo via http da un web service.

    @param url: url del servizio es: http://osgis.csi.it/servizio.php
    @param usr: parametro user da dare in post al servizio
    @param pwd: parametro password da dare in post al servizio
    @param tab: parametro tipologia del tab da dare in post al servizio: 'geoservizi', 'vector', 'progetti', 'raster'
    """
    global cache_json
    global cache_rows

    query_args = {'usr': usr, 'pwd': pwd, 'tab': tab}
    encoded_args = urllib.urlencode(query_args)
    filehandle = urllib2.urlopen(url, encoded_args)

    lines = filehandle.readlines()
    filehandle.close()
    if lines[0][0] == '<':
        return None
    rows = '\n'.join(lines)

    # log per DEBUG
#     s = QSettings()
#     REMOTE_DBG = s.value(''.join([PROJECT_NAME, "/debug"]), False, type=bool)
#     if REMOTE_DBG:
#         logfile = ''.join([QFileInfo(os.path.realpath(__file__)).path(), '/', 'debug_json_', tab, '.log'])
#         wlog = open(logfile, "wt")
#         wlog.write(rows)
#         #wlog.write(json.dumps(rows, indent=2, separators=(',', ': ')))
#         wlog.close()

    #LOGGER = Logger(LOGGER_NAME)
    LOGGER.debug('--- SERVIZIO -----------------------------------------------------------------------------------')
    LOGGER.debug("%s?usr=%s&pwd=%s&tab=%s" % (url, usr, pwd, tab))
    LOGGER.debug('------------------------------------------------------------------------------------------------')
    LOGGER.debug(rows)
    LOGGER.debug('------------------------------------------------------------------------------------------------')

    if cache_rows != rows:
        cache_rows = rows

    cache_json = json.loads(cache_rows)

    return cache_json


def getJSONObjFromFile(tab):
    """
    Restituisce un json prelevandolo da un file locale presente nella cartella del plugin,
    es:
    locale_geoservizi.json
    locale_progetti.json
    locale_raster.json
    locale_vector.json
    locale_indica.json

    @param tab: parametro tipologia del tab: 'geoservizi', 'progetti', 'raster', 'vector'
    """
    # TODO: mettere a fattore comune con la getJSONObj
    global cache_json
    global cache_rows

    jsonfile = ''.join([QFileInfo(os.path.realpath(__file__)).path(), '/', 'locale_', tab, '.json'])

    filehandle = open(jsonfile, 'r')

    lines = filehandle.readlines()
    filehandle.close()
    if lines[0][0] == '<':
        return None

    clean_lines = [l.strip() for l in lines if l.strip()]
    rows = '\n'.join(clean_lines)

    # log per DEBUG
#     REMOTE_DBG = s.value(''.join([PROJECT_NAME, "/debug"]), False, type=bool)
#     if REMOTE_DBG:
#         logfile = ''.join([QFileInfo(os.path.realpath(__file__)).path(), '/', 'debug_locale_', tab, '.log'])
#         wlog = open(logfile, "wt")
#         wlog.write(rows)
#         #wlog.write(json.dumps(rows, indent=2, separators=(',', ': ')))
#         wlog.close()
    #LOGGER = Logger(LOGGER_NAME)
    LOGGER.debug("getJSONObjFromFile tab %s", (tab))
    LOGGER.debug(rows)

    if cache_rows != rows:
        cache_rows = rows
        #cache_json = json.loads(cache_rows)

    cache_json = json.loads(cache_rows)

    return cache_json


class Singleton(object):
    """
    Singleton interface:
    Overriding the __new__ method
    http://www.python.org/download/releases/2.2.3/descrintro/#__new__
    """
    def __new__(cls, *args, **kwds):
        it = cls.__dict__.get("__it__")
        if it is not None:
            return it
        cls.__it__ = it = object.__new__(cls)
        it.init(*args, **kwds)
        return it

    def init(self, *args, **kwds):
        pass


class LoggerManager(Singleton):
    """
    Logger Manager.
    Handles all logging files.
    """
    def init(self):
        self.logger = logging.getLogger()
        handler = None
        if not os.path.isdir(LOG_PATH):
            try:
                os.mkdir(LOG_PATH)    # create dir if it doesn't exist
            except:
                raise IOError("Couldn't create \"" + LOG_PATH + "\" folder. Check permissions")
        try:
            # handler = logging.FileHandler(LOG_FILENAME, "a")
            handler = RotatingFileHandler(LOG_FILENAME, 'a', maxBytes=1024 * 1024, backupCount=5, encoding='UTF-8', delay=0)
        except:
            raise IOError("Couldn't create/open file \"" + LOG_FILENAME + "\". Check permissions.")

        if REMOTE_DBG:
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.WARNING)

        formatter = logging.Formatter('%(asctime)s - %(module)s [%(lineno)d] %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def debug(self, loggername, msg):
        self.logger = logging.getLogger(loggername)
        self.logger.debug(msg)

    def error(self, loggername, msg):
        self.logger = logging.getLogger(loggername)
        self.logger.error(msg)

    def info(self, loggername, msg):
        self.logger = logging.getLogger(loggername)
        self.logger.info(msg)

    def warning(self, loggername, msg):
        self.logger = logging.getLogger(loggername)
        self.logger.warning(msg)


class csiLogger(object):
    """
    Logger object.
    """
    def __init__(self, loggername="root"):
        self.lm = LoggerManager()    # LoggerManager instance
        self.loggername = loggername    # logger name

    def debug(self, msg):
        self.lm.debug(self.loggername, msg)

    def error(self, msg):
        self.lm.error(self.loggername, msg)

    def info(self, msg):
        self.lm.info(self.loggername, msg)

    def warning(self, msg):
        self.lm.warning(self.loggername, msg)


class CsiAtlantePlugin(QObject):
    """
    Classe principale del plugin
    """
    def __init__(self, iface):
        """
        Inizializzazione
        """
        QObject.__init__(self)

        # Initialize singleton Logger and keep reference
        self.logger = csiLogger(LOGGER_NAME)
        LOGGER = self.logger

        # Save reference to the QGIS interface
        self.iface = iface

        # Get QGIS version
        try:
            self.QgisVersion = unicode(QGis.QGIS_VERSION_INT)
        except:
            self.QgisVersion = unicode(QGis.QGIS_VERSION)[0]

        # initialize plugin path
        self.path_plugin = os.path.abspath(os.path.dirname(__file__))

        # i18n support http://pyqt.sourceforge.net/Docs/PyQt4/i18n.html
        locale = QSettings().value("locale/userLocale")
        myLocale = locale[0:2]

        self.path_locale = ''.join([QFileInfo(os.path.realpath(__file__)).path(), '/i18n/csiatlante_', myLocale, '.qm'])

        if QFileInfo(self.path_locale).exists():
            self.translator = QTranslator()
            self.translator.load(self.path_locale)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # retrieve informations from metadata
        metadatafile = os.path.join(os.path.abspath(os.path.dirname(__file__)), "metadata.txt")
        s = QSettings(metadatafile, QSettings.IniFormat)
        s.setIniCodec('UTF-8')
        s.sync()
        self.version = s.value("version")
        self.name = s.value("name")
        self.description = s.value("description")

        # eventuale chiave di servizio per ***evitare*** la rinomina forzata di DB: vm-osstore2 con vm-osstore1
        self.connections_avoid_rename = s.value("/".join([PROJECT_NAME, "/connections/avoid_rename"]), False, type=bool)

        # patch per  rinomina forzata di DB: vm-osstore2 con vm-osstore1
        if (not self.connections_avoid_rename):
            ConnectionsPortfolio().patchConnections()

        # Crea e alimenta il portfolio delle connessioni e mantiene il riferimento
        self.connectionsportfolio = ConnectionsPortfolio()

        # Crea e alimenta il portfolio dei servizi e mantiene il riferimento
        self.servicesportfolio = ServicesPortfolio()

        # Definisce il comportamento di default del plugin: locale=0
        # eventualmetne viene sovrascritto alla creazione del dialog
        self.behaviour = 0

        # Flag che pilota il comportamento per la lettura dei WMS da cache
        # viene impostato a True allo startup e ad ogni cambio di servizio
        # viene impostato a False al primo aggiornamento dell'elenco
        self.useWmsCache = True

        self.cachePath = ''.join([QFileInfo(os.path.realpath(__file__)).path(), '/cache'])

        # Flags per notificare ai tab che il servizio di connessione è cambiato
        # settato in GestoreTab.changedServiceConnections()
        # discriminato in CsiAtlanteDialog.activateTab()
        self.servicechanged_not_initial = False
        self.servicechanged_tabProgetti = True
        self.servicechanged_tabPostgis = True
        self.servicechanged_tabRaster = True
        self.servicechanged_tabWMS = True
        self.servicechanged_tabIndica = True

        # PPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPP
        # PPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPP
        # PPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPP
        # PPPPPPPPPPPPPPP                               PPPPPPPPPPPPPPP
        # PPPPPPPPPPPPPPP             DEBUG             PPPPPPPPPPPPPPP
        # PPPPPPPPPPPPPPP                               PPPPPPPPPPPPPPP
        # PPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPP
        # PPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPP
        # PPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPP
        #
        #pydevd.settrace()
        #
        # PPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPP
        # PPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPP
        # PPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPP
        # PPPPPPPPPPPPPPP                               PPPPPPPPPPPPPPP
        # PPPPPPPPPPPPPPP             DEBUG             PPPPPPPPPPPPPPP
        # PPPPPPPPPPPPPPP                               PPPPPPPPPPPPPPP
        # PPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPP
        # PPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPP
        # PPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPPP

        # Save reference to Canvas
        self.canvas = self.iface.mapCanvas()

        # Create the dialog and keep reference
        self.dlg = CsiAtlanteDialog(self)

        # Inizializzazione delle schede attive in base ai flag di configurazione, va dopo che self.dlg e' istanziato
        self.schede_visibili()

        # definizione custom property per layer
        self.tag_seriestorica = 'serie_storica'

        # sga_toolbar
        self.sga_toolbar = self.iface.addToolBar(u'Grafici interattivi Indicatori - Serie storica')
        self.sga_toolbar.setObjectName(u'SGA Tools')

        # Empty the internal cursor stack of that QApplication::instance
        csiutils.Cursor.EmptyStack()

        # Last operations in init
        self.servicechanged_not_initial = True
        self.alreadyloaded = False

    def initGui(self):
        """
        Inizializza la configurazione del plugin
        """

        if int(self.QgisVersion) < 1.8:
            QMessageBox.warning(self.iface.mainWindow(), "CSI Atlante",
                               QCoreApplication.translate("CSI Atlante", "Quantum GIS version detected: ") + unicode(self.QgisVersion) + ".xx\n" +
                               QCoreApplication.translate("CSI Atlante", "Questa versione richiede QGIS version 1.8"))
            return None

        icon_plugin = os.path.join(self.path_plugin, 'icons/icon.png')
        self.action_run = QAction(QIcon(icon_plugin), u"CSI Atlante", self.iface.mainWindow())
        self.action_run.setStatusTip(QCoreApplication.translate("CSI Atlante", "Accesso organizzato a dati e geoservizi"))

        icon_about = os.path.join(self.path_plugin, 'icons/about.png')
        self.action_about = QAction(QIcon(icon_about), "About", self.iface.mainWindow())

        icon_chart_identify = os.path.join(self.path_plugin, 'icons/chartidentify.png')
        self.action_chart_identify = QAction(QIcon(icon_chart_identify), "Grafici Georiferiti Indicatori - Serie storica", self.iface.mainWindow())
        self.action_chart_identify.setCheckable(True)

        icon_graph_identify = os.path.join(self.path_plugin, 'icons/graphidentify.png')
        self.action_graph_identify = QAction(QIcon(icon_graph_identify), "Grafici Interattivi Indicatori - Serie storica", self.iface.mainWindow())
        self.action_graph_identify.setCheckable(True)

        # connect the actions to the slot_run method and slot_about method
        QObject.connect(self.action_run, SIGNAL("triggered()"), self.slot_run)
        QObject.connect(self.action_about, SIGNAL("triggered()"), self.slot_about)
        QObject.connect(self.action_chart_identify, SIGNAL("triggered()"), self.slot_chart_identify)
        QObject.connect(self.action_graph_identify, SIGNAL("triggered()"), self.slot_graph_identify)

        # Add sga_toolbar button and menu item
        self.iface.addToolBarIcon(self.action_run)
        self.iface.addPluginToMenu(u"&CSI Atlante", self.action_run)
        self.iface.addPluginToMenu(u"&CSI Atlante", self.action_about)

        QObject.connect(self.dlg, SIGNAL("visibilityChanged ( bool )"), self.slot_widget_visible)
        QObject.connect(self.dlg.ui.btCarica, SIGNAL("clicked()"), self.slot_carica_selezionati)
        QObject.connect(self.dlg.ui.btAggiorna, SIGNAL("clicked()"), self.slot_aggiorna_elenco)
        QObject.connect(self.dlg.ui.btSvuotaToc, SIGNAL("clicked()"), self.slot_svuota_toc)

        # Add tools
       
#       # connect e disconnect di toolChartSerieStorica sono gestite in CsiAtlanteDialog::GestoreTabObject
#       #QObject.connect(self.dlg.ui.indica_btSerieStorica, SIGNAL("clicked()"), self.canvas.setMapTool(self.toolChartSerieStorica))

        # aggiunta alla sga_toolbar dei tools per i grafici
        self.sga_toolbar.addAction(self.action_chart_identify)
        self.sga_toolbar.addAction(self.action_graph_identify)

        self.iface.addDockWidget(Qt.LeftDockWidgetArea, self.dlg)

        # Build an action list from QGIS navigation toolbar
        actionList = self.iface.mapNavToolToolBar().actions()
        # Add actions from QGIS attributes toolbar (handling QWidgetActions)
        tmpActionList = self.iface.attributesToolBar().actions()
        for action in tmpActionList:
            if isinstance(action, QWidgetAction):
                actionList.extend(action.defaultWidget().actions())
            else:
                actionList.append(action)

        # Build a group with actions from actionList and add your own action
        group = QActionGroup(self.iface.mainWindow())
        group.setExclusive(True)
        for action in actionList:
            group.addAction(action)
        group.addAction(self.action_graph_identify)
        group.addAction(self.action_chart_identify)

    def __disconnect(self):
        """
        Disconnette tutti i segnali
        """
        QObject.disconnect(self.action_run, SIGNAL("triggered()"), self.slot_run)
        QObject.disconnect(self.action_about, SIGNAL("triggered()"), self.slot_about)
        QObject.disconnect(self.action_chart_identify, SIGNAL("triggered()"), self.slot_chart_identify)
        QObject.disconnect(self.action_graph_identify, SIGNAL("triggered()"), self.slot_graph_identify)
        QObject.disconnect(self.dlg, SIGNAL("visibilityChanged ( bool )"), self.slot_widget_visible)
        QObject.disconnect(self.dlg.ui.btCarica, SIGNAL("clicked()"), self.slot_carica_selezionati)
        QObject.disconnect(self.dlg.ui.btAggiorna, SIGNAL("clicked()"), self.slot_aggiorna_elenco)
        QObject.disconnect(self.dlg.ui.btSvuotaToc, SIGNAL("clicked()"), self.slot_svuota_toc)
#         # connect e disconnect di toolChartSerieStorica sono gestite in CsiAtlanteDialog::GestoreTabObject
#         #QObject.connect(self.dlg.ui.indica_btSerieStorica, SIGNAL("clicked()"), self.canvas.setMapTool(self.toolChartSerieStorica))
        self.dlg.disconnect()

    def unload(self):
        """
        Remove the plugin menu item and icon
        """
        # self.iface.removePluginMenu( QCoreApplication.translate( "CSI Atlante", "CSI Atlante" ), self.action_run )
        # self.iface.removePluginMenu( QCoreApplication.translate( "CSI Atlante", "CSI Atlante" ), self.action_about )
        self.iface.removePluginMenu(u"&CSI Atlante", self.action_run)
        self.iface.removePluginMenu(u"&CSI Atlante", self.action_about)
        self.iface.removeToolBarIcon(self.action_run)

        self.__disconnect()
        #self.dlg = None
        del self.dlg
        del self.sga_toolbar
        #QMessageBox.information(None, "CSIAtlante", "unload")
        pass

    def slot_run(self):
        """
        Run
        """
        self.show_hide_dock_widget()

    def slot_about(self):
        """
        Show About Dialog
        """
        dlgAbout = AboutDialog(self.iface.mainWindow())
        dlgAbout.exec_()

    def slot_chart_identify(self):
        """
        Chart Identify  (modeless)
        """
        self.toolChartSerieStorica = ChartMapToolIdentify(self.iface, self)
        self.canvas.setMapTool(self.toolChartSerieStorica)

    def slot_graph_identify(self):
        """
        Show Graph Identify Dialog (modeless)
        """
        self.toolGraphSerieStorica = GraphMapToolIdentify(self.iface, self)
        self.canvas.setMapTool(self.toolGraphSerieStorica)

    def show_hide_dock_widget(self):
        """
        Show Hide Dock Widget
        """
        if self.dlg.isVisible():
            self.dlg.hide()
        else:
            self.dlg.show()

    def slot_widget_visible(self, bvisible):
        """
        visibilityChanged
        """
        if bvisible:
            if not self.alreadyloaded:
                self.alreadyloaded = True
                self.slot_aggiorna_elenco()

    def getSaveAsFileName(self):
        """
        getSaveAsFileName
        """
        saveAsFileName = QFileDialog.getSaveFileName(self.dlg,
                      "Save QGIS Project file as...",
                      ".",
                      "QGIS Project Files (*.qgs)")
        if saveAsFileName is None:
            return ''
        if not str(saveAsFileName.strip()).endswith('.qgs'):
            saveAsFileName += '.qgs'
        return saveAsFileName

    def getNewProjectPath(self):
        """
        getNewProjectPath
        """
        project = QgsProject.instance()
        saveAsFileName = self.getSaveAsFileName()
        project.setFileName(saveAsFileName)
        project.write()
        title = project.title  # @UnusedVariable: title
        return saveAsFileName

    def azzera_elenco(self):
        """
        Azzera e svuota l'elenco delle informazioni gestite per il tab corrente:
        UNUSED
        """
        try:
            csiutils.Cursor.Hourglass()

            # clearTreeWidget per il tab corrente
            if self.dlg.ui.tabWidget.currentWidget() == self.dlg.ui.tabProgetti:
                self.dlg.gestorePROGETTI.clearTreeWidget()

            elif self.dlg.ui.tabWidget.currentWidget() == self.dlg.ui.tabPostgis:
                self.dlg.gestoreVECTOR.clearTreeWidget()

            elif self.dlg.ui.tabWidget.currentWidget() == self.dlg.ui.tabIndica:
                self.dlg.gestoreINDICA.clearTreeWidget()

            elif self.dlg.ui.tabWidget.currentWidget() == self.dlg.ui.tabRaster:
                self.dlg.gestoreRASTER.clearTreeWidget()

            elif self.dlg.ui.tabWidget.currentWidget() == self.dlg.ui.tabWMS:
                self.dlg.gestoreWMS.clearTreeWidget()

            else:
                pass

        finally:
            csiutils.Cursor.Restore()

    def slot_aggiorna_elenco(self):
        """
        Aggiorna l'elenco delle informazioni gestite per il tab corrente:
        si riconnette al servizio che restituisce il json e rialimenta l'elenco.
        Se il comportamento e' locale ricava l'elenco da un file json locale da file system
        """
        if not hasattr(self, 'dlg'):
            return

        try:
            csiutils.Cursor.Hourglass()

            # Ricava la tipologia dell'elenco dal tab corrente
            if self.dlg.ui.tabWidget.currentWidget() == self.dlg.ui.tabProgetti:
                tab = "progetti"
            elif self.dlg.ui.tabWidget.currentWidget() == self.dlg.ui.tabPostgis:
                tab = "vector"
            elif self.dlg.ui.tabWidget.currentWidget() == self.dlg.ui.tabIndica:
                tab = "indica"
            elif self.dlg.ui.tabWidget.currentWidget() == self.dlg.ui.tabRaster:
                tab = "raster"
            elif self.dlg.ui.tabWidget.currentWidget() == self.dlg.ui.tabWMS:
                tab = "geoservizi"
            else:
                tab = "unknown"

            jsonObj = ''
            if self.behaviour == 0:
                # Se il comportamento e' locale ricava l'elenco da un file json locale su file system
                try:
                    jsonObj = getJSONObjFromFile(tab)
                except Exception, ex:
                    txt = str(ex)
                    QMessageBox.information(None, "Errore", \
                        "Impossibile leggere l'elenco dal file:\n%s " % (''.join(['locale_', tab, '.json'])))
                    csiutils.Cursor.Restore()
                    return
            else:
                # Ricava i dati dalla connessione del servizio attivo
                url, usr, pwd = self.dlg.getServiceUrlUsrPwd()
                try:
                    jsonObj = getJSONObj(url, usr, pwd, tab)
                except Exception, ex:
                    txt = str(ex)
                    pwdfake = "********"
                    QMessageBox.information(None, "Errore", \
                        "[%s]\nImpossibile leggere l'elenco dal servizio:\nverificare la connessione di rete o\nil contenuto della risposta del servizio:\n\n%s?usr=%s&pwd=%s&tab=%s" % (txt, url, usr, pwdfake, tab))
                    csiutils.Cursor.Restore()
                    # no return procede oltre
                    # return

            # Aggiorna e carica il tree solo per il tab corrente
            if self.dlg.ui.tabWidget.currentWidget() == self.dlg.ui.tabProgetti:
                # disabilitato
                csiutils.Cursor.Restore()
                self.projInfoTree = PROJECTInfo.readFromJson(jsonObj)
                self.dlg.gestorePROGETTI.clearTreeWidget()
                datiCat = [t.category for t in self.projInfoTree]
                self.dlg.gestorePROGETTI.loadCombo(datiCat)
                for tree in self.projInfoTree:
                    self.dlg.gestorePROGETTI.loadTreeWidget(tree)

            elif self.dlg.ui.tabWidget.currentWidget() == self.dlg.ui.tabPostgis:
                self.postgisInfoTree = POSTGISInfo.readFromJson(jsonObj)
                self.dlg.gestoreVECTOR.clearTreeWidget()
                datiCat = [t.category for t in self.postgisInfoTree]
                if len(datiCat) > 0:
                    self.dlg.gestoreVECTOR.loadCombo(datiCat)
                    for tree in self.postgisInfoTree:
                        self.dlg.gestoreVECTOR.loadTreeWidget(tree)
                else:
                    msg = ""
                    if self.behaviour == 0:
                        msg = "Nessun Dato Postgis presente in elenco locale"
                    else:
                        msg = "Nessun Dato Postgis presente nella tabella del gruppo:\n %s \n\nper il servizio attivo: \n%s" % (self.dlg.getServiceUrlUsrPwd()[1], self.dlg.getServiceUrlUsrPwd()[0])
                    self.iface.messageBar().pushMessage("Attenzione", msg, level=QgsMessageBar.CRITICAL)
                    csiutils.Cursor.Restore()

            elif self.dlg.ui.tabWidget.currentWidget() == self.dlg.ui.tabIndica:
                self.indicaInfoTree = INDICAInfo.readFromJson(jsonObj)
                self.dlg.gestoreINDICA.clearTreeWidget()
                datiCat = [t.category for t in self.indicaInfoTree]
                if len(datiCat) > 0:
                    self.dlg.gestoreINDICA.loadCombo(datiCat)

                    for topTree in self.indicaInfoTree:
                        self.dlg.gestoreINDICA.loadTreeWidget(topTree)

                    datiUnita = self.dlg.gestoreINDICA.getValoriUnita(self.indicaInfoTree)
                    if len(datiUnita) > 0:
                        self.dlg.gestoreINDICA.loadComboUnita(datiUnita)

                    datiPeriodicita = self.dlg.gestoreINDICA.getValoriPeriodicita(self.indicaInfoTree)
                    if len(datiPeriodicita) > 0:
                        self.dlg.gestoreINDICA.loadComboPeriodicita(datiPeriodicita)

                else:
                    msg = ""
                    if self.behaviour == 0:
                        msg = "Nessun Dato Postgis Indicatori presente in elenco locale"
                    else:
                        msg = "Nessun Dato Postgis Indicatori presente nella tabella del gruppo:\n %s \n\nper il servizio attivo: \n%s" % (self.dlg.getServiceUrlUsrPwd()[1], self.dlg.getServiceUrlUsrPwd()[0])
                    self.iface.messageBar().pushMessage("Attenzione", msg, level=QgsMessageBar.CRITICAL)
                    csiutils.Cursor.Restore()

            elif self.dlg.ui.tabWidget.currentWidget() == self.dlg.ui.tabRaster:
                self.rasterInfoTree = RASTERInfo.readFromJson(jsonObj)
                self.dlg.gestoreRASTER.clearTreeWidget()
                rasterCat = [t.category for t in self.rasterInfoTree]
                if len(rasterCat) > 0:
                    self.dlg.gestoreRASTER.loadCombo(rasterCat)
                    for tree in self.rasterInfoTree:
                        self.dlg.gestoreRASTER.loadTreeWidget(tree)
                else:
                    msg = ""
                    if self.behaviour == 0:
                        msg = "Nessun Dato Raster presente in elenco locale"
                    else:
                        msg = "Nessun Dato Raster presente nella tabella del gruppo:\n %s \n\nper il servizio attivo: \n%s" % (self.dlg.getServiceUrlUsrPwd()[1], self.dlg.getServiceUrlUsrPwd()[0])
                    self.iface.messageBar().pushMessage("Attenzione", msg, level=QgsMessageBar.CRITICAL)
                    csiutils.Cursor.Restore()

            elif self.dlg.ui.tabWidget.currentWidget() == self.dlg.ui.tabWMS:
                # QMessageBox.information(None, "slot_aggiorna_elenco", "self.useWmsCache: " + str(self.useWmsCache) + "\nself.servicechanged_tabWMS: " + str(self.servicechanged_tabWMS))

                show_msg = True
                if self.servicechanged_tabWMS == True:
                    show_msg = False
                cached = False
                cacheDate = None
                cacheFile = None
                cacheToDo = True
                go_on = True

                """
                caso A: usa la cache wms per il servizio attivo
                sottocaso A1: se per il servizio attivo la cache non esiste setta il flag cacheToDo e rimanda a caso B
                sottocaso A2: se per il servizio attivo la cache e' obsoleta o corrotta setta il flag cacheToDo e rimanda a caso B

                caso B: non usa la cache wms per il servizio attivo ma carica il json e esegue tutte le getcapabilities, alimentando quindi anche la cache
                sottocaso B1: se all'inizio o in una situazione in cui non esiste la cache non mostra messaggio di conferma creazione e procede
                sottocaso B2: in caso di bottone aggiona cache, mostra prima messaggio di conferma creazione e procede solo se risposta affermativa
                """
                if (self.useWmsCache):
                    cacheToDo = False

                    # TODO:
                    # automatizzare la gestione della cache in base alla data
                    cached, cacheDate, cacheFile = self.dlg.getServiceWmsCacheValues()

                    # QMessageBox.information(None, "cache", "".join([str(cached), '\n', cacheDate, '\n', cacheFile]))

                    if not cached:
                        # QMessageBox.information(None, "slot_aggiorna_elenco", "not cached")
                        cacheToDo = True
                    # patch ***PUR*** e.c
                    cacheFile = cacheFile.split("/")[-1]
                    cacheFullName = ''.join([self.cachePath, '/', cacheFile])
                    if not os.path.isfile(cacheFullName):
                        # QMessageBox.information(None, "slot_aggiorna_elenco", "not os.path.isfile(cacheFullName)" + "\n" + cacheFullName)
                        cacheToDo = True
                    if not os.access(cacheFullName, os.R_OK):
                        # QMessageBox.information(None, "slot_aggiorna_elenco", "not os.access(cacheFullName, os.R_OK)" + "\n" + cacheFullName)
                        cacheToDo = True

                # QMessageBox.information(None, "slot_aggiorna_elenco", "cacheToDo:" + "\n" + str(cacheToDo))

                if (not cacheToDo):
                    """
                    caso A: usa la cache wms per il servizio attivo
                    """
                    self.wmsInfoList = WMSInfo.readFromCache(cacheFullName)
                    # caricamento strutture dalla wmsInfoList
                    wmsCat = [t.category for t in self.wmsInfoList]
                    if len(wmsCat) > 0:
                        self.dlg.gestoreWMS.clearTreeWidget()
                        self.dlg.gestoreWMS.loadCombo(wmsCat)

                        for wmsInfo in self.wmsInfoList:
                            # qui la getWMSTree() trova wmsInfo.wmsTree già istanziato e quindi al suo interno non richiama la __ParseCapabilities
                            self.dlg.gestoreWMS.loadTreeWidget(wmsInfo.getWMSTree())
                    # flag
                    self.useWmsCache = False
                    go_on = False
                else:
                    if show_msg:
                        msg = "Il caricamento dei geoservizi potrebbe essere una operazione lunga:\ndipende dal numero di wms da caricare e dalle condizioni di rete"
                        msg = msg + "\n\nPer ottenere vantaggi in termini di prestazioni \noccorre generare la cache per i geoservizi"
                        msg = msg + "\n\nProcedere?\n\nOK = Aggiornare ora la cache\nCancel = Rimandare"
                        result = QMessageBox.information(None, "Aggiornamento Cache con Elenco Geoservizi", msg, QMessageBox.Ok | QMessageBox.Cancel)
                        if result == QMessageBox.Ok:
                            go_on = True
                        else:
                            go_on = False
                    else:
                        go_on = True

                if (go_on):
                    """
                    caso B: genera la cache wms per il servizio attivo
                    """
                    # QMessageBox.information(None, "go_on cache", "genera la cache wms per il servizio attivo")
                    self.dlg.gestoreWMS.clearTreeWidget()
                    self.dlg.gestoreWMS.clearCombo()

                    self.wmsInfoList = WMSInfo.readFromJson(jsonObj)
                    wmsInfoListCount = len(self.wmsInfoList)

                    # caricamento strutture dalla wmsInfoList
                    wmsCat = [t.category for t in self.wmsInfoList]
                    if len(wmsCat) > 0:
                        msg = "Creazione della Cache per i WMS del servizio attivo"
                        progressMessageBar = self.iface.messageBar().createMessage(msg)
                        progress = QProgressBar()
                        progress.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                        progress.setMaximum(wmsInfoListCount)
                        progressMessageBar.layout().addWidget(progress)
                        self.iface.messageBar().pushWidget(progressMessageBar, self.iface.messageBar().INFO)
                        #self.dlg.gestoreWMS.clearTreeWidget()
                        self.dlg.gestoreWMS.loadCombo(wmsCat)
                        #
                        # @TODO:
                        # usare i threading per sfruttare anche interrupt...
                        #
                        # http://snorf.net/blog/2013/12/07/multithreading-in-qgis-python-plugins/
                        # https://mayaposch.wordpress.com/2011/11/01/how-to-really-truly-use-qthreads-the-full-explanation/
                        # http://gis.stackexchange.com/questions/64831/how-do-i-prevent-qgis-from-being-detected-as-not-responding-when-running-a-hea/64928#64928
                        #
                        i = 0
                        for wmsInfo in self.wmsInfoList:
                            i = i + 1
                            progress.setValue(i)
                            QgsMessageLog.logMessage("Cache WMS [%s] - %s" % (str(i), wmsInfo.wmsURL), 'CSI Atlante')
                            LOGGER.debug("Cache WMS [%s] - %s" % (str(i), wmsInfo.wmsURL))
                            self.iface.mainWindow().statusBar().showMessage("[%s] %s" % (str(i), wmsInfo.wmsURL))
                            # qui la getWMSTree() trova wmsInfo.wmsTree == None e quindi al suo interno richiama la __ParseCapabilities
                            self.dlg.gestoreWMS.loadTreeWidget(wmsInfo.getWMSTree())

                        # costruzione cache
                        name = self.dlg.getServiceName()
                        if name is None or name == '':
                            name = "csiatlante"
                        cacheFullName = ''.join([self.cachePath, '/', name, '.ecx'])
                        result = WMSInfo.writeToCache(cacheFullName, self.wmsInfoList)
                        if result == 0:
                            # scrittura cache ok
                            now = datetime.datetime.now()
                            cacheDate = now.strftime('%d/%m/%Y %H:%M:%S')  # 04/04/2014 15:59:23
                            cached = True
                            # patch ***PUR*** e.c
                            cacheFileNameOnly = ''.join([name, '.ecx'])
                            self.dlg.setServiceWmsCacheValues(cached, cacheDate, cacheFileNameOnly)
                        else:
                            QMessageBox.information(None, "Errore Cache", "Creazione cache fallita\nresult: " + str(result))
                            pass

                        # Termine messaggio creazione cache
                        self.iface.messageBar().clearWidgets()
                        self.iface.mainWindow().statusBar().clearMessage()
                    else:
                        # QMessageBox.information(None, "go_on cache", "len(wmsCat) <= 0 : " + str(len(wmsCat)) + "\n self.behaviour: " + str(self.behaviour))
                        # len(wmsCat) <= 0 : nessun wms da presentare!
                        msg = ""
                        if self.behaviour == 0:
                            msg = "Nessun WMS presente nell' elenco locale"
                        else:
                            msg = "Nessun WMS presente nella tabella del gruppo:\n %s \n\nper il servizio attivo: \n%s" % (self.dlg.getServiceUrlUsrPwd()[1], self.dlg.getServiceUrlUsrPwd()[0])
                        #QMessageBox.information(None, "go_on cache", msg)
                        self.iface.messageBar().pushMessage("Attenzione", msg, level=self.iface.messageBar().CRITICAL)
                        csiutils.Cursor.Restore()
                    pass
                else:
                    # go_on == false
                    csiutils.Cursor.Restore()
                    pass

            else:
                # TODO: eventuali tab futuri...
                # ######################################################################################################
                # log per DEBUG
                #s = QSettings()
                #REMOTE_DBG = s.value(''.join([PROJECT_NAME, "/debug"]), False, type=bool)
                #if REMOTE_DBG:
                #    from time import gmtime, strftime
                #    strnow = strftime("%Y-%m-%d %H:%M:%S", gmtime())
                #    logfile = ''.join([QFileInfo(os.path.realpath(__file__)).path(), '/', 'debug_csiutils', '.log'])
                #    fw = open(logfile, 'a')
                #    fw.write(''.join([strnow, ' : ', 'slot_aggiorna_elenco :: Arrow 6', '\n']))
                #    fw.flush()
                #    fw.close()
                # ######################################################################################################
                csiutils.Cursor.Restore()
                pass

        finally:
            csiutils.Cursor.EmptyStack()

    def schede_visibili(self):
        """
        Aggiorna la visibilita' delle schede cosi' come configurate da servizio:
        si connette al servizio che restituisce il json e in funzione del risultato
        rimuove o mantiene ciascun tab dalla gui
        """
        if not hasattr(self, 'dlg'):
            #QMessageBox.information(None, "Errore", "schede_visibili: l'oggetto dlg del plugin non esiste ancora! ")
            return

        tab = "conf"
        try:
            csiutils.Cursor.Hourglass()

            jsonObj = {}
            if self.behaviour == 0:
                # Se il comportamento e' locale ricava l'elenco da un file json locale su file system
                try:
                    jsonObj = getJSONObjFromFile(tab)
                except Exception, ex:
                    txt = str(ex)
                    QMessageBox.information(None, "Errore", \
                        "Impossibile leggere l'elenco dal file:\n%s " % (''.join(['locale_', tab, '.json'])))
                    csiutils.Cursor.Restore()
                    return
            else:
                # Ricava i dati dalla connessione del servizio attivo
                url, usr, pwd = self.dlg.getServiceUrlUsrPwd()
                try:
                    jsonObj = getJSONObj(url, usr, pwd, tab)
                except Exception, ex:
                    txt = str(ex)
                    QMessageBox.information(None, "Errore", \
                        "Impossibile leggere l'elenco dal servizio:\n%s \ntab: \n%s \nControllare la connessione di rete.\n[%s]" % (url, tab, txt))
                    csiutils.Cursor.Restore()

            if 'flg_vector' in jsonObj.keys():
                pass
                LOGGER.debug("schede_visibili :: esiste flg_vector --> si tratta di servizio nuovo OSGIS2")
                #QMessageBox.information(None, "schede_visibili", "DEBUG\nflg_vector trovato")
            else:
                LOGGER.debug("schede_visibili :: NON esiste flg_vector --> si tratta di servizio vecchio OSGIS! oppure RETE assente!")
                QMessageBox.information(None, "schede_visibili",
                                        "Attenzione!\n\nSi sta utilizzando un servizio non compatibile con questa versione di plugin: \
                                        \n\nplugin: CSIAtlante %s \nservizio: %s \n\nVerificare nel tab 'Impostazioni' il servizio in uso\
                                        \n\nPer informazioni contattare: cartografia@csi.it" % (self.version, url))
                jsonObj = {
                            'flg_vector': 1,
                            'flg_progetti': 0,
                            'flg_raster': 0,
                            'flg_wms': 0,
                            'flg_tms': 0,
                            'flg_wfs': 0,
                            'flg_indica': 0,
                            'flg_indica_geo': 0
                            }

            self.confInfo = CONFInfo.readFromJson(jsonObj)

            msg = "schede_visibili: flg_vector, flg_progetti, flg_raster, flg_wms, flg_tms, flg_wfs, flg_indica, flg_indica_geo"
            LOGGER.debug(msg)
            msg = "schede_visibili: %s" % (str(self.confInfo))
            LOGGER.debug(msg)

            self.dlg.gestoreCONF.changeStateTabFromConf(jsonObj)

        finally:
            csiutils.Cursor.EmptyStack()

    def slot_carica_selezionati(self):
        """
        Metodo eseguito dal bottone carica
        gestisce il caricamento degli elementi selezionati in un'elenco:
        la specializzazione del caricamento avviene in base al tab corrente
        """
        #self.dlg.Commit()  # serve solo per tab progetti!
        try:
            csiutils.Cursor.Hourglass()

            if self.dlg.ui.tabWidget.currentWidget() == self.dlg.ui.tabProgetti:
                projectList = self.dlg.gestorePROGETTI.treeWidgetGetSelectedList()
                if len(projectList) > 0:
                    __, usr, pwd = self.dlg.getServiceUrlUsrPwd()
                    if usr == '':
                        QMessageBox.information(None, "Errore", "Inserire utente e password per Progetti")
                        return

                    url = self.dlg.getServiceReadProjectUrl()
                    pcon = [p for p in projectList]
                    pcon.reverse()
                    for info in pcon:
                        info.LoadProject(self.iface, url, usr, pwd)

            elif self.dlg.ui.tabWidget.currentWidget() == self.dlg.ui.tabWMS:
                layerList = self.dlg.gestoreWMS.treeWidgetGetSelectedList()
                selWMS = WMSSelection.getWMSSelectionList_LayerList(layerList)
                if len(selWMS) > 0:
                    for wm in selWMS:
                        grouped, srs, outputformat, abilita, usadesc, stampabile = self.dlg.wms_getGeneralSettings()
                        self.addWMSLayer(wm, str(srs), grouped, str(outputformat), abilita, usadesc, stampabile)

            elif self.dlg.ui.tabWidget.currentWidget() == self.dlg.ui.tabPostgis:
                pgisList = self.dlg.gestoreVECTOR.treeWidgetGetSelectedList()
                if len(pgisList) > 0:
                    abilitati = self.dlg.dati_getAbilitati()
                    tcon = [t for t in pgisList if (t.host is not None and t.host != '')]
                    tcon.reverse()
                    for info in tcon:
                        info.loadVectorLayer(self.iface, self.dlg.getServiceReadQmlUrl(), abilitati, True)

            elif self.dlg.ui.tabWidget.currentWidget() == self.dlg.ui.tabIndica:
                pgisList = self.dlg.gestoreINDICA.treeWidgetGetSelectedList()
                if self.dlg.indica_getStoricizzati():
                    """caso: check Serie Storica = True --> Caricamento vector caso d'uso serie storica"""
                    if len(pgisList) > 1 and len(pgisList) <= 8:
                        abilitati = self.dlg.indica_getAbilitati()
                        tcon = [t for t in pgisList if (t.host is not None and t.host != '')]
                        #tcon = [t for t in pgisList if (t.host != '' and t.seriestorica != '')]
                        periodi_selezionati = ''
                        for info in tcon:
                            s = info.nome
                            periodicita = info.periodicita

                            if (periodicita == "Annuale"):
                                s = s.replace('Anno ', '')
                            elif (periodicita == "Semestrale"):
                                s = s.replace(' Semestre ', '_')
                            elif (periodicita == "Quadrimestrale"):
                                s = s.replace(' Quadrimestre ', '_')
                            elif (periodicita == "Trimestrale"):
                                s = s.replace(' Trimestre ', '_')
                            elif (periodicita == "Mensile"):
                                s = s.replace(' Mese ', '_')
                            elif (periodicita == "Settimanale"):
                                s = s.replace(' Settimana ', '_')
                            else:
                                LOGGER.debug('slot_carica_selezionati: periodicita non prevista: %s' % (periodicita))

                            periodi_selezionati = ''.join([periodi_selezionati, ' ', s])
                        periodi_selezionati = periodi_selezionati.strip()
                        # reverse della lista non necessaria
                        #tcon.reverse()

                        paragoneseriestorica = ''
                        firstloop = True
                        tobecontinued = True
                        i = 0
                        for info in tcon:
                            i = i + 1
                            #LOGGER.debug('slot_carica_selezionati: [%d] | %s | %s | %s | %s | %s | %s | %s ' % (i, info.category, info.unita, info.periodicita, info.seriestorica, info.nome, info.nome_indicatore, info.desc_dimensione))
                            LOGGER.debug('slot_carica_selezionati: [%d] | %s | %s ' % (i, info.seriestorica, info.nome))
                            if firstloop:
                                if (info.seriestorica == ''):
                                    QMessageBox.information(None, "Serie Storica", "Dato di serie storica non presente su almeno un ramo selezionato:\n%s" % (info.nome))
                                    tobecontinued = False
                                    break
                                paragoneseriestorica = info.seriestorica
                                LOGGER.debug('slot_carica_selezionati paragoneseriestorica: %s' % (paragoneseriestorica))
                                firstloop = False
                            else:
                                if (info.seriestorica == ''):
                                    QMessageBox.information(None, "Serie Storica", "Dato di serie storica non presente su almeno un ramo selezionato:\n%s" % (info.nome))
                                    tobecontinued = False
                                    break
                                if info.seriestorica != paragoneseriestorica:
                                    LOGGER.debug('info.seriestorica != paragoneseriestorica')
                                    msg = "Selezionare almeno 2 dati omogenei per una analisi di serie storica!"
                                    msg = msg + "%s" % ("\n\nVerificare che non siano selezionati nodi da precedenti ricerche")
                                    QMessageBox.information(None, "Serie Storica", msg)
                                    tobecontinued = False
                                    break
                        pass

                        if tobecontinued:
#                             periodi_selezionati = ''
#                             for info in tcon:
#                                 s = info.nome
#                                 periodi_selezionati = ''.join([periodi_selezionati, ' ', s])
                            grouptag = "#"
                            for info in tcon:
                                groupLayerName = '%s %s %s - %s' % (grouptag, info.nome_indicatore, info.desc_dimensione, periodi_selezionati)
                                tocLayerName = info.unita
                                """
                                ...
                                nome: "Anno 2011",
                                ...
                                unita_territoriale: "Comunale",
                                periodicita: "Annuale",
                                des_unita_misura: "mcg/m3",
                                ideal_point: "40",
                                nome_indicatore: "Modellistica qualita' dell'aria - NO2",
                                desc_dimensione: "Media Annua"
                                """
                                propertySerieStorica = {}
                                propertySerieStorica['dimensione'] = info.desc_dimensione
                                propertySerieStorica['idealpoint'] = info.ideal_point
                                propertySerieStorica['indicatore'] = info.nome_indicatore
                                propertySerieStorica['periodi'] = periodi_selezionati
                                propertySerieStorica['periodicita'] = info.periodicita
                                propertySerieStorica['unita'] = info.unita
                                propertySerieStorica['unitamisura'] = info.des_unita_misura
                                LOGGER.debug('slot_carica_selezionati: propertySerieStorica = %s' % (str(propertySerieStorica)))

                                info.loadVectorLayerSerieStorica(self.iface,
                                                                 self.dlg.getServiceReadQmlUrl(),
                                                                 abilitati,
                                                                 loadQML=False,
                                                                 groupLayerName=groupLayerName,
                                                                 tocLayerName=tocLayerName,
                                                                 propertySerieStorica=propertySerieStorica)
                                break
                            pass
                            # se non è presente in toc/legend , occorre caricare il gruppo "Serie Storica Grafici" in posizione 0
                            groupindex = ChartMapToolIdentify.getGroupIndexSerieStoricaGrafici(self.iface)
                            if (groupindex < 0):
                                LOGGER.debug('slot_carica_selezionati: non trova gruppo per i grafici serie storica (%d)' % (groupindex))
                                pass

                            #QMessageBox.information(None, "Serie Storica", "DEBUG: caricato vector serie storica")

#                             # carica lista checkbox selezionati
#                             # la lista al termine conterra' seguenti valori
#                             # periodi = ['anno_2009', 'anno_2010', 'anno_2011]
#                             periodi = []
#                             for info in tcon:
#                                 s = info.nome
#                                 periodi.append(s.replace(' ', '_'))
#
#                             # passa i periodi al tool di chart
#                             LOGGER.debug('passa i periodi a toolChartInfo: %s' % (periodi))
#                             self.toolChartInfo.setPeriodi(periodi)
#
#                             # attiva il tool di chart
#                             #self.canvas.setMapTool(self.toolChartInfo)

                    elif len(pgisList) > 8:
                        QMessageBox.information(None, "Serie Storica", "Selezionare al massimo 8 periodi!")
                    else:
                        QMessageBox.information(None, "Serie Storica", "Seleziona almeno 2 periodi per costruire una serie storica")
                else:
                    """caso: check Serie Storica = False --> Caricamento vector caso d'uso default"""
                    if len(pgisList) > 0:
                        abilitati = self.dlg.indica_getAbilitati()
                        tcon = [t for t in pgisList if t.host != '']
                        tcon.reverse()
                        for info in tcon:
                            info.loadVectorLayer(self.iface, self.dlg.getServiceReadQmlUrl(), abilitati, True)

            elif self.dlg.ui.tabWidget.currentWidget() == self.dlg.ui.tabRaster:
                rasterList = self.dlg.gestoreRASTER.treeWidgetGetSelectedList()
                if len(rasterList) > 0:
                    abilitati = self.dlg.raster_getAbilitati()
                    tcon = [t for t in rasterList if t.host != '']
                    tcon.reverse()
                    for info in tcon:
                        info.loadRasterLayer(self.iface, self.dlg.getServiceReadQmlUrl(), abilitati, True)

            else:
                pass
            # -----------------------------------------
            # jiraprod.csi.it:8083/browse/CSIATLANTE-8
            #self.dlg.deselectAllButIndica()
            # -----------------------------------------
            self.dlg.deselectAll()
        finally:
            csiutils.Cursor.Restore()
            self.iface.mapCanvas().refresh()

    def slot_svuota_toc(self):
        """
        Svuota completamente la TOC, chiede prima conferma,
        implementato per ora solo nel tab Indica
        """
        reply = QMessageBox.question(None, 'Ripulisci dati in TOC', "Saranno cancellati tutti i dati finora caricati in TOC. \n\nSei sicuro di proseguire?", QMessageBox.Yes, QMessageBox.No)
        if reply == QMessageBox.Yes:
            root = QgsProject.instance().layerTreeRoot()
            root.removeAllChildren()
        else:
            pass

    def addWMSLayer(self, wmsselection, crs, newLayersAsGroup, outputformat, abilita, usadesc, stampabile):
        """
        Aggiunge in QGIS la porzione di WMS selezionata confezionando l'uri secondo i parametri passati

        @param wmsselection : lista di tipo WMSSelection contenente oggetti WMSlayers
        @param crs : crs
        @param newLayersAsGroup: True/False indica se caricare il layer raggruppato in un grouplayer
        @param outputformat: formato immagine di output es: image/jpeg image/png ecc...
        @param abilita: True/False se abilitato in toc
        @param usadesc: True/False se usare la descrizione del tag <Title>
        @param stampabile: True/False se usare la modalita' per stampa impostando un size per i tiles
        """
        layers, styles, titles = wmsselection.getLayerStyleTitlesLists()  # @UnusedVariable
        if len(layers) == 0:
            return

        info = WMSInfo.getInfoFromList(self.wmsInfoList, wmsselection.tree)
        url = info.wmsURL

        legend = self.iface.legendInterface()

        if usadesc:
            layerDesc = titles
        else:
            layerDesc = layers

        # limite di elementi per GetFeatureInfo
        # TODO: per ogni WMS sarebbe informazione da settare su configurazione oppure da plugin insieme agli altri settaggi nel tab
        s = QSettings()
        featurecountlimit = s.value("/CSIAtlante/wms/featureCount", "10", type=unicode)

        # valori di default per tile size, usati in caso di wms stampabile
        tileMaxHeight = s.value("/CSIAtlante/wms/maxHeight", "256", type=unicode)
        tileMaxWidth = s.value("/CSIAtlante/wms/maxWidth", "256", type=unicode)

        legend.blockSignals(True)

        csiutils.Cursor.Hourglass()

        try:
            if newLayersAsGroup:
                # --------------------------------------------
                # CASO A:
                # Caricare layers come gruppo nella toc
                # --------------------------------------------
                groupindex = legend.addGroup(wmsselection.tree.name)
                legend.setGroupVisible(groupindex, abilita)

                layerDesc.reverse()
                layers.reverse()
                for i in range(len(layers)):
                    # uri = "crs=" + crs + "&featureCount=" + featurecountlimit + "&format=" + outputformat + "&layers=" + layers[i] + "&styles=" + "&url=" + url

                    # NB
                    # il name per ciascun layer deve esistere nella GetCapabilities altrimenti non puo' fare request GetMap
                    # rif:
                    #     OpenGIS Web Map Service (WMS) Implementation Specification
                    #     http://www.opengeospatial.org/standards/wms
                    if layers[i] != u'<has_no_Name>':
                        params = {
                                  'url': url,
                                  'crs': crs,
                                  'featureCount': featurecountlimit,
                                  'format': outputformat,
                                  'layers': layers[i],
                                  'styles': ''
                        }
                        if stampabile:
                            params.update({'maxHeight': tileMaxHeight})
                            params.update({'maxWidth': tileMaxWidth})

                        utf8params = csiutils.getEncodedDictionary(params)
                        urlWithParams = urllib.unquote_plus(urllib.urlencode(utf8params))
                        rlayer = self.iface.addRasterLayer(urlWithParams, layerDesc[i], "wms")
                        if not abilita:
                            legend.setLayerVisible(rlayer, False)
                        legend.moveLayer(rlayer, groupindex)
            else:
                # --------------------------------------------
                # CASO B:
                # Caricare i layers in modo singolo nella toc
                # --------------------------------------------
                if (wmsselection.layers[0].parentLayer is None):
                    # --------------------------------------------
                    # CASO B1:
                    # Carica solo il nodo padre
                    # --------------------------------------------
                    i = 0
                    if layers[i] != u'<has_no_Name>':
                        # --------------------------------------------
                        # CASO B11:
                        # Carica solo il nodo padre
                        # --------------------------------------------
                        params = {
                                  'url': url,
                                  'crs': crs,
                                  'featureCount': featurecountlimit,
                                  'format': outputformat,
                                  'layers': layers[i],
                                  'styles': ''
                        }
                        if stampabile:
                            params.update({'maxHeight': tileMaxHeight})
                            params.update({'maxWidth': tileMaxWidth})

                        utf8params = csiutils.getEncodedDictionary(params)
                        urlWithParams = urllib.unquote_plus(urllib.urlencode(utf8params))
                        rlayer = self.iface.addRasterLayer(urlWithParams, layerDesc[i], "wms")
                        if not abilita:
                            legend.setLayerVisible(rlayer, False)
                    else:
                        # --------------------------------------------
                        # CASO B12:
                        # Carica raggruppati in toc in modo forzato per simulare unico caricamento
                        # quando il nodo padre non ha il tag name nella GetCapabilities ...
                        # caso ARPA
                        # --------------------------------------------

                        groupindex = legend.addGroup(wmsselection.tree.name)
                        legend.setGroupVisible(groupindex, abilita)

                        layerDesc.reverse()
                        layers.reverse()
                        for i in range(len(layers)):
                            # uri = "crs=" + crs + "&featureCount=" + featurecountlimit + "&format=" + outputformat + "&layers=" + layers[i] + "&styles=" + "&url=" + url

                            # NB
                            # il name per ciascun layer deve esistere nella GetCapabilities altrimenti non puo' fare request GetMap
                            # rif:
                            #     OpenGIS Web Map Service (WMS) Implementation Specification
                            #     http://www.opengeospatial.org/standards/wms
                            if layers[i] != u'<has_no_Name>':
                                params = {
                                          'url': url,
                                          'crs': crs,
                                          'featureCount': featurecountlimit,
                                          'format': outputformat,
                                          'layers': layers[i],
                                          'styles': ''
                                }
                                if stampabile:
                                    params.update({'maxHeight': tileMaxHeight})
                                    params.update({'maxWidth': tileMaxWidth})

                                utf8params = csiutils.getEncodedDictionary(params)
                                urlWithParams = urllib.unquote_plus(urllib.urlencode(utf8params))
                                rlayer = self.iface.addRasterLayer(urlWithParams, layerDesc[i], "wms")
                                if not abilita:
                                    legend.setLayerVisible(rlayer, False)
                                legend.moveLayer(rlayer, groupindex)

                else:
                    # --------------------------------------------
                    # CASO B2:
                    # Carica i singoli nodi dell'elenco
                    # --------------------------------------------
                    layerDesc.reverse()
                    layers.reverse()
                    for i in range(len(layers)):
                        # NB
                        # il name per ciascun layer deve esistere nella GetCapabilities altrimenti non puo' fare request GetMap
                        # rif:
                        #     OpenGIS Web Map Service (WMS) Implementation Specification
                        #     http://www.opengeospatial.org/standards/wms
                        if layers[i] != u'<has_no_Name>':
                            params = {
                                      'url': url,
                                      'crs': crs,
                                      'featureCount': featurecountlimit,
                                      'format': outputformat,
                                      'layers': layers[i],
                                      'styles': ''
                            }
                            if stampabile:
                                params.update({'maxHeight': tileMaxHeight})
                                params.update({'maxWidth': tileMaxWidth})

                            utf8params = csiutils.getEncodedDictionary(params)
                            urlWithParams = urllib.unquote_plus(urllib.urlencode(utf8params))
                            rlayer = self.iface.addRasterLayer(urlWithParams, layerDesc[i], "wms")
                            if not abilita:
                                legend.setLayerVisible(rlayer, False)

        finally:
            legend.blockSignals(False)
            csiutils.Cursor.Restore()


class AsynchronousHTTPHandler(urllib2.HTTPHandler):
    """
    Asynchronous HTTP Handler in urllib2
    """
    def http_response(self, req, response):
        print "url: %s" % (response.geturl(),)
        print "info: %s" % (response.info(),)
        for l in response:
            print l
        return response


class LoaderThread(threading.Thread):
    """
    Classe per gestire il caricamento di un file qgs o porzioni di qgs nel progetto corrente
    """
    def __init__(self, iface, filename):
        self.filename = filename
        self.iface = iface

    def run(self):
        csiutils.Cursor.Hourglass()
        time.sleep(3)
        csiutils.Cursor.Restore()
        self.iface.addProject(self.filename)


class PROJECTInfo:
    """
    Classe di gestione del dato progetto
    """
    def __init__(self):
        self.category = ''
        self.id = ''
        self.idtree = ''
        self.idpadre = ''
        self.nome = ''

    @classmethod
    def readFromJson(self, jsonObj):
        """
        Ricava dal json le informazioni dell'attributo 'progetto'
        Alimenta una lista in cui ciascun elemento e' uno struct/dto PROJECTInfo
        Da questo carica un tree.

        @param jsonObj: jsonObj
        @return: tree
        """
        olines = []

        try:
            for ln in jsonObj['progetto']:
                w = PROJECTInfo()
                w.category = ln['categoria']
                w.id = str(ln['idAlbProgetto'])
                w.idtree = str(ln['idtree'])
                w.idpadre = str(ln['idpadre'])
                w.nome = ln['nome']
                olines.append(w)
        except Exception, ex:
            QgsMessageLog.logMessage("errore caricamento json: " + str(ex), 'CSI Atlante')  # @_enzo_UndefinedVariable
            return []

        tree = PROJECTInfo.loadTree(olines)
        return tree

    def setChildren(self, infolist):
        """
        setChildren
        @param infolist : lista di elementi
        """
        self.children = [t  for t in infolist if t.idpadre == self.idtree]
        if len(self.children) > 0:
            for t in self.children:
                t.setChildren(infolist)
        else:
            self.children = None

    @classmethod
    def loadTree(cl, infolist):
        """
        Carica gli elementi passati come lista e li restituisce in un tree

        @param infolist : lista di elementi
        @return: l0 : tree
        """
        for el in infolist:
            if el.idpadre == el.idtree:
                el.idpadre = ''
            else:
                l0 = [t  for t in infolist if t.idtree == el.idpadre]
                if len(l0) == 0:
                    el.idpadre = ''
        l0 = [t  for t in infolist if t.idpadre == '']
        for t in l0:
            t.setChildren(infolist)
        return l0

    def LoadProject(self, iface, url, usr, pwd):
        """
        Metodo che carica sul client desktop un progetto ricavando il QGS tramite web service

        @param iface : interfaccia qgis
        @param url: url del servizio di lettura di un progetto qgs
        @param usr: utente per richiamare il servizio
        @param pwd: password per richiamare il servizio
        """
        csiutils.Cursor.Hourglass()
        try:
            query_args = {'id': self.id, 'usr': usr, 'pwd': pwd}
            encoded_args = urllib.urlencode(query_args)
            filehandle = urllib2.urlopen(url, encoded_args)

            lines = csiutils.RemoveCR(filehandle.readlines())
            filehandle.close()

            tx = '\n'.join(lines)
            tx = csiutils.escapeLeftRightDirectionSymbol(tx)

            fw = tempfile.NamedTemporaryFile(suffix='.qgs', delete=False)
            userFilePath = fw.name
            # fw = open(userFilePath,"wb")
            fw.write(tx)
            fw.flush()
            fw.close()

            self.loader = LoaderThread(iface, userFilePath)
            self.loader.run()
        except:
            raise
        finally:
            #legend.blockSignals(False)
            csiutils.Cursor.Restore()


class POSTGISInfo(object):
    """
    Classe di gestione del dato postgis
    """
    # def __init__(self, iface):
    def __init__(self):
        self.category = ''
        self.category_backup = ''
        self.id = ''
        self.idtree = ''
        self.idpadre = ''
        self.nome = ''
        self.nome_toc = ''
        self.host = ''
        self.porta = ''
        self.dbname = ''
        self.utente = ''
        self.schema = ''
        self.tavola = ''
        self.urlmetadati = ''
        self.scrittura = False
        self.whereclause = ''
        self.keycolumn = ''
        self.urllicenza = ''
        self.vl = None

    @classmethod
    def readFromJson(cls, jsonObj):
        """
        Ricava dal json le informazioni dell'attributo 'postgis'
        Alimenta una lista in cui ciascun elemento e' uno struct/dto POSTGISInfo
        Converte tutta la lista in un tree generico, che poi potrà essere filtrato per categoria

        @param jsonObj: jsonObj
        @return: tree
        """
        olines = []
        try:
            for ln in jsonObj['postgis']:
                w = POSTGISInfo()
                w.category = ln.get('categoria', '')
                w.category_backup = ln.get('categoria', '')
                w.id = str(ln['idAlbPostgis'])
                w.idtree = str(ln['idtree'])
                w.idpadre = str(ln['idpadre'])
                w.nome = ln['nome']
                w.nome_toc = ln['nome']
                w.host = ln['host']
                w.schema = ln['aschema']
                w.porta = str(ln['porta'])
                w.dbname = ln['dbname']
                w.tavola = ln['tavola']
                w.urlmetadati = ln.get('urlmetadati', '')
                w.scrittura = ln['scrittura'] == 'S'
                w.utente = ln['utente']
                w.whereclause = ln.get('clausola_where', '')
                w.keycolumn = ln.get('primary_key', '')
                w.urllicenza = ln.get('url_licenza', '')
                olines.append(w)
        except Exception, ex:
            QgsMessageLog.logMessage("errore caricamento json: " + str(ex), 'CSI Atlante')
            return []

        tree = POSTGISInfo.loadTree(olines)
        return tree

    def loadVectorLayer(self, iface, readQmlUrl, visible=False, loadQML=False):
        try:
            getattr(self, "geo_tavola")
        except AttributeError:
            # situazione base senza join : versione < 1.0.10
            vl = self.loadVectorLayerBase(iface, readQmlUrl, visible, loadQML)  # @UnusedVariable
        else:
            # situazione in caso la clausola try non sollevi un'eccezione
            if (self.geo_tavola == ''):
                vl = self.loadVectorLayerBase(iface, readQmlUrl, visible, loadQML)  # @UnusedVariable
            else:
                # @TODO: estendere con caso Join
                pass

    def loadVectorLayerBase(self, iface, readQmlUrl, visible=False, loadQML=False, postfixLegendName=''):
        """
        Metodo che crea e carica un nuovo vector layer come definito dall'elenco
        dei parametri di connessione associati.
        Cerca la password se e' presente nel portafoglio delle connessioni db,
        se non esiste permette di inserire una password per alimentare il portafoglio.
        Permette 3 tentativi per l'inserimento della password.

        @param iface: interfaccia qgis
        @param visible: boolean per caricare il layer gia' visibile (piu' lento)
        @param loadQML: boolean per caricare QML associato
        @param readQmlUrl: url del servizio per ottenere un qml
        @param postfixLegendName: stringa da postporre al nome in legenda
        @return: vl: puntatore al vectorlayer creato | None
        """
        vl = None
        if self.host == '':
            return

        legend = iface.legendInterface()

        pwdCoax = self.getPasswordCoax(self.host, self.porta, self.dbname, self.utente)
        if pwdCoax == None:
            QMessageBox.information(None, "Dato non caricato", "Dato non caricato:\n%s" % (self.nome))
        else:
            # caricamento del vector layer
            legend.blockSignals(True)
            vl = QgsVectorLayer()

            try:
                # made sure the crs prompt is disabled
                s = QSettings()
                oldValidation = s.value("/Projections/defaultBehaviour", "useGlobal", type=unicode)
                s.setValue("/Projections/defaultBehaviour", "useGlobal")
                """
                La connessione al DB deve avvenire con le credenziali di utente
                Il caricamento del vector layer avviene con le credenziali dello schema
                """
                uri = QgsDataSourceURI()
                uri.setConnection(self.host, self.porta, self.dbname, self.utente, pwdCoax)
                cn = CSIPostGisDBConnector(uri)

                vl = cn.getVectorLayer(self.schema, self.tavola, self.keycolumn, self.whereclause, ''.join([self.nome_toc, postfixLegendName]))
                if vl.isValid():
                    vl.setReadOnly(not self.scrittura)
                    # imposta il sistema di riferimento ricavato dal mapRenderer
                    # (disattivato)
                    # crs = iface.mapCanvas().mapRenderer().destinationCrs()
                    # vl.setCrs(crs)
                    QgsMapLayerRegistry.instance().addMapLayer(vl)

                    legend.setLayerVisible(vl, visible)
                    if loadQML:
                        self.loadQML(readQmlUrl, vl, self.id, self.category_backup)
                        pass

                    # se è il primo layer in legenda , fa lo zoom sull'extent 1.0.31
                    if (len(legend.layers()) == 1):
                        canvas = iface.mapCanvas()
                        canvas.setExtent(vl.extent())

            except Exception, ex:
                QMessageBox.information(None, "Errore", \
                    "loadVectorLayerBase:\nImpossibile caricare il vectorlayer %s\n\n%s" % (self.nome, str(ex)))

            finally:
                s.setValue("/Projections/defaultBehaviour", oldValidation)
                legend.blockSignals(False)
                legend.refreshLayerSymbology(vl)
                return vl

    def loadQML(self, url, layer, layer_id, layer_cat):
        """
        Metodo che carica il QML associato ad un layer_id prelevandolo tramite web service

        @param layer: layer
        @param layer_id: layer_id, id trasportato dal json univoco all'interno della stessa categoria
        @param layer_cat: categoria del layer per rendere univoca la ricerca della legenda qml
        """
        error = None
        userFilePath = ""
        class_name = self.__class__.__name__
        LOGGER.debug('loadQML class_name: %s' % (class_name))

        tab = 'vector'
#         if class_name == 'INDICAInfo':
#             tab = 'indica'

        ex = ""
        try:
            query_args = {'id': layer_id, 'cat': layer_cat, 'tab': tab}
            encoded_args = urllib.unquote_plus(urllib.urlencode(query_args))
            #encoded_args = urllib.urlencode(query_args)

            LOGGER.debug('loadQML encoded_args: %s' % (encoded_args))

            filehandle = urllib2.urlopen(url, encoded_args)

            lines = csiutils.RemoveCR(filehandle.readlines())
            filehandle.close()

            LOGGER.debug('loadQML len(lines): %s' % (str(len(lines))))

            if len(lines) > 0:
                tx = '\n'.join(lines)
                # LOGGER.debug('loadQML tx: %s' % (tx))

                tf = tempfile.NamedTemporaryFile(suffix='.qml', delete=False)
                userFilePath = tf.name
                # tf = open(userFilePath,"wb")
                tf.write(tx)
                tf.flush()
                tf.close()

                layer.loadNamedStyle(userFilePath)
        #except (IOError, OSError, ValueError), e:
        except Exception, ex:
            #raise
            error = "Errore caricamento qml: \ntab = %s%\nid = %s\ncategoria = %s\n\n %s" % tab, layer_id, layer_cat, ex
            QgsMessageLog.logMessage(error, 'CSI Atlante')
            LOGGER.error('loadQML %s' % (error))
        finally:
            if error is not None:
                pass

    @classmethod
    def testConnection(cls, host, port, dbname, usr, pwd):
        """
        Metodo di test di una connessione db

        @param host: host
        @param port: port
        @param dbname: dbname
        @param usr: usr
        @param pwd: pwd
        @return: boolean testconnection: True | False
        """
        result = False
        # usa postgis_utils
        uri = QgsDataSourceURI()
        uri.setConnection(host, port, dbname, usr, pwd)

        try:
            cn = CSIPostGisDBConnector(uri)
            if cn.connected():
                cn.close()
                result = True
        except:
            result = False

        return result

    @classmethod
    def loadTree(cl, infolist):
        """
        Carica gli elementi passati come lista e li restituisce in un tree

        @param infolist : lista di elementi
        @return: lzero : tree
        """
        # inizializza eventuale idpadre non esistente
        for el in infolist:
            l0 = [t  for t in infolist if t.idtree == el.idpadre and t.category == el.category]
            if len(l0) == 0:
                el.idpadre = ''

        l0 = [t  for t in infolist if t.idpadre == '']
        for t in l0:
            t.setChildren(infolist)

        # introduce una nuova categoria "*" "All Inclusive" unione di tutte le categorie
        s = QSettings()
        category_aux = s.value("CSIAtlante/conf/categoriaAll", u"*", type=unicode)

        infolist_aux = copy.deepcopy(infolist)
        #l0_aux = copy.deepcopy(l0)
        l0_aux = [t  for t in infolist_aux if t.idpadre == '']
        for t in l0_aux:
            t.setChildrenAux(infolist_aux, category_aux)
            t.category = category_aux

        lzero = []
        lzero.extend(l0_aux)
        lzero.extend(l0)
        #lzero = l0_aux + l0

        return lzero

    def setChildren(self, infolist):
        """
        setChildren
        @param infolist : lista di elementi
        """
        self.children = [t  for t in infolist if t.idpadre == self.idtree and t.category == self.category]
        if len(self.children) > 0:
            for t in self.children:
                t.setChildren(infolist)
        else:
            self.children = None

    def setChildrenAux(self, infolist, category_aux):
        """
        setChildrenAux
        @param infolist : lista di elementi
        @param category_aux : nome categoria addizionale
        """
        self.children = [t  for t in infolist if t.idpadre == self.idtree and t.category == self.category]
        if len(self.children) > 0:
            for t in self.children:
                t.setChildrenAux(infolist, category_aux)
                t.category = category_aux
        else:
            self.children = None

    @classmethod
    def getPassword(cls, host, port, database, username):
        """
        Cerca e restituisce una password dal portafoglio delle connessioni utente.
        Se non la trova restituisce None

        @param host: host
        @param port: port
        @param database: database
        @param username: username
        @return: pwd: password | None
        """
        # TODO: portfolio = csiAtlantePlugin.portfolio
        portfolio = ConnectionsPortfolio()
        pwd = portfolio.getPassword(host, port, database, username)
        return pwd

    @classmethod
    def getPasswordCoax(cls, host, port, database, username):
        """
        Cerca e restituisce una password dal portafoglio delle connessioni utente.
        Se non la trova permette di inserire una password per alimentare il portafoglio.
        Permette 3 tentativi per l'inserimento della password.

        @param host: host
        @param port: port
        @param database: database
        @param username: username
        @return: pwd: password | None
        """
        # TODO: portfolio = csiAtlantePlugin.portfolio
        portfolio = ConnectionsPortfolio()
        tentativi = 3
        pwd = None
        try:
            looptest = True
            while looptest:
                tentativi = tentativi - 1
                pwd = portfolio.getPassword(host, port, database, username)

                if pwd is None or not cls.testConnection(host, port, database, username, pwd):
                    QMessageBox.information(None, "Errore", "Errore di connessione DB dati:\n\ncontrollare i parametri e la password\n\nhost: %s\nport: %s\ndatabase: %s\nutente: %s" % (host, port, database, username))

                    dlgNew = NewConnectionDialog()
                    dlgNew.setWindowTitle("Nuova connessione db")
                    cname = dlgNew.formatConnectionName(username, host, port, database)
                    dlgNew.leName.setText(cname)
                    dlgNew.leHost.setText(host)
                    dlgNew.lePort.setText(port)
                    dlgNew.leDatabase.setText(database)
                    dlgNew.leUsername.setText(username)

                    if dlgNew.exec_() == QDialog.Accepted:
                        pwd = dlgNew.lePassword.text()
                        # QMessageBox.information(None, "Debug", "self.nome: %s \npassword: %s" % (self.nome, dlgNew.lePassword.text()))
                        if tentativi == 0:
                            looptest = False
                            QMessageBox.information(None, "Password non trovata o fornita", "Terminati tentativi!\n\nPassword non trovata o fornita:\n\nhost: %s\nport: %s\ndatabase: %s\nutente: %s" % (host, port, database, username))
                    else:
                        looptest = False
                        QMessageBox.information(None, "Password non trovata o fornita", "Password non trovata o fornita:\n\nhost: %s\nport: %s\ndatabase: %s\nutente: %s" % (host, port, database, username))

                else:
                    looptest = False

        except Exception, ex:
            QMessageBox.information(None, "Errore", "\n%s" % (str(ex)))

        finally:
            pass

        return pwd


class INDICAInfo(POSTGISInfo):
    """
    Classe di gestione del dato indicatori
    Estende la classe POSTGISInfo
    e reimplementa readFromJson e loadVectorLayer
    """
    def __init__(self):
        #POSTGISInfo.__init__(self)
        super(POSTGISInfo, self).__init__()
        self.unita = ''
        self.periodicita = ''
        self.ord_unita = ''
        self.ord_periodicita = ''
        self.comportamento_qml = 0
        self.seriestorica = ''
#         self.geo_tavola = ''
#         self.geo_utente = ''
#         self.geo_schema = ''
#         self.geo_keycolumn = ''
#         self.geo_field = ''
#         self.tavola_field = ''
        self.des_unita_misura = ''
        self.ideal_point = '0'
        self.nome_indicatore = ''
        self.desc_dimensione = ''

        def __iter__(self):
            return self

    @classmethod
    def readFromJson(cls, jsonObj):
        """
        Ricava dal json le informazioni dell'attributo 'indica'
        Alimenta una lista in cui ciascun elemento e' un dto INDICAInfo
        Converte tutta la lista in un tree generico, che poi potrà essere filtrato per categoria

        @param jsonObj: jsonObj
        @return: tree
        """
        olines = []
        try:
            for ln in jsonObj['indica']:
                w = INDICAInfo()
                w.category = ln.get('categoria', '')
                w.category_backup = ln.get('categoria', '')
                w.id = str(ln.get('idAlbIndicatori', ''))
                w.idtree = str(ln.get('idtree', ''))
                w.idpadre = str(ln.get('idpadre', ''))
                w.nome = ln.get('nome', '')
                w.nome_toc = ln.get('nome', '')
                w.host = ln.get('host', '')
                w.schema = ln.get('aschema', '')
                w.porta = str(ln.get('porta', ''))
                w.dbname = ln.get('dbname', '')
                w.tavola = ln.get('tavola', '')
                w.urlmetadati = ln.get('urlmetadati', '')
                w.scrittura = ln['scrittura'] == 'S'
                w.utente = ln.get('utente', '')
                w.whereclause = ln.get('clausola_where', '')
                w.keycolumn = ln.get('primary_key', '')
                w.urllicenza = ln.get('url_licenza', '')
#                 w.geo_tavola = ln.get('geo_tavola', '')
#                 w.geo_utente = ln.get('geo_utente', '')
#                 w.geo_schema = ln.get('geo_aschema', '')
#                 w.geo_keycolumn = ln.get('geo_primary_key', '')
#                 w.geo_field = ln.get('geo_field', '')
#                 w.tavola_field = ln.get('tavola_field', '')
                w.unita = ln.get('unita_territoriale', '')
                w.periodicita = ln.get('periodicita', '')
                w.ord_unita = ln.get('ord_ris_spaz', '')
                w.ord_periodicita = ln.get('ord_ris_temp', '')
                w.seriestorica = ln.get('nome_vista_serie_storica', '')
                w.comportamento_qml = 0 if ln.get('comportamento_qml', 0) == '' else int(ln.get('comportamento_qml', 0))
                w.des_unita_misura = ln.get('des_unita_misura', '')
#                 w.ideal_point = 0 if ln.get('ideal_point', 0) == '' else int(ln.get('ideal_point', 0))
                w.ideal_point = '0' if ln.get('ideal_point', '0') == '' else ln.get('ideal_point', '0')
                w.nome_indicatore = ln.get('nome_indicatore', '')
                w.desc_dimensione = ln.get('desc_dimensione', '')

                #LOGGER.debug('INDICAInfo.readFromJson - %s %s %s %s %s %s %s %s %s' % (w.id, w.idpadre, w.category, w.unita, w.periodicita, w.des_unita_misura, w.ideal_point, w.nome_indicatore, w.desc_dimensione))
                olines.append(w)
        except Exception, ex:
            QgsMessageLog.logMessage("errore caricamento json: " + str(ex), 'CSI Atlante')
            return []

        tree = INDICAInfo.loadTree(olines)
        return tree

    @classmethod
    def loadTree(cl, infolist):
        """
        Carica in un tree gli elementi passati come lista
        Il tree e' costruito ricorsivamente in base alle relazioni padre-figlio accorpate per categoria.

        @param infolist : lista di elementi
        @return: lzero : lista tree
        """
        # inizializza eventuale idpadre non esistente
        for el in infolist:
            l0 = [t  for t in infolist if t.idtree == el.idpadre and t.category == el.category]
            if len(l0) == 0:
                el.idpadre = ''

        l0 = [t  for t in infolist if t.idpadre == '']
        for t in l0:
            # nooooooooo t.nome_toc = t.nome + ':'
            t.setChildren(infolist)

        # introduce una nuova categoria "*" "All Inclusive" unione di tutte le categorie
        s = QSettings()
        category_aux = s.value("CSIAtlante/conf/categoriaAll", u"*", type=unicode)

        infolist_aux = copy.deepcopy(infolist)
        #l0_aux = copy.deepcopy(l0)
        l0_aux = [t  for t in infolist_aux if t.idpadre == '']
        for t in l0_aux:
            t.setChildrenAux(infolist_aux, category_aux)
            t.category = category_aux

        lzero = []
        lzero.extend(l0_aux)
        lzero.extend(l0)

        return lzero

    def setChildren(self, infolist):
        """
        setChildren
        @param infolist : lista di elementi
        """
        self.children = [t  for t in infolist if t.idpadre == self.idtree and t.category == self.category]
        if len(self.children) > 0:
            for t in self.children:
                t.nome_toc = self.nome_toc + ' - ' + t.nome
                t.setChildren(infolist)
        else:
            self.children = None

    def setChildrenAux(self, infolist, category_aux):
        """
        setChildrenAux
        @param infolist : lista di elementi
        @param category_aux : nome categoria addizionale artificiale
        """
        self.children = [t  for t in infolist if t.idpadre == self.idtree and t.category == self.category]
        if len(self.children) > 0:
            for t in self.children:
                t.setChildrenAux(infolist, category_aux)
                t.category = category_aux
        else:
            self.children = None

    def loadVectorLayer(self, iface, readQmlUrl, visible=False, loadQML=False):
        """ INDICAInfo reimplementato  """
        try:
            getattr(self, "geo_tavola")
        except AttributeError:
            # situazione base senza join : versione < 1.0.10
            vl = self.loadVectorLayerBase(iface, readQmlUrl, visible, loadQML)  # @UnusedVariable
        else:
            # situazione in caso la clausola try non sollevi un'eccezione
            if (self.geo_tavola == ''):
                vl = self.loadVectorLayerBase(iface, readQmlUrl, visible, loadQML)  # @UnusedVariable
            else:
                # @TODO: estendere con caso Join
                vlTABELLA = self.loadVectorLayerBase(iface, readQmlUrl, visible, loadQML, '_Tabella')
                vlGEOMETRIA = self.loadVectorLayerGeom(iface, readQmlUrl, visible, loadQML)
                if (vlTABELLA is not None and vlGEOMETRIA is not None):
                    joinInfo = QgsVectorJoinInfo()
                    joinInfo.joinLayerId = vlTABELLA.id()  # okkio !!!
                    joinInfo.joinFieldName = self.tavola_field
                    joinInfo.targetFieldName = self.geo_field
                    #joinInfo.setJoinFieldNamesSubset(['valore','anno'])
                    joinInfo.memoryCache = True
                    # joinInfo.prefix = "custom-prefix_"
                    joinOperator = vlGEOMETRIA.addJoin(joinInfo)
                    if (joinOperator):
                        QMessageBox.information(None, "Errore Join", "Problema con Join tra vectorlayers per %s \n\n%s\n%s" % (self.nome, vlGEOMETRIA.id(), vlTABELLA.id()))
        finally:
            pass

    def loadVectorLayerSerieStorica(self, iface, readQmlUrl, visible=False, loadQML=False, groupLayerName='Serie Storica', tocLayerName='Layer', propertySerieStorica={}):
        """
        Carica il vector layer di una serie storica
        Metodo principale in cui gestisce il caricamento in legenda e il grouplayer in cui caricare

        @TODO:
        rivedere la gestione dei gruppi usando Layer Tree API
        http://www.lutraconsulting.co.uk/blog/2014/07/06/qgis-layer-tree-api-part-1/
        http://www.lutraconsulting.co.uk/blog/2014/07/25/qgis-layer-tree-api-part-2/
        http://gis.stackexchange.com/questions/26257/how-can-i-iterate-over-map-layers-in-qgis-python
        """
        legend = iface.legendInterface()
        groupname = groupLayerName
        groups = legend.groups()

        root = QgsProject.instance().layerTreeRoot()

        # 20150429 rimuove eventuali gruppi taggati per serie storica
        grouptag = "#"
        groups_toremove = []
        for i in range(0, len(groups)):
            g = groups[i]
            if g[:1] == grouptag:
#                 groupindex = groups.index(g)
#                 legend.removeGroup(groupindex)
                groups_toremove.append(g)

        for i in range(0, len(groups_toremove)):
            g = groups_toremove[i]
            node_group = root.findGroup(g)
            root.removeChildNode(node_group)

        # old API ... TODO: QgsLayerTreeGroup
        groups = legend.groups()
        if groupname in groups:
            #legend.removeGroup(groups.index(groupname))
            groupindex = groups.index(groupname)
        else:
            groupindex = legend.addGroup(groupname, expand=True, parent=None)
            legend.setGroupVisible(groupindex, visible)

        layertreegroup = root.findGroup(groupname)

        idlayers = layertreegroup.findLayerIds()
        for idlayer in idlayers:
            # se il nome è contenuto nell'id
            if idlayer.find(tocLayerName) > -1:
                # rimuovere il layer
                QgsMapLayerRegistry.instance().removeMapLayer(idlayer)

        vl = self.loadVectorLayerSerieStoricaBase(iface, readQmlUrl, visible, loadQML, '', tocLayerName, propertySerieStorica)

        if (vl is not None):
            LOGGER.debug('loadVectorLayerSerieStorica: vl is not None')
            legend.setLayerVisible(vl, visible)
            legend.moveLayer(vl, groupindex)
        else:
            LOGGER.error('loadVectorLayerSerieStorica: vl is None')
            QMessageBox.information(None, "Errore loadVectorLayerSerieStorica", "Problema con Carica il vector layer di una serie storica \n%s" % (self.nome))

        # TODO:
        pass

    def loadVectorLayerSerieStoricaBase(self, iface, readQmlUrl, visible=False, loadQML=False, postfixLegendName='', tocLayerName='', propertySerieStorica={}):
        """
        Carica il vector layer di una serie storica:
        In sostanza riprende il metodo POSTGISInfo.loadVectorLayerBase
        cambiando la vista geometrica da caricare e la modalita' di caricamentento,
        la vista geometrica da INDICAInfo.seriestorica invece che da INDICAInfo.tavola

        @param iface: interfaccia qgis
        @param visible: boolean per caricare il layer gia' visibile (piu' lento)
        @param loadQML: boolean per caricare QML associato
        @param readQmlUrl: url del servizio per ottenere un qml
        @param postfixLegendName: stringa da postporre al nome in legenda
        @return: vl: puntatore al vectorlayer creato | None
        """
        vl = None
        if self.host == '':
            return

        legend = iface.legendInterface()

        pwdCoax = self.getPasswordCoax(self.host, self.porta, self.dbname, self.utente)
        if pwdCoax == None:
            QMessageBox.information(None, "Dato non caricato", "Dato non caricato:\n%s" % (self.nome))
        else:
            # caricamento del vector layer
            legend.blockSignals(True)
            vl = QgsVectorLayer()

            try:
                # made sure the crs prompt is disabled
                s = QSettings()
                oldValidation = s.value("/Projections/defaultBehaviour", "useGlobal", type=unicode)
                s.setValue("/Projections/defaultBehaviour", "useGlobal")
                """
                La connessione al DB deve avvenire con le credenziali di utente
                Il caricamento del vector layer avviene con le credenziali dello schema
                """
                uri = QgsDataSourceURI()
                uri.setConnection(self.host, self.porta, self.dbname, self.utente, pwdCoax)
                cn = CSIPostGisDBConnector(uri)

                # vl = cn.getVectorLayer(self.schema, self.tavola, self.keycolumn, self.whereclause, ''.join([self.nome_toc, postfixLegendName]))
                #toc_name = ''.join([self.category_backup, '_', self.unita, '_', self.periodicita, postfixLegendName])  # 5_Rifiuti_Comunale_Annuale'

                toc_name = tocLayerName
                vl = cn.getVectorLayer(self.schema, self.seriestorica, 'identificativo_spaziale', '', toc_name)
                #LOGGER.debug('loadVectorLayerSerieStoricaBase: schema=%s | seriestorica=%s | keycolumn=%s | nometoc=%s' % (self.schema, self.seriestorica, self.keycolumn, '""'.join([self.nome, postfixLegendName])))
                LOGGER.debug('loadVectorLayerSerieStoricaBase: schema=%s | seriestorica=%s | keycolumn=%s | nometoc=%s' % (self.schema, self.seriestorica, self.keycolumn, toc_name))
                if vl.isValid():
                    vl.setReadOnly(not self.scrittura)
                    # imposta il sistema di riferimento ricavato dal mapRenderer
                    # (disattivato)
                    # crs = iface.mapCanvas().mapRenderer().destinationCrs()
                    # vl.setCrs(crs)
                    vl.setCustomProperty("sga/serie_storica", "true")
                    vl.setCustomProperty("sga/dimensione", propertySerieStorica['dimensione'])
                    vl.setCustomProperty("sga/idealpoint", propertySerieStorica['idealpoint'])
                    vl.setCustomProperty("sga/indicatore", propertySerieStorica['indicatore'])
                    vl.setCustomProperty("sga/periodi", propertySerieStorica['periodi'])
                    vl.setCustomProperty("sga/periodicita", propertySerieStorica['periodicita'])
                    vl.setCustomProperty("sga/unita", propertySerieStorica['unita'])
                    vl.setCustomProperty("sga/unitamisura", propertySerieStorica['unitamisura'])

                    QgsMapLayerRegistry.instance().addMapLayer(vl)
                    LOGGER.debug('loadVectorLayerSerieStoricaBase: addMapLayer(vl)')

                    legend.setLayerVisible(vl, visible)
                    if loadQML:
                        self.loadQML(readQmlUrl, vl, self.id, self.category_backup)
                    else:
                        self.loadDefaultQML(vl)

            except Exception, ex:
                LOGGER.error('loadVectorLayerSerieStoricaBase: Errore forse con vectorlayer %s\n%s' % ('""'.join([self.nome]), str(ex)))
                QMessageBox.information(None, "Errore", \
                    "loadVectorLayerSerieStoricaBase:\nErrore forse con vectorlayer %s\nerrore:\n%s" % ('""'.join([self.nome]), str(ex)))

            finally:
                s.setValue("/Projections/defaultBehaviour", oldValidation)
                legend.blockSignals(False)
                legend.refreshLayerSymbology(vl)
                return vl

    def loadVectorLayerGeom(self, iface, readQmlUrl, visible=False, loadQML=False, postfixLegendName=''):
        """
        Metodo che crea e carica un nuovo vector layer come definito dall'elenco
        dei parametri di connessione associati.
        Cerca la password se e' presente nel portafoglio delle connessioni db,
        se non esiste permette di inserire una password per alimentare il portafoglio.
        Permette 3 tentativi per l'inserimento della password.

        @param iface: interfaccia qgis
        @param visible: boolean per caricare il layer gia' visibile (piu' lento)
        @param loadQML: boolean per caricare QML associato
        @param readQmlUrl: url del servizio per ottenere un qml
        @param postfixLegendName: stringa da postporre al nome in legenda
        @return: vl: puntatore al vectorlayer creato | None
        """
        vl = None
        if self.host == '':
            return

        legend = iface.legendInterface()

        pwdCoax = self.getPasswordCoax(self.host, self.porta, self.dbname, self.geo_utente)
        if pwdCoax == None:
            QMessageBox.information(None, "Dato non caricato", "Dato non caricato:\n%s" % (self.nome))
        else:
            # caricamento del vector layer
            legend.blockSignals(True)
            vl = QgsVectorLayer()

            try:
                # made sure the crs prompt is disabled
                s = QSettings()
                oldValidation = s.value("/Projections/defaultBehaviour", "useGlobal", type=unicode)
                s.setValue("/Projections/defaultBehaviour", "useGlobal")
                """
                La connessione al DB deve avvenire con le credenziali di utente
                Il caricamento del vector layer avviene con le credenziali dello schema
                """
                uri = QgsDataSourceURI()
                uri.setConnection(self.host, self.porta, self.dbname, self.geo_utente, pwdCoax)
                cn = CSIPostGisDBConnector(uri)

                #vl = cn.getVectorLayer(self.geo_schema, self.geo_tavola, self.geo_keycolumn, self.geo_whereclause, ''.join([self.nome, postfixLegendName]))
                vl = cn.getVectorLayer(self.geo_schema, self.geo_tavola, self.geo_keycolumn, '', ''.join([self.nome, postfixLegendName]))
                if vl.isValid():
                    vl.setReadOnly(not self.scrittura)
                    # imposta il sistema di riferimento ricavato dal mapRenderer
                    # (disattivato)
                    # crs = iface.mapCanvas().mapRenderer().destinationCrs()
                    # vl.setCrs(crs)
                    QgsMapLayerRegistry.instance().addMapLayer(vl)

                    legend.setLayerVisible(vl, visible)
                    if loadQML:
                        self.loadQML(readQmlUrl, vl, self.id, self.category_backup)
                        pass

            except Exception, ex:
                QMessageBox.information(None, "Errore", \
                    "loadVectorLayerGeom:\nImpossibile caricare il vectorlayer %s\n\n%s" % (self.nome, str(ex)))

            finally:
                s.setValue("/Projections/defaultBehaviour", oldValidation)
                legend.blockSignals(False)
                legend.refreshLayerSymbology(vl)
                return vl

    def loadQML(self, url, layer, layer_id, layer_cat):
        """
        Metodo che carica il QML associato ad un layer_id prelevandolo tramite web service

        @param layer: layer
        @param layer_id: layer_id, id trasportato dal json univoco all'interno della stessa categoria
        @param layer_cat: categoria del layer per rendere univoca la ricerca della legenda qml
        """
        error = None
        userFilePath = ""
        class_name = self.__class__.__name__
        LOGGER.debug('loadQML class_name: %s' % (class_name))

        tab = 'indica'
        # pezza per caso indicatori per avere una row univoca non basta l'id all'interno di una categoria ma ci vuole anche idpadre
        idp = self.idpadre
        LOGGER.debug('loadQML idp: %s' % (idp))

        ex = ""
        try:
            query_args = {'id': layer_id, 'idp': idp, 'cat': layer_cat, 'tab': tab}
            encoded_args = urllib.unquote_plus(urllib.urlencode(query_args))

            LOGGER.debug('loadQML encoded_args: %s' % (encoded_args))

            filehandle = urllib2.urlopen(url, encoded_args)

            lines = csiutils.RemoveCR(filehandle.readlines())
            filehandle.close()

            LOGGER.debug('loadQML len(lines): %s' % (str(len(lines))))

            if len(lines) > 0:
                tx = '\n'.join(lines)
                #LOGGER.debug('loadQML tx: %s' % (tx))
                LOGGER.debug('loadQML %s \n >>> [ ... ] <<< \n %s' % (tx[:350], tx[-200:]))

                tf = tempfile.NamedTemporaryFile(suffix='.qml', delete=False)
                userFilePath = tf.name
                tf.write(tx)
                tf.flush()
                tf.close()

                layer.loadNamedStyle(userFilePath)

                """
                Logica caricamewnto QML :
                1 = Riclassificazione su 5 classi e ricalcolo
                """
                renderer = layer.rendererV2()
                if (self.comportamento_qml == 1):
                    nclasses = 5
                    mode = renderer.mode()
                    renderer.updateClasses(layer, mode, nclasses)
                    layer.setRendererV2(renderer)
                    renderer = layer.rendererV2()
                    LOGGER.debug('loadQML : 1 = Riclassificazione su 5 classi e ricalcolo : effettuata')

                    # l' uodate della legend symbology viene fatta nel finally del metodo chiamante
                    # self.iface.legendInterface().refreshLayerSymbology(layer)
                elif (self.comportamento_qml == 2):
                    LOGGER.debug('loadQML : 2 = Riclassificazione futura')
                    pass
                else:
                    LOGGER.debug('loadQML : %s = Riclassificazione non prevista per id=%s e nome=%s!' % (str(self.comportamento_qml), self.id, self.nome))
                    pass

        except Exception, ex:
            #raise
            error = "Errore caricamento qml: \ntab = %s%\nid = %s\ncategoria = %s\n\n %s" % tab, layer_id, layer_cat, ex
            QgsMessageLog.logMessage(error, 'CSI Atlante')
            LOGGER.error('loadQML %s' % (error))
        finally:
            if error is not None:
                pass

    def loadDefaultQML(self, layer):  # (self, layer, layer_id, layer_cat):
        """
        Metodo che carica un QML di default

        @param layer: layer
        """
        error = None
        class_name = self.__class__.__name__
        LOGGER.debug('loadDefaultQML class_name: %s' % (class_name))

        tab = 'indica'

        ex = ""
        try:
            renderer = layer.rendererV2()
#             renderer_type = renderer.type()
#             renderer_types = QgsRendererV2Registry().renderersList()
            geometry_type = layer.geometryType()

            symbol = QgsSymbolV2.defaultSymbol(geometry_type)
            if symbol is None:
                if geometry_type == QGis.Point:
                    symbol = QgsMarkerSymbolV2()
                elif geometry_type == QGis.Line:
                    symbol = QgsLineSymbolV2()
                elif geometry_type == QGis.Polygon:
                    symbol = QgsFillSymbolV2()

            border_color = QColor('#ff0000')
            fill_color = QColor('#ffffff')
            size = 10
            if geometry_type == QGis.Point:
                symbol_layer = QgsSimpleMarkerSymbolLayerV2()
                symbol_layer.setFillColor(fill_color)
                symbol_layer.setBorderColor(border_color)
                symbol_layer.setSize(size)
                symbol.changeSymbolLayer(0, symbol_layer)
            elif geometry_type == QGis.Polygon:
                symbol_layer = QgsSimpleFillSymbolLayerV2()
                symbol_layer.setFillColor(fill_color)
                symbol_layer.setBorderColor(border_color)
                symbol.setAlpha(0.5)  # QgsSymbolV2::setAlpha(qreal alpha)    1 = completely opaque, 0 = completely transparent
                symbol.changeSymbolLayer(0, symbol_layer)
            else:
                # for lines we do nothing special as the property setting
                # below should give us what we require.
                pass

            try:
                value = 0.5
                symbol_layer.setBorderWidth(value)
            except (NameError, KeyError):
                # use QGIS default border size
                # NameError is when symbol_layer is not defined (lines for example)
                # KeyError is when borderWidth is not defined
                if hasattr(symbol_layer, 'setBorderWidth') and geometry_type == QGis.Polygon:
                    symbol_layer.setBorderWidth(0)

            # Simple fill, QgsSimpleFillSymbolLayerV2
            # Outline: simple line, QgsSimpleLineSymbolLayerV2
            renderer.setSymbol(symbol)
            layer.setRendererV2(renderer)
            #transparency = 40
            #layer.setLayerTransparency(transparency)
            renderer = layer.rendererV2()
            # l' uodate della legend symbology viene fatta nel finally del metodo chiamante
            # self.iface.legendInterface().refreshLayerSymbology(layer)
        except Exception, ex:
            #raise
            #error = "Errore caricamento qml di default: \ntab = %s%\nid = %s\ncategoria = %s\n\n %s" % tab, layer_id, layer_cat, ex
            error = "Errore caricamento qml di default: tab = %s : %s" % (tab, ex)
            QgsMessageLog.logMessage(error, 'CSI Atlante')
            LOGGER.error('loadDefaultQML %s' % (error))
        finally:
            if error is not None:
                pass


class RASTERInfo:
    """
    Classe di gestione del dato raster
    """
    def __init__(self):
        self.category = ''
        self.category_backup = ''
        self.id = ''
        self.idtree = ''
        self.idpadre = ''
        self.nome = ''
        self.host = ''
        self.porta = ''
        self.dbname = ''
        self.schema = ''
        self.tavola = ''
        self.urlmetadati = ''
        self.scrittura = False
        self.utente = ''  # TODO: eliminare dal servizio?

    @classmethod
    def readFromJson(self, jsonObj):
        """
        Ricava dal json le informazioni dell'attributo 'raster'
        Alimenta una lista in cui ciascun elemento e' uno struct/dto RASTERInfo
        Da questo carica un tree.

        @param jsonObj: jsonObj
        @return: tree
        """
        olines = []
        try:
            for ln in jsonObj['raster']:
                w = RASTERInfo()
                w.category = ln['categoria']
                w.category_backup = ln['categoria']
                w.id = str(ln['idimmagine'])
                w.idtree = str(ln['idtree'])
                w.idpadre = str(ln['idpadre'])
                w.nome = ln['nome']
                w.host = ln['host']
                w.porta = str(ln.get('porta', ''))
                w.dbname = ln['dbname']
                w.schema = ln['aschema']
                w.utente = ln['utente']  # TODO: eliminare dal servizio?
                w.tavola = ln['tavola']
                w.urlmetadati = ln.get('urlmetadati', '')
                w.scrittura = ln['scrittura'] == 'S'

                olines.append(w)
        except Exception, ex:
            QgsMessageLog.logMessage("errore caricamento json: " + str(ex), 'CSI Atlante')
            return []

        tree = RASTERInfo.loadTree(olines)
        return tree

    def loadRasterLayer(self, iface, readQmlUrl, visible=False, loadQML=False):
        """
        Metodo che crea e carica un nuovo raster layer come definito in "host" e "tavola"

        @param iface: interfaccia qgis
        @param visible: boolean per caricare il layer gia' visibile (piu' lento)
        @param loadQML: boolean per caricare QML associato
        """
        # legendDescription = None
        if self.host == '':
            return
        if self.tavola == '':
            return

        legend = iface.legendInterface()
        legend.blockSignals(True)
        rlayer = QgsRasterLayer()
        oldValidation = 'useGlobal'  # per evitare UnboundLocalError: local variable 'oldValidation' referenced before assignment
        try:
            s = QSettings()
            oldValidation = s.value("/Projections/defaultBehaviour", "useGlobal", type=unicode)
            s.setValue("/Projections/defaultBehaviour", "useGlobal")

            # TODO: generalizzare
            # per ora carica solo raster da file system, ricavando il path come join di stringhe da host e tavola
            # dummyrasterpath = 'D:/prova/raster/sez156050.tif'
            dummyrasterpath = ''.join([self.host, self.tavola])
            rlayer = QgsRasterLayer(dummyrasterpath, self.nome)

            if rlayer.isValid():
                # If you do change layer symbology and would like ensure that the changes are immediately visible to the user
                if hasattr(rlayer, "setCacheImage"):
                    rlayer.setCacheImage(None)
                rlayer.triggerRepaint()

                # imposta il sistema di riferimento ricavato dal mapRenderer
                # (disattivato)
                # crs = iface.mapCanvas().mapRenderer().destinationCrs()
                # rlayer.setCrs(crs)
                QgsMapLayerRegistry.instance().addMapLayer(rlayer)
                legend.setLayerVisible(rlayer, visible)

                if loadQML:
                    self.loadQML(readQmlUrl, rlayer, self.id, self.category_backup)
            else:
                QMessageBox.information(None, "Tab Raster", "Il raster non e' valido\nVerificare l'esistenza o il percorso:\n\n%s\n\n%s" % (self.nome, dummyrasterpath))

        finally:
            s.setValue("/Projections/defaultBehaviour", oldValidation)
            legend.blockSignals(False)
            legend.refreshLayerSymbology(rlayer)

    def loadQML(self, url, layer, layer_id, layer_cat):
        """
        Metodo che carica il QML associato ad un layer_id prelevandolo tramite web service

        @param layer: layer
        @param layer_id: layer_id, id trasportato dal json univoco all'interno della stessa categoria
        @param layer_cat: categoria del layer per rendere univoca la ricerca della legenda qml
        """
        error = None
        userFilePath = ""
        tab = 'raster'
        try:
            query_args = {'id': layer_id, 'cat': layer_cat, 'tab': tab}
            encoded_args = urllib.urlencode(query_args)

            filehandle = urllib2.urlopen(url, encoded_args)

            lines = csiutils.RemoveCR(filehandle.readlines())
            filehandle.close()

            tx = '\n'.join(lines)

            fw = tempfile.NamedTemporaryFile(suffix='.qml', delete=False)
            userFilePath = fw.name
            # fw = open(userFilePath,"wb")
            fw.write(tx)
            fw.flush()
            fw.close()

            layer.loadNamedStyle(userFilePath)
        #except (IOError, OSError, ValueError), e:
        except Exception, ex:
            #raise
            error = "Errore caricamento qml: \ntab = %s%\nid = %s\ncategoria = %s\n\n %s" % tab, layer_id, layer_cat, ex
            QgsMessageLog.logMessage(error, 'CSI Atlante')
        finally:
            if error is not None:
                pass

    def setChildren(self, infolist):
        """
        setChildren
        @param infolist : lista di elementi
        """
        self.children = [t  for t in infolist if t.idpadre == self.idtree]
        if len(self.children) > 0:
            for t in self.children:
                t.setChildren(infolist)
        else:
            self.children = None

    def setChildrenAux(self, infolist, category_aux):
        """
        setChildrenAux
        @param infolist : lista di elementi
        @param category_aux : nome categoria addizionale artificiale
        """
        self.children = [t  for t in infolist if t.idpadre == self.idtree and t.category == self.category]
        if len(self.children) > 0:
            for t in self.children:
                t.setChildrenAux(infolist, category_aux)
                t.category = category_aux
        else:
            self.children = None

    @classmethod
    def loadTree(cl, infolist):
        """
        Carica gli elementi passati come lista e li restituisce in un tree

        @param infolist : lista di elementi
        @return: lzero : lista tree
        """
        # reimposta idpadre non esistente
        for el in infolist:
            l0 = [t  for t in infolist if t.idtree == el.idpadre and t.category == el.category]
            if len(l0) == 0:
                el.idpadre = ''

        l0 = [t  for t in infolist if t.idpadre == '']
        for t in l0:
            t.setChildren(infolist)

        # introduce una nuova categoria "All Inclusive"
        s = QSettings()
        category_aux = s.value("CSIAtlante/conf/categoriaAll", u"*", type=unicode)

        infolist_aux = copy.deepcopy(infolist)
        #l0_aux = copy.deepcopy(l0)
        l0_aux = [t  for t in infolist_aux if t.idpadre == '']
        for t in l0_aux:
            t.setChildrenAux(infolist_aux, category_aux)
            t.category = category_aux

        lzero = []
        lzero.extend(l0_aux)
        lzero.extend(l0)

        return lzero


class WMSInfo:
    """
    Classe di gestione del dato wms
    """
    def __init__(self):
        self.category = ''
        self.wmsURL = ''
        self.urlCapabilities = ''
        self.name = ''
        self.legenda = ''
        self.metadati = ''
        self.wmsTree = None

    def getWMSTree(self):
        if self.wmsTree is None:
            self.wmsTree = wmstree.WMSTree(self.name, self.urlCapabilities, self.category, self.metadati)
        return self.wmsTree

    @classmethod
    def readFromJson(cls, jsonObj):
        """
        Ricava dal json le informazioni dell'attributo 'geoservizio'
        Alimenta e restituisce una lista in cui ciascun elemento e' uno struct/dto WMSInfo

        @param jsonObj: jsonObj
        @return: wmsInfoList [WMSInfo, WMSInfo ...]
        """
        wmsInfoList = []
        try:
            for ln in jsonObj['wms']:
                w = WMSInfo()
                w.category = ln['categoria']
                w.name = ln['nome']
                w.wmsURL = ln['url']
                w.urlCapabilities = ln['urlcapabilities']
                w.metadati = ln.get('urlmetadati', '')
                wmsInfoList.append(w)
            return wmsInfoList
        except Exception, ex:
            QgsMessageLog.logMessage("errore caricamento json: " + str(ex), 'CSI Atlante')
            return []

    @classmethod
    def getInfoFromList(cl, infolist, wmstree):
        for info in infolist:
            if info.wmsTree == wmstree:
                return info
        return None

    @classmethod
    def readFromCache(cls, cachefile):
        """
        Recupera oggetto WMSInfoList[] serializzato in un file cache

        @param cachefile : nome completo del file serializzato
        @return:  wmsInfoList [WMSInfo, WMSInfo ...]
        """
        wmsInfoList = []
        try:
            prima = datetime.datetime.now()  # @UnusedVariable
            f = open(cachefile, 'r')  # , encoding='utf-8')
            wmsInfoList = pickle.load(f)
            f.close()
            dopo = datetime.datetime.now()  # @UnusedVariable

            return wmsInfoList
        except Exception, ex:
            QgsMessageLog.logMessage("errore caricamento da cache: " + str(ex), 'CSI Atlante')
            return []

    @classmethod
    def writeToCache(cls, cachefile, wmsInfoList):
        """
        Serializza oggetto WMSINfoList[] scrivendolo in un file cache

        @param cachefile : nome completo del file in cui serializzare
        @param wmsInfoList [WMSInfo, WMSInfo ...]
        @return: result = 0: ok , result > 0: error
        """
        try:
            prima = datetime.datetime.now()  # @UnusedVariable
            f = open(cachefile, 'w')  # , encoding='utf-8')
            pickle.dump(wmsInfoList, f)
            f.close()
            dopo = datetime.datetime.now()  # @UnusedVariable
            # msg = "Scrittura dump in \n" + cachefile + "\nprima: " + prima.strftime('%d %b %Y %H:%M:%S') + "\ndopo: " + dopo.strftime('%d %b %Y %H:%M:%S')
            # QMessageBox.information(None, "Scrittura dump ...", msg)
            return 0
        except Exception, ex:
            QgsMessageLog.logMessage("errore scrittura in cache: " + str(ex), 'CSI Atlante')
            return 9


class WMSSelection:
    """
    Classe WMSSelection
    """
    def __init__(self, wmsTree):
        self.tree = wmsTree
        self.layers = []

    def addLayer(self, layer):
        if layer in self.layers:
            return
        # if layer.style!=None:
        self.layers.append(layer)
        if layer.layers != None:
            for l in layer.layers:
                self.addLayer(l)

    def addAllLayers(self):
        self.layers = []
        for l in self.tree.layers:
            self.addLayer(l)

    def getLegendHTML(self, onlySelectedLayers=False):
        if onlySelectedLayers == False:
            mfilter = None
        else:
            mfilter = []
            for ly in self.layers:
                mfilter.append(ly.name)
        return self.tree.getLegendHTML(mfilter)

    def getLayerStyleTitlesLists(self):
        """
        Restituisce una lista di 3 array di dimensione n = numero dei layers della WMSSelection
        Layers = [] : array con i "name" dei layers (unicode)
        Styles = [] : array con gli "style" (se non presenti restituisce str: "default")
        Titles = [] : array con i "title" per ciascun layer (unicode)

        @return: LayerStyleTitlesLists
        """
        la = []
        st = []
        titles = []
        for layer in self.layers:
            if layer.style != None:
                la.append(layer.name)
                st.append(layer.style)
                titles.append(layer.title)
            else:
                la.append(layer.name)
                st.append('default')
                titles.append(layer.title)

        return [la, st, titles]

    @classmethod
    def getWMSSelectionList_LayerList(cl, layerList):
        """
        Restituisce una lista di oggetti wmslayers da una WMSSelection

        @param layerList
        @return: valuesList
        """
        dtree = {}
        for ob in layerList:
            if isinstance(ob, wmstree.WMSTree):
                if not ob in dtree:
                    sel = WMSSelection(ob)
                    sel.addAllLayers()
                    dtree[ob] = sel

            if isinstance(ob, wmstree.WMSLayer):
                k = ob.parentTree
                if not k in dtree:
                    dtree[k] = WMSSelection(k)
                dtree[k].addLayer(ob)

        return dtree.values()


class ConnectionsPortfolio(object):
    """
    Classe di gestione del portafoglio delle connessioni db
    """

    def __init__(self):
        self.connections = self.getConnections()

    #@staticmethod
    def getConnections(self):
        """
        Metodo che restituisce il dictionary delle connessioni presenti in portafoglio:
        {key1: conn1, key2: conn2, ..., key<n>: conn<n>)}

        key: unicode formattata come user@host:port:DATABASE ;
        conn: connessione ConnectionDTO

        @return: dictConnections
        """
        # TODO: ottimizzare con QMap
        dictConnections = {}
        try:
            s = QSettings()
            s.beginGroup("/CSIAtlante/connections/")
            names = s.childGroups()    # QStringList # API 2.0: Replace QStringList with list
            s.endGroup()
            for name in names:
                c = ConnectionDTO()
                c.name = name
                key = "/CSIAtlante/connections/" + c.name
                c.username = s.value(key + "/username", u'', type=unicode)
                c.host = s.value(key + "/host", u'', type=unicode)
                c.port = s.value(key + "/port", u'', type=unicode)
                c.database = s.value(key + "/database", u'', type=unicode)
                c.password = s.value(key + "/password", u'', type=unicode)
                c.compressed = self.compress(c.password, c.name)
                dictConnections[c.name] = c

            return dictConnections
        except Exception, ex:
            QgsMessageLog.logMessage("errore ricerca portafoglio connessioni: " + str(ex), 'CSI Atlante')
            return {}

    @staticmethod
    def patchConnections():
        """
        Patch delle connessioni nei qsettings
        tutti gli eventuali "vm-osstore2.csi.it" devono diventare "vm-osstore1.csi.it"

        @return: 0
        """
        old_host = "vm-osstore2.csi.it"
        new_host = "vm-osstore1.csi.it"
        try:
            s = QSettings()
            s.beginGroup("/CSIAtlante/connections/")
            names = s.childGroups()
            s.endGroup()
            for name in names:
                if old_host in name:
                    c = ConnectionDTO()
                    c.name = name
                    key = "/CSIAtlante/connections/" + c.name
                    c.username = s.value(key + "/username", u'', type=unicode)
                    c.host = s.value(key + "/host", u'', type=unicode)
                    c.port = s.value(key + "/port", u'', type=unicode)
                    c.database = s.value(key + "/database", u'', type=unicode)
                    c.password = s.value(key + "/password", u'', type=unicode)
                    # cancellare chiave originale
                    s.remove(key)
                    # nuova chiave con nuovo host
                    c.name = name.replace(old_host, new_host)
                    key = "/CSIAtlante/connections/" + c.name
                    c.host = c.host.replace(old_host, new_host)
                    s.setValue(key + "/host", c.host)
                    s.setValue(key + "/port", c.port)
                    s.setValue(key + "/database", c.database)
                    s.setValue(key + "/username", c.username)
                    s.setValue(key + "/password", c.password)
            # selected
            storedSelected = s.value('/CSIAtlante/connections/selected', u'', type=unicode)
            if old_host in storedSelected:
                newSelected = storedSelected.replace(old_host, new_host)
                s.setValue('/CSIAtlante/connections/selected', newSelected)
            QgsMessageLog.logMessage("OK patch vm-osstore2 --> vm-osstore1", 'CSI Atlante')
            return 0
        except Exception, ex:
            QgsMessageLog.logMessage("errore patch vm-osstore2.csi.it" + str(ex), 'CSI Atlante')
            return 9

    def updateConnections(self):
        """
        Metodo che aggiorna il dictionary delle connessioni
        """
        self.connections = self.getConnections()

    def getPassword(self, host, port, database, username):
        """
        Metodo che compone la key user@host:port:DATABASE
        e ottiene la password associata nel portafoglio delle connessioni.
        Se non la trova restituisce None

        @param host: unicode host
        @param port: unicode port
        @param database: unicode database
        @param username: unicode username
        """
        keyconnectionname = self.formatConnectionName(username, host, port, database)
        pwd = self.findPassword(keyconnectionname)
        return pwd

    def findPassword(self, key):
        """
        Metodo che usa la key e cerca la password associata nel portafoglio delle connessioni.
        Se non la trova restituisce None

        @param key: chiave unicode formattata user@host:port:DATABASE
        """
        if key in self.connections:
            c = self.connections[key]
            pwd = c.password
        else:
            pwd = None
        return pwd

    def formatConnectionName(self, username, host, port, database):
        """
        Restituisce il nome di una connessione formattata come: user@host:port:DATABASE
        tutto lowercase eccetto il database che e' case sensitive

        @param username: unicode username
        @param host: unicode host
        @param port: unicode port
        @param database: unicode database
        """
        # @TODO: richiamare NewConnectionDialog.formatConnectionName
        aux = "%s@%s:%s" % (username, host, port)
        aux = aux.lower()
        fcname = "%s:%s" % (aux, database)
        # fcname.encode('ascii', 'replace')
        # fcname = "%s@%s:%s\/%s" % (username, host, port, database)
        return fcname

    @classmethod
    def compress(cls, tocompress, cover):
        """
        compressione
        @return: compressed
        """
        covered = ''.join([tocompress.encode('utf-8'), cover.encode('utf-8')])
        compressed = bz2.compress(covered)
        compressed = binascii.hexlify(compressed)
        return compressed

    @classmethod
    def decompress(cls, compressed, cover):
        """
        decompressione
        @return: decompressed
        """
        decompressed = binascii.unhexlify(compressed)
        decompressed = bz2.decompress(decompressed).decode('utf-8').replace(cover, "")
        return decompressed


class ConnectionDTO():
    """
    Classe DTO per connessione DB
    i membri sono unicode
    """
    def __init__(self):
        self.name = u''
        self.username = u''
        self.host = u''
        self.port = u''
        self.database = u''
        self.password = u''
        self.compressed = u''


class ServicesPortfolio():
    """
    Classe di gestione del portafoglio dei servizi
    """
    def __init__(self):
        self.services = self.getServices()

    #@staticmethod
    def getServices(self):
        """
        Metodo che restituisce il dictionary dei servizi presenti in portafoglio:
        {key1: service1, key2: service2, ..., key<n>: service<n>)}

        key: unicode col nome del servizio
        service: servizio ServiceDTO

        @return: dictServices
        """
        # @TODO : ottimizzare con QMap
        dictServices = {}
        try:
            s = QSettings()
            s.beginGroup("/CSIAtlante/services/")
            names = s.childGroups()
            s.endGroup()
            for name in names:
                c = ServiceDTO()
                c.name = name
                key = "/CSIAtlante/services/" + c.name
                c.url = s.value(key + "/url", u'', type=unicode)
                c.usr = s.value(key + "/usr", u'', type=unicode)
                c.pwd = s.value(key + "/pwd", u'', type=unicode)
                c.compressed = self.compress(c.pwd, c.name)

                dictServices[c.name] = c

            return dictServices
        except Exception, ex:
            QgsMessageLog.logMessage("errore ricerca portafoglio servizi: " + str(ex), 'CSI Atlante')
            return {}

    def updateServices(self):
        """
        Metodo che aggiorna il dictionary dei servizi
        """
        self.services = self.getServices()

    @classmethod
    def compress(cls, tocompress, cover):
        """
        compressione
        @return: compressed
        """
        return ConnectionsPortfolio.compress(tocompress, cover)

    @classmethod
    def decompress(cls, compressed, cover):
        """
        decompressione
        @return: decompressed
        """
        return ConnectionsPortfolio.decompress(compressed, cover)


class ServiceDTO():
    """
    Classe DTO per connessione servizio
    """
    def __init__(self):
        self.name = u''
        self.url = u''
        self.usr = u''
        self.pwd = u''
        self.compressed = u''


class CONFInfo:
    """
    Classe di gestione della gui da configurazione
    """
    def __init__(self):
        self.flg_vector = 0
        self.flg_progetti = 0
        self.flg_raster = 0
        self.flg_wms = 0
        self.flg_tms = 0
        self.flg_wfs = 0
        self.flg_indica = 0
        self.flg_indica_geo = 0

    @classmethod
    def readFromJson(cls, jsonObj):
        """
        Ricava dal json le informazioni di configurazione del tab conf

        @param jsonObj: jsonObj
        @return: CONFInfo object instance
        """
        try:
            # per ora il json e' un dictionary {}
            ln = jsonObj
            c = CONFInfo()
            c.flg_vector = ln.get('flg_vector', 0)
            c.flg_progetti = ln.get('flg_progetti', 0)
            c.flg_raster = ln.get('flg_raster', 0)
            c.flg_wms = ln.get('flg_wms', 0)
            c.flg_tms = ln.get('flg_tms', 0)
            c.flg_wfs = ln.get('flg_wfs', 0)
            c.flg_indica = ln.get('flg_indica', 0)
            c.flg_indica_geo = ln.get('flg_indica_geo', 0)
            return c
        except Exception, ex:
            QgsMessageLog.logMessage("errore caricamento json: " + str(ex), 'CSI Atlante')
            return None

    def __str__(self):
        return "%d %d %d %d %d %d %d %d" % (self.flg_vector, self.flg_progetti, self.flg_raster, self.flg_wms, self.flg_tms, self.flg_wfs, self.flg_indica, self.flg_indica_geo)
