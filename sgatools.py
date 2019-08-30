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

 Date                 : 2015-11-30
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

from qgis.core import Qgis, QgsMessageLog
from qgis.core import QgsMapLayer
from qgis.gui import QgsMapToolIdentify
from qgis.PyQt import QtCore, QtWidgets
from qgis.PyQt.QtCore import QSettings
from qgis.PyQt.QtWidgets import QMessageBox

from qgis.PyQt.QtGui import QCursor, QPixmap

from .graphidentifydialog import GraphIdentifyDialog

from operator import itemgetter
import collections
import json
import logging
import urllib
import urllib.request, urllib.parse, urllib.error
import os

PROJECT_NAME = "CSIAtlante"
MAIN_MODULE_NAME = "csiatlante"
FOLDER_NAME = __name__.split('.')[0]
MODULE_NAME = __name__.split('.')[1]
MAIN_MODULE = "%s.%s" % (FOLDER_NAME, MAIN_MODULE_NAME)
LOGGER_NAME = MAIN_MODULE
LOGGER = logging.getLogger()

LOGGER_TAG = 'SGA Tools'

try:
    module = __import__(MAIN_MODULE)
    class_logger = getattr(module, "csiLogger")
    LOGGER = class_logger(LOGGER_NAME)
    LOGGER.debug('### sgatools logger from: CSIAtlante.csiatlante.csiLogger')
except Exception as ex:
    LOGGER = logging.getLogger()
    LOGGER.debug('### sgatools logger from: logging.getLogger()')

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

# -----------------------------------------------------------------------------
#qgisapp.cpp
#    connect( mActionIdentify, SIGNAL( triggered() ), this, SLOT( identify() ) );
#qgismaptoolidentifyaction.cpp
#    void QgsMapToolIdentifyAction::canvasReleaseEvent( QgsMapMouseEvent* e )
#qgismaptoolidentify.h
#qgismaptoolidentify.cpp
# -----------------------------------------------------------------------------


class GraphMapToolIdentify(QgsMapToolIdentify):
    """
    Reimplementa e estende QgsMapToolIdentify in modo da renderizzare l'identfy result
    con un grafico d3/js dinamico inserito in una qt webview
    """
    def __init__(self, iface, caller):
        #QgsMapToolIdentify.__init__(self, iface.mapCanvas())
        super(GraphMapToolIdentify, self).__init__(iface.mapCanvas())
        # set cursor
        self.setCursor(Cursors.graph_identify_cursor())
        # extends attributes
        self.iface = iface
        self.caller = caller
        self.url = caller.dlg.getServiceGraphUrl()  # 'http://osgis2.csi.it/identigraph/graph.php'

        self.denominazioneunita = u''
        self.dimensione = u''
        self.idealpoint = u''
        self.indicatore = u''
        self.nomicampi = list()
        self.periodi = list()
        self.periodistringa = u''
        self.periodilabel = dict()
        self.periodicita = u''
        self.unita = u''
        self.unitamisura = u''

        self.identify_dialog = GraphIdentifyDialog()

    def __del__(self):
        del self.identify_dialog.browser.web_inspector
        del self.identify_dialog.browser
        del self.identify_dialog

    def activate(self):
        """called when set as currently active map tool
        void QgsMapTool::activate()"""
        super(GraphMapToolIdentify, self).activate()

    def canvasPressEvent(self, e):
        """ canvasPressEvent """
        super(GraphMapToolIdentify, self).canvasPressEvent(e)

    def canvasReleaseEvent(self, e):
        """
        intercetta l'evento del rilascio del click sul canvas e fa il lavoro "sporco" dei grafici:
        innesto nell'identify, chiamata servizio generazione grafico, caricamento dialogo con webview
        """
        #super(GraphMapToolIdentify, self).canvasReleaseEvent(e)
        try:
            point = self.toMapCoordinates(e.pos())
            xp = point.x()
            yp = point.y()
            #QMessageBox.information(None, "sgatools", "canvasReleaseEvent...\n%s\n%s" % (str(xp), str(yp)))
            QgsMessageLog.logMessage('sgatools::GraphMapToolIdentify::canvasReleaseEvent: point x: %s  y: %s' % (str(xp), str(yp)), LOGGER_TAG, Qgis.Info)

            """QList< IdentifyResult > List of QgsMapToolIdentify::IdentifyResult
            results = self.identify(e.x(), e.y(), mylayerList, mode)

            enum QgsMapToolIdentify::IdentifyMode
            Enumerator
            DefaultQgsSetting
            ActiveLayer
            TopDownStopAtFirst
            TopDownAll
            LayerSelection
            """
#             identify_result = self.identify(e.x(), e.y(), self.LayerSelection, self.VectorLayer)
#             identify_result = self.identify(e.x(), e.y(), self.ActiveLayer, self.VectorLayer)

            seriestoricalayerlist = self.getSerieStoricaLayerList()
            current_layer = self.iface.mapCanvas().currentLayer()

            if current_layer is None:
                QMessageBox.information(None, "sgatools", "Nessun layer attivo!")
                #self.iface.mainWindow().statusBar().showMessage("Nessun layer attivo!")
                return

            if current_layer in seriestoricalayerlist:
                pass
            else:
                QMessageBox.information(None, "sgatools", "Il layer attivo non e' di tipo serie storica!: \n%s" % (current_layer.name()))
                QgsMessageLog.logMessage("sgatools::canvasReleaseEvent: Il layer attivo non e' di tipo serie storica!: %s" % (current_layer.name()), LOGGER_TAG, Qgis.Info)
                return

            self.dimensione = current_layer.customProperty("sga/dimensione", "")
            self.idealpoint = current_layer.customProperty("sga/idealpoint", "")
            self.indicatore = current_layer.customProperty("sga/indicatore", "")
            self.periodistringa = current_layer.customProperty("sga/periodi", "")
            self.periodicita = current_layer.customProperty("sga/periodicita", "")
            self.unita = current_layer.customProperty("sga/unita", "")
            self.unitamisura = current_layer.customProperty("sga/unitamisura", "")

            LOGGER.debug("self.dimensione : %s" % (self.dimensione))
            LOGGER.debug("self.idealpoint : %s" % (str(self.idealpoint)))
            LOGGER.debug("self.indicatore : %s" % (self.indicatore))
            LOGGER.debug("self.periodistringa : %s" % (self.periodistringa))
            LOGGER.debug("self.periodicita : %s" % (self.periodicita))
            LOGGER.debug("self.unita : %s" % (self.unita))
            LOGGER.debug("self.unitamisura : %s" % (self.unitamisura))

            prefix = ''
            periodicita = self.periodicita

            if (periodicita == "Annuale"):
                prefix = 'anno_'
            elif (periodicita == "Semestrale"):
                prefix = 'semestre_'
            elif (periodicita == "Quadrimestrale"):
                prefix = 'quadrimestre_'
            elif (periodicita == "Trimestrale"):
                prefix = 'trimestre_'
            elif (periodicita == "Mensile"):
                prefix = 'mese_'
            elif (periodicita == "Settimanale"):
                prefix = 'settimana_'
            else:
                prefix = ''

            nomecampo = ""
            plist = self.periodistringa.split()
            for p in plist:
                self.periodi.append(p)
                nomecampo = ('%s%s' % (prefix, p))
                self.nomicampi.append(nomecampo)
                self.periodilabel[nomecampo] = p

            """ QList<IdentifyResult> results = QgsMapToolIdentify::identify( e->x(), e->y(), layerList, mode );"""
            identify_result = self.identify(e.x(), e.y(), seriestoricalayerlist, self.ActiveLayer)

            if len(identify_result) == 0:
                self.iface.mainWindow().statusBar().showMessage("No features at this position found.")
                QgsMessageLog.logMessage('len(identify_result) == 0', LOGGER_TAG, Qgis.Info)

            else:
                feature = identify_result[0].mFeature

                allfields = feature.fields()
                allfieldsnames = []
                for i in range(allfields.count()):
                    field = allfields[i]
                    allfieldsnames.append(field.name())
                LOGGER.debug("allfieldsnames ricavati da identify: %s" % (''.join(allfieldsnames)))

                values_array = list()

                for fieldname in allfieldsnames:
                    if (fieldname in self.nomicampi):

                        item = collections.OrderedDict()
                        item['x'] = self.periodilabel[fieldname]  # fieldname.replace('_', ' ')
                        item['y'] = feature.attribute(fieldname)
                        values_array.append(item)
                        LOGGER.debug("x: %s - y: %s" % (fieldname, feature.attribute(fieldname)))

                    if fieldname == 'denominazione':
                        self.denominazioneunita = feature.attribute(fieldname)
                        LOGGER.debug("self.denominazioneunita : %s" % (self.denominazioneunita))
                # ---------------------------------------------------------------------------------
                for v in values_array:
                    QgsMessageLog.logMessage('values: %s %s' % (v['x'], v['y']), LOGGER_TAG, Qgis.Info)

#                 values_sorted_array = sorted(values_array, key=itemgetter('x'))
#
#                 for v in values_sorted_array:
#                     QgsMessageLog.logMessage('values_sorted: %s %s' % (v['x'], v['y']), LOGGER_TAG, Qgis.Info)

                blob_array = list()

                # elemento 0 di blob_array
                obj_dict = collections.OrderedDict()

                item = collections.OrderedDict()
                item['title'] = "%s %s - %s" % (self.indicatore.encode("utf-8"), self.dimensione.encode("utf-8"), self.unita.encode("utf-8"))
                item['subtitle'] = "%s - Unità di misura: %s" % (self.denominazioneunita.encode("utf-8"), self.unitamisura.encode("utf-8"))
                obj_dict['options'] = item

                item = collections.OrderedDict()
                item['selectedType'] = "area_steps_vertical"
                item['color'] = "#F01322"
                #item['xlabel'] = "Anni" if self.periodicita == "Annuale" else "Periodi"
                item['xlabel'] = u"Periodicità %s" % (self.periodicita)
                item['ylabel'] = "Valori"
                obj_dict['graph'] = item

                LOGGER.debug("self.idealpoint : %s" % (str(self.idealpoint)))

                item = collections.OrderedDict()
                item['value'] = self.idealpoint
                item['label'] = "Ideal Point"
                obj_dict['goal'] = item

                obj_dict['values'] = values_array

                blob_array.append(obj_dict)
                LOGGER.debug("blob_array completato")
                # ---------------------------------------------------------------------------------
#
#                 LOG_PATH = ''.join([QFileInfo(os.path.realpath(__file__)).path(), '/'])
#                 OUT_FILENAME = ''.join([LOG_PATH, '/', 'blob.json'])
#                 with open(OUT_FILENAME, 'w') as outfile:
#                     json.dump(blob_array, outfile)  # NB <--- dump
#
                # ---------------------------------------------------------------------------------
                blob_json = json.dumps(blob_array, encoding="utf-8")  # NB <--- dumps
                data_dict = {'data': blob_json}

                s = QSettings()
                REMOTE_DBG = s.value(''.join([PROJECT_NAME, "/debug"]), False, type=bool)
                self.identify_dialog = GraphIdentifyDialog(enable_developer=REMOTE_DBG)
                #self.identify_dialog.setWindowTitle("Identify")

                try:
                    self.identify_dialog.browser.navigate('POST', self.url, data_dict)
                except Exception as ex:
                    QgsMessageLog.logMessage('identify_dialog.browser.navigate: %s' % str(ex), LOGGER_TAG, Qgis.Info)
                finally:
                    QgsMessageLog.logMessage('identify_dialog.browser.navigate: finally', LOGGER_TAG, Qgis.Info)
                    self.identify_dialog.show()  # show() for non-modal dialog

        except Exception as ex:
            QMessageBox.information(None, "sgatools", "errore canvasReleaseEvent: %s " % (ex))
        finally:
            pass

    def getSerieStoricaLayerList(self):
        seriestoricalayerlist = list()
        layers = self.iface.mapCanvas().layers()
        for layer in layers:
            if layer.type() == QgsMapLayer.VectorLayer:
                if layer.customProperty("sga/serie_storica", "false") == "true":
                    seriestoricalayerlist.append(layer)
        return seriestoricalayerlist

    def dirty_work_harcoded(self):
        """
        """
        QgsMessageLog.logMessage('GraphMapToolIdentify::dirty_work: start', LOGGER_TAG, Qgis.Info)

        # ---------------------------------------------------------------------------------------
        blob_array = list()

        # elemento 0 di blob_array
        obj_dict = collections.OrderedDict()

        item = collections.OrderedDict()
        item['title'] = "Modellistica qualità dell'aria PM10"
        item['subtitle'] = "Unità di misura mcg m3"
        obj_dict['options'] = item

        item = collections.OrderedDict()
        item['selectedType'] = "area_steps_vertical"
        item['color'] = "#F01322"
        item['xlabel'] = "Anno"
        item['ylabel'] = "Valori m3"
        obj_dict['graph'] = item

        item = collections.OrderedDict()
        item['value'] = 10
        item['label'] = "valore di tendenza"
        obj_dict['goal'] = item

        values_array = list()

        item = collections.OrderedDict()
        item['x'] = "l'àèòù 2011"
        item['y'] = 7.13
        values_array.append(item)

        item = collections.OrderedDict()
        item['x'] = "Anno 2012"
        item['y'] = 5.12
        values_array.append(item)

        item = collections.OrderedDict()
        item['x'] = "Anno 2013"
        item['y'] = 4
        values_array.append(item)

        item = collections.OrderedDict()
        item['x'] = "Anno 2014"
        item['y'] = 15
        values_array.append(item)

        item = collections.OrderedDict()
        item['x'] = "Anno 2015"
        item['y'] = -10.52
        values_array.append(item)

        item = collections.OrderedDict()
        item['x'] = "Anno 2016"
        item['y'] = -20.6
        values_array.append(item)

        item = collections.OrderedDict()
        item['x'] = "Anno 2017"
        item['y'] = 10.6
        values_array.append(item)

        obj_dict['values'] = values_array

        blob_array.append(obj_dict)

        # elemento 1 di blob_array
        # obj_dict = collections.OrderedDict()
        # ...
        # ...
        # blob_array.append(obj_dict)

        # elemento 2 di blob_array
        # obj_dict = collections.OrderedDict()
        # ...
        # ...
        # blob_array.append(obj_dict)

        # DEBUG
        LOG_PATH = ''.join([QFileInfo(os.path.realpath(__file__)).path(), '/'])
        OUT_FILENAME = ''.join([LOG_PATH, '/', 'blob.json'])
        with open(OUT_FILENAME, 'w') as outfile:
            json.dump(blob_array, outfile)  # NB <--- dump

        # send ...
        blob_json = json.dumps(blob_array, encoding="utf-8")  # NB <--- dumps

        data_dict = {'data': blob_json}
        # --------------------------------------------------------------------------------------
        s = QSettings()
        REMOTE_DBG = s.value(''.join([PROJECT_NAME, "/debug"]), False, type=bool)
        self.identify_dialog = GraphIdentifyDialog(enable_developer=REMOTE_DBG)

        try:
            self.identify_dialog.browser.navigate('POST', self.url, data_dict)

        except Exception as ex:
            QgsMessageLog.logMessage('GraphMapToolIdentify::dirty_work:: %s' % str(ex), LOGGER_TAG, Qgis.Info)
        finally:
            QgsMessageLog.logMessage('GraphMapToolIdentify::dirty_work: finally', LOGGER_TAG, Qgis.Info)
            self.identify_dialog.show()
        QgsMessageLog.logMessage('GraphMapToolIdentify::dirty_work: end', LOGGER_TAG, Qgis.Info)



class ChartMapToolIdentify(QgsMapToolIdentify):
    """
    Reimplementa e estende QgsMapToolIdentify in modo da renderizzare l'identify result
    con un chart georiferito da posizionare in mappa

    Adattamento per chiamare il servizio osgis2 [ottobre 2015]
    http://osgis2.csi.it/graph/sga/graph_stream.php?title=Rifiuti+urbani+Raccolta+Differenziata+Totale+-+Comune+di+TORINO&key3=anno_2011&goalkey=goal&key1=anno_2009&goalval=12&title2=Unita%27+di+misura%3A+t%2Fanno&key2=anno_2010&val3=272908.0&val2=285013.0&val1=292516.0&type=bar

    Refactoring totale marzo 2016 per farlo diventare un vero tool esterno,
    @TODO: in seguito a questo refactoring ha molte parti comuni con GraphMapToolIdentify
    """
    def __init__(self, iface, caller):
        #QgsMapToolIdentify.__init__(self, iface.mapCanvas())
        super(ChartMapToolIdentify, self).__init__(iface.mapCanvas())
        # set cursor
        self.setCursor(Cursors.chart_identify_cursor())
        # extends attributes
        self.iface = iface
        self.caller = caller
        self.url = caller.dlg.getServiceChartUrl()  # "http://osgis2.csi.it/graph/sga/graph_stream.php"

        self.denominazioneunita = u''
        self.dimensione = u''
        self.idealpoint = u''
        self.indicatore = u''
        self.nomicampi = list()
        self.periodi = list()
        self.periodistringa = u''
        self.periodilabel = dict()
        self.periodicita = u''
        self.unita = u''
        self.unitamisura = u''

        self.identify_dialog = GraphIdentifyDialog()

    def activate(self):
        """called when set as currently active map tool
        void QgsMapTool::activate()"""
        super(ChartMapToolIdentify, self).activate()

    def canvasPressEvent(self, e):
        """ canvasPressEvent """
        super(ChartMapToolIdentify, self).canvasPressEvent(e)

    def canvasReleaseEvent(self, e):
        """
        intercetta l'evento del rilascio del click sul canvas e fa il lavoro "sporco" dei grafici:
        innesto nell'identify, chiamata servizio generazione grafico, caricamento in legend e map
        """
        #super(ChartMapToolIdentify, self).canvasReleaseEvent(e)
        try:
            point = self.toMapCoordinates(e.pos())
            xp = point.x()
            yp = point.y()
            QgsMessageLog.logMessage('sgatools::ChartMapToolIdentify::canvasReleaseEvent: point x: %s  y: %s' % (str(xp), str(yp)), LOGGER_TAG, Qgis.Info)

            seriestoricalayerlist = self.getSerieStoricaLayerList()
            current_layer = self.iface.mapCanvas().currentLayer()

            if current_layer is None:
                QMessageBox.information(None, "sgatools", "Nessun layer attivo!")
                return

            if current_layer in seriestoricalayerlist:
                pass
            else:
                QMessageBox.information(None, "sgatools", "Il layer attivo non e' di tipo serie storica!: \n%s" % (current_layer.name()))
                QgsMessageLog.logMessage("sgatools::canvasReleaseEvent: Il layer attivo non e' di tipo serie storica!: %s" % (current_layer.name()), LOGGER_TAG, Qgis.Info)
                return

            self.dimensione = current_layer.customProperty("sga/dimensione", "")
            self.idealpoint = current_layer.customProperty("sga/idealpoint", "")
            self.indicatore = current_layer.customProperty("sga/indicatore", "")
            self.periodistringa = current_layer.customProperty("sga/periodi", "")
            self.periodicita = current_layer.customProperty("sga/periodicita", "")
            self.unita = current_layer.customProperty("sga/unita", "")
            self.unitamisura = current_layer.customProperty("sga/unitamisura", "")

            LOGGER.debug("self.dimensione : %s" % (self.dimensione))
            LOGGER.debug("self.idealpoint : %s" % (str(self.idealpoint)))
            LOGGER.debug("self.indicatore : %s" % (self.indicatore))
            LOGGER.debug("self.periodistringa : %s" % (self.periodistringa))
            LOGGER.debug("self.periodicita : %s" % (self.periodicita))
            LOGGER.debug("self.unita : %s" % (self.unita))
            LOGGER.debug("self.unitamisura : %s" % (self.unitamisura))

            prefix = ''
            periodicita = self.periodicita

            if (periodicita == "Annuale"):
                prefix = 'anno_'
            elif (periodicita == "Semestrale"):
                prefix = 'semestre_'
            elif (periodicita == "Quadrimestrale"):
                prefix = 'quadrimestre_'
            elif (periodicita == "Trimestrale"):
                prefix = 'trimestre_'
            elif (periodicita == "Mensile"):
                prefix = 'mese_'
            elif (periodicita == "Settimanale"):
                prefix = 'settimana_'
            else:
                prefix = ''

            nomecampo = ""
            plist = self.periodistringa.split()
            for p in plist:
                self.periodi.append(p)
                nomecampo = ('%s%s' % (prefix, p))
                self.nomicampi.append(nomecampo)
                self.periodilabel[nomecampo] = p

            identify_result = self.identify(e.x(), e.y(), seriestoricalayerlist, self.ActiveLayer)

            if len(identify_result) == 0:
                self.iface.mainWindow().statusBar().showMessage("No features at this position found.")
                QgsMessageLog.logMessage('len(identify_result) == 0', LOGGER_TAG, Qgis.Info)

            else:
                feature = identify_result[0].mFeature

                allfields = feature.fields()
                allfieldsnames = []
                for i in range(allfields.count()):
                    field = allfields[i]
                    allfieldsnames.append(field.name())
                LOGGER.debug("allfieldsnames ricavati da identify: %s" % (''.join(allfieldsnames)))

                values_array = list()

                for fieldname in allfieldsnames:
                    if (fieldname in self.nomicampi):

                        item = collections.OrderedDict()
                        item['x'] = self.periodilabel[fieldname]
                        item['y'] = feature.attribute(fieldname)
                        values_array.append(item)
                        LOGGER.debug("x: %s - y: %s" % (fieldname, feature.attribute(fieldname)))

                    if fieldname == 'denominazione':
                        self.denominazioneunita = feature.attribute(fieldname)
                        LOGGER.debug("self.denominazioneunita : %s" % (self.denominazioneunita))
                # ---------------------------------------------------------------------------------
                for v in values_array:
                    QgsMessageLog.logMessage('values: %s %s' % (v['x'], v['y']), LOGGER_TAG, Qgis.Info)

#                 values_sorted_array = sorted(values_array, key=itemgetter('x'))
#
#                 for v in values_sorted_array:
#                     QgsMessageLog.logMessage('values_sorted: %s %s' % (v['x'], v['y']), LOGGER_TAG, Qgis.Info)

                #title = "%s %s - %s" % (self.indicatore.encode("utf-8"), self.dimensione.encode("utf-8"), self.unita.encode("utf-8"))
                title = "%s %s - %s" % (self.indicatore.encode("utf-8"), self.dimensione.encode("utf-8"), self.denominazioneunita.encode("utf-8"))
                subtitle = "Unità di misura: %s            Periodicità: %s" % (self.unitamisura.encode("utf-8"), self.periodicita.encode("utf-8"))
                chart_type = 'bar'
                idealpoint = self.idealpoint

                query_args = {'title': title,
                              'title2': subtitle,
                              'type': chart_type,
                              'goalkey': 'goal',
                              'goalval': idealpoint
                              }
                i = 0
                for v in values_array:
                    i = i + 1
                    key_name = "key%d" % (i)
                    val_name = "val%d" % (i)
                    QgsMessageLog.logMessage('%s=%s %s=%s' % (key_name, v['x'], val_name, v['y']), LOGGER_TAG, Qgis.Info)
                    query_args[key_name] = v['x']
                    query_args[val_name] = v['y']

                encoded_args = urllib.urlencode(query_args)

                LOGGER.debug('--- SERVIZIO CHART -----------------------------------------------------------------------------')
                LOGGER.debug("%s?%s" % (self.url, encoded_args))
                LOGGER.debug('------------------------------------------------------------------------------------------------')
                LOGGER.debug(str(query_args))
                LOGGER.debug('------------------------------------------------------------------------------------------------')

                img_tocname = title
                img_name = title
                img_path = ''.join([QFileInfo(os.path.realpath(__file__)).path(), '/graphs'])
                img_fullname = ''.join([img_path, '/', img_name, '.png'])

                """ Chunked_transfer_encoding """
                use_HTTP_GET = True
                CHUNK = 16 * 1024
                data = ''
                try:
                    """ the HTTP request will be a POST instead of a GET when the data parameter is provided"""
                    if (use_HTTP_GET):
                        """GET"""
                        url_get = ''.join([self.url, '?', encoded_args])
                        LOGGER.debug('url_get:  %s' % url_get)
                        res = urllib.urlopen(url_get)
                    else:
                        """POST"""
                        LOGGER.debug('url_post:  %s%s' % (self.url, encoded_args))
                        res = urllib.urlopen(self.url, data=encoded_args)

                    with open(img_fullname, "wb") as outfile:
                        chunk = res.read(CHUNK)
                        while chunk:
                            data += chunk
                            chunk = res.read(CHUNK)
                        outfile.write(data)

                except urllib.HTTPError as ex:
                    LOGGER.error("errore scrittura file: %s " % (ex))
                    if ex.code == 404:
                        print("404")
                    else:
                        print("else 404")
                except urllib.URLError as ex:
                    LOGGER.error("Not an HTTP-specific error %s" % (ex))
                except IOError as ex:
                    LOGGER.error("errore scrittura file: %s " % (ex))
                finally:
                    #LOGGER.debug('res headers:  %s' % (res.headers))
                    res.close()

                world_fullname = ''.join([img_path, '/', img_name, '.pgw'])
                fw = open(world_fullname, 'w')
                fw.write("%0.14f\n" % 29.99568903578100)
                fw.write("%0.14f\n" % 0.00000000000000)
                fw.write("%0.14f\n" % 0.00000000000000)
                fw.write("%0.14f\n" % -29.99694563225412)
                fw.write("%0.14f\n" % xp)  # 395009.00000000000000)
                fw.write("%0.14f\n" % yp)  # 4992105.00000000000000)
                fw.close()

                # workaround per evitare warning di SRS mancante
                from osgeo import osr, gdal, gdalconst  # @UnusedImport
                dataset = gdal.Open(img_fullname)  # (img_fullname, gdalconst.GA_Update)
                if (dataset == None):
                    LOGGER.debug("canvasReleaseEvent: dataset == None per img_fullname: %s" % (img_fullname))

                band = dataset.GetRasterBand(1)  # @UnusedVariable
                srs = osr.SpatialReference()
                srs.ImportFromEPSG(32632)
                dataset.SetProjection(srs.ExportToWkt())
                dataset = None

                # caricamento in legend nel grouplayer di serie storica grafici
                legend = self.iface.legendInterface()
                groupindex = ChartMapToolIdentify.getGroupIndexSerieStoricaGrafici(self.iface)

                if (groupindex < 0):
                    pass

                # --------------------------------------------------------------
                # http://jiraprod.csi.it:8083/browse/CSIATLANTE-7
                #  i file raster "Serie Storica Grafici" sono sempre accesi.
                #legend.setGroupVisible(groupindex, True)
                # --------------------------------------------------------------

                # made sure the crs prompt is disabled
                s = QSettings()
                oldValidation = s.value("/Projections/defaultBehaviour", "useGlobal", type=unicode)
                s.setValue("/Projections/defaultBehaviour", "useGlobal")

                crs = QgsCoordinateReferenceSystem(32632, QgsCoordinateReferenceSystem.EpsgCrsId)

                fileinfo = QFileInfo(img_fullname)
                basename = fileinfo.baseName()  # @UnusedVariable

                rlayer = QgsRasterLayer(img_fullname, img_tocname)
                if rlayer.isValid():
#                     if hasattr(rlayer, "setCacheImage"):
#                         rlayer.setCacheImage(None)   DeprecationWarning: QgsMapLayer.setCacheImage() is deprecated

                    rlayer.triggerRepaint()
                    QgsMapLayerRegistry.instance().addMapLayer(rlayer)
                    rlayer.setCrs(crs, emitSignal=True)

                    legend.setLayerVisible(rlayer, True)
                    legend.moveLayer(rlayer, groupindex)
                else:
                    QMessageBox.information(None, "canvasReleaseEvent  DEBUG", "rlayer not valid!")
                    LOGGER.debug("errore canvasReleaseEvent: rlayer not valid!")

                s.setValue("/Projections/defaultBehaviour", oldValidation)

        except Exception as ex:
            QMessageBox.information(None, "sgatools", "errore canvasReleaseEvent: %s " % (ex))
        finally:
            # e.c@20160329
            self.iface.mapCanvas().setMapTool(self)

    def getSerieStoricaLayerList(self):
        seriestoricalayerlist = list()
        layers = self.iface.mapCanvas().layers()
        for layer in layers:
            if layer.type() == QgsMapLayer.VectorLayer:
                if layer.customProperty("sga/serie_storica", "false") == "true":
                    seriestoricalayerlist.append(layer)
        return seriestoricalayerlist

    @classmethod
    def getGroupIndexSerieStoricaGrafici(cl, iface):
        """Restituisce l'indice del gruppo che contiente i grafici georiferiti di serie storica
        se il gruppo non esiste lo crea, se non riesce a recuperarlo restituisce indice -1

        @return groupIndex , int 0..n  (-1: non esiste)
        """
        groupindex = -1
        legend = iface.legendInterface()
        groupname = "Serie Storica Grafici"
        groupslist = legend.groups()
        if groupname in groupslist:
            #legend.removeGroup(groupslist.index(groupname))
            groupindex = groupslist.index(groupname)
            LOGGER.debug("getGroupIndexSerieStoricaGrafici trovato groupindex: %d " % (groupindex))
        else:
            # http://www.lutraconsulting.co.uk/blog/2014/07/06/qgis-layer-tree-api-part-1/
            root = QgsProject.instance().layerTreeRoot()
            groupindex = 0
            newgroup = root.insertGroup(groupindex, groupname)  # @UnusedVariable
            #groupindex = legend.addGroup(groupname, expand=True, parent=root)  # parent=0)
            legend.setGroupVisible(groupindex, False)
            LOGGER.debug("getGroupIndexSerieStoricaGrafici non trovato groupindex ma aggiunto: %d " % (groupindex))
        pass
        return groupindex


class Cursors(object):
    def __init__(self):
        pass

    @staticmethod
    def identify_cursor():
        cursor = QCursor(QPixmap(["16 16 3 1",
                                  "# c None",
                                  "a c #000000",
                                  ". c #ffffff",
                                  ".###########..##",
                                  "...########.aa.#",
                                  ".aa..######.aa.#",
                                  "#.aaa..#####..##",
                                  "#.aaaaa..##.aa.#",
                                  "##.aaaaaa...aa.#",
                                  "##.aaaaaa...aa.#",
                                  "##.aaaaa.##.aa.#",
                                  "###.aaaaa.#.aa.#",
                                  "###.aa.aaa..aa.#",
                                  "####..#..aa.aa.#",
                                  "####.####.aa.a.#",
                                  "##########.aa..#",
                                  "###########.aa..",
                                  "############.a.#",
                                  "#############.##"]))
        return cursor

    @staticmethod
    def graph_identify_cursor():
        cursor = QCursor(QPixmap(["16 16 3 1",
                                  "# c None",
                                  "a c #ff0000",
                                  ". c #ffffff",
                                  ".###########..##",
                                  "...########.aa.#",
                                  ".aa..######.aa.#",
                                  "#.aaa..#####..##",
                                  "#.aaaaa..##.aa.#",
                                  "##.aaaaaa...aa.#",
                                  "##.aaaaaa...aa.#",
                                  "##.aaaaa.##.aa.#",
                                  "###.aaaaa.#.aa.#",
                                  "###.aa.aaa..aa.#",
                                  "####..#..aa.aa.#",
                                  "####.####.aa.a.#",
                                  "##########.aa..#",
                                  "###########.aa..",
                                  "############.a.#",
                                  "#############.##"]))
        return cursor

    @staticmethod
    def chart_identify_cursor():
        cursor = QCursor(QPixmap(["16 16 3 1",
                                  "      c None",
                                  ".     c #ff0000",
                                  "+     c #faed55",
                                  "                ",
                                  "       +.+      ",
                                  "      ++.++     ",
                                  "     +.....+    ",
                                  "    +.  .  .+   ",
                                  "   +.   .   .+  ",
                                  "  +.    .    .+ ",
                                  " ++.    .    .++",
                                  " ... ...+... ...",
                                  " ++.    .    .++",
                                  "  +.    .    .+ ",
                                  "   +.   .   .+  ",
                                  "   ++.  .  .+   ",
                                  "    ++.....+    ",
                                  "      ++.++     ",
                                  "       +.+      "]))
        return cursor

    @staticmethod
    def old_graph_identify_cursor():
        cursor = QCursor(QPixmap(["16 16 3 1",
                                  "      c None",
                                  ".     c #5592fa",
                                  "+     c #faed55",
                                  "                ",
                                  "       +.+      ",
                                  "      ++.++     ",
                                  "     +.....+    ",
                                  "    +.  .  .+   ",
                                  "   +.   .   .+  ",
                                  "  +.    .    .+ ",
                                  " ++.    .    .++",
                                  " ... ...+... ...",
                                  " ++.    .    .++",
                                  "  +.    .    .+ ",
                                  "   +.   .   .+  ",
                                  "   ++.  .  .+   ",
                                  "    ++.....+    ",
                                  "      ++.++     ",
                                  "       +.+      "]))
        return cursor
