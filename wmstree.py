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

 Date                 : 2015-10-18
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

import urllib.request, urllib.error, urllib.parse
#import xml.etree.ElementTree as ET
"""
The cElementTree module is a C implementation of the ElementTree API,
optimized for fast parsing and low memory use.
"""
import xml.etree.cElementTree as ET
from qgis.core import QgsMessageLog
#2to3 import cStringIO
import io
import time
from qgis.PyQt.QtCore import QSettings
from qgis.PyQt.QtCore import QUrl
from qgis.PyQt.QtCore import QObject
from qgis.PyQt.QtCore import QFileInfo
from qgis.PyQt.QtWidgets import QMessageBox
from qgis.PyQt.QtWidgets import QApplication
from qgis.PyQt.QtWebKitWidgets import QWebView
from qgis.PyQt import QtNetwork
import os
import sys  # @UnusedImport
#sys.path.append("C:\\OSGeo4W\\apps\\qgis\\plugins")

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


class WMSLegend:
    def __init__(self, element):
        self.format = element.find('Format').text
        onl = element.find('OnlineResource')
        for k, v in onl.items():
            if k.find('href') > 0:
                self.url = v


class WMSLayer:
    """
    Classe che gestisce un oggetto wmslayer nel tree:
    le proprieta' name e title sono inizializzati con '<has_no_Name>' e '<has_no_Title>'
    che puo' essere usata come discriminante per riconoscere se puo' essere fatta una request GetMap
    rif:
    OpenGIS Web Map Service (WMS) Implementation Specification
    http://www.opengeospatial.org/standards/wms

    @param parentTree
    @param parentLayer
    @param element
    """
    def __init__(self, parentTree, parentLayer, element):
        self.parentTree = parentTree
        self.parentLayer = parentLayer
        self.name = u'<has_no_Name>'
        self.title = u'<has_no_Title>'

        if (element.find('Name') != None):
            self.name = element.find('Name').text
        if (element.find('Title') != None):
            self.title = element.find('Title').text

        self.srs = []
        try:
            for elm in element.findall('SRS'):
                tx = elm.text
                if not tx in self.srs:
                    self.srs.append(tx)
        except:
            pass

        if len(self.srs) == 0:
            try:
                for elm in element.findall('CRS'):
                    tx = elm.text
                    if not tx in self.srs:
                        self.srs.append(tx)
            except:
                pass

        self.style = None
        try:
            self.style = element.find('./Style/Name').text
        except:
            pass

        self.legend = None
        try:
            lg = element.find('./Style/LegendURL')
            self.legend = WMSLegend(lg)
        except:
            pass

        self.metadataurl = None
        try:
            onl = element.find('./MetadataURL/OnlineResource')
            for k, v in onl.items():
                if k.find('href') > 0:
                    self.metadataurl = v
        except:
            self.metadataurl = None

        self.format = 'image/png'
        self.layers = None

        alayers = element.findall('./Layer')
        if len(alayers) > 0:
            self.layers = []
            for layer in alayers:
                self.layers.append(WMSLayer(self.parentTree, self, layer))

    def getMetadataURL(self):
        itm = self
        while itm != None:
            if itm.metadataurl != None and itm.metadataurl != '':
                return itm.metadataurl
            itm = itm.parentLayer
        return self.parentTree.metadataurl

    def __isNameInList(self, names):
        if names is None:
            return True
        if self.name in names:
            return True
        if self.parentLayer != None:
            return self.parentLayer.__isNameInList(names)
        # if self.parentTree.name in names:
        #    return True
        return False

    def GetLegendHTML(self, filterLayerList):
        s = ''
        if self.legend != None:
            if self.__isNameInList(filterLayerList) == True:
                if self.metadataurl != None:
                    s = s + "<a href='%s'><img src='%s'></a><br>\n" % (self.metadataurl, self.legend.url)
                else:
                    s = s + "<img src='%s'><br>\n" % (self.legend.url)
        if self.layers != None:
            for l in self.layers:
                s = s + l.GetLegendHTML(filterLayerList)
        return s


class WMSTree:
    def __init__(self, name, urlCapabilities, category='', metadataurl=None):
        self.name = name
        # self.url=urlCapabilities
        self.layers = []
        self.aformat = []
        self.category = category
        self.metadataurl = metadataurl
        self.__ParseCapabilities(urlCapabilities)
        #self.calldll(urlCapabilities)

#     def calldll(self, urlcap):
#         from ctypes import *  # SyntaxWarning: import * only allowed at module level
#         lib = cdll.LoadLibrary("C:\\OSGeo4W\\apps\\qgis\\plugins\\wmsprovider.dll")
#         #prov = wmsDll.QgsWmsProvider(urlcap)

    def getMetadataURL(self):
        itm = self
        if itm.metadataurl != None and itm.metadataurl != '':
            return itm.metadataurl
        else:
            return ''

    def __remove_namespaces(self, doc):
        # Porting QGIS 2.0
        # for elem in doc.getiterator():
        # PendingDeprecationWarning: This method will be removed in future versions.
        # Use 'tree.iter()' or 'list(tree.iter())' instead.
        for elem in doc.iter():
            a = elem.tag
            if a.startswith('{'):
                elem.tag = a[a.index('}') + 1:]

    def __ParseCapabilities(self, urlCap):

        xmlContent = ''
        xmlData = b''
        
        scheme, netloc, path, query_string, fragment = urllib.parse.urlsplit(urlCap)
        url = urllib.parse.urlunsplit((scheme, netloc, path, "", fragment))
        
        encoded_args = query_string    
        byte_encoded_args = encoded_args.encode('utf-8')
        
        try:
            req = urllib.request.Request(url, byte_encoded_args)
            with urllib.request.urlopen(url) as response:
               xmlData = response.read()

        except Exception as ex:
            self.name = self.name + ' - ' + str(ex)
            QgsMessageLog.logMessage('filehandle read error: ' + str(ex), 'wmstree')
            QgsMessageLog.logMessage(urlCap, 'wmstree')
            return
                    
#         /************ CsiAtlante 1.0.0 ****************************************
#         xmlContent = ''
#         try:
#             #csiutils.LogFile.write("\n###----------------------------------------------------", True)
#             #csiutils.LogFile.write("urllib.urlopen %s\n" % urlCap, True)
#             filehandle = urllib.request.urlopen(urlCap)
#             try:
#                 xmlContent = filehandle.read()
#             finally:
#                 filehandle.close()
#             #csiutils.LogFile.write(xmlContent, True)
#         except Exception as ex:
#             self.name = self.name + ' - ' + str(ex)
#             #csiutils.LogFile.write('###filehandle read error: ' + str(ex), True)
#             QgsMessageLog.logMessage('filehandle read error: ' + str(ex), 'wmstree')
#             QgsMessageLog.logMessage(urlCap, 'wmstree')
#             return
#         ***************************************************************************/

#         /************ CsiAtlante 1.0.03 ****************************************
#         try:
#             scrape = ScrapeCapabilities(urlCap)
#         #try:
#             #scrape.load(urlCap)
#             #time.sleep(1)
#             #scrape.exit()
#
#         except Exception as ex:
#             self.name = self.name + ' - ' + str(ex)
#             QgsMessageLog.logMessage('scrape capabilities error: ' + str(ex), 'wmstree')
#             QgsMessageLog.logMessage(urlCap, 'wmstree')
#             return
#
#         xmlContent = scrape.getXmlContent()
#         /***************************************************************************

#         /************ CsiAtlante future ****************************************
#         xmlContent = '<xml></xml>'
#         try:
#             pass
#             webView = QWebView(None)
#             webView.load(QUrl(urlCap))
#             page = webView.page()
#             frame = page.currentFrame()   ########### !!!!!!!!!!!!!!!!!!!!!!!!!   <<<<<<<<<<<<<<<<<<<<<< mainFrame()
#             #doc = frame.documentElement()
#             #uxml = frame.toPlainText()
#             uxml = frame.toHtml()
#             QgsMessageLog.logMessage('scrape capabilities frame.toHtml(): ' + uxml, 'wmstree')
#             #uxml = uxml.replace('\n', '')
#             xmlContent = uxml
#
#             reqUrl = frame.requestedUrl()
#             reqUrl = reqUrl.toString()
#             QgsMessageLog.logMessage('requested url: ' + reqUrl, 'wmstree')
#             #documentElement = page.currentFrame().documentElement()
#
#             if REMOTE_DBG:
#                 fw = open("C:\\temp\\parsecapabilities.txt", 'w')  # , encoding='utf-8')
#                 fw.write(xmlContent.decode('utf-8'))
#                 fw.flush()
#                 fw.close()
#
#         except Exception as ex:
#             self.name = self.name + ' - ' + str(ex)
#             QgsMessageLog.logMessage('scrape capabilities error: ' + str(ex), 'wmstree')
#             QgsMessageLog.logMessage(urlCap, 'wmstree')
#             return
#         /***************************************************************************

        #logstep = 1
        #csiutils.LogFile.write("\nlogstep = %s\n" % (logstep), True)
        try:
            xmlContent = xmlData.decode('utf-8')
            tval = io.StringIO(xmlContent)
            #---wrapper = io.TextIOWrapper(xmlData, encoding='utf-8')
            #---tval = io.StringIO(wrapper.read())
            xmltree = ET.parse(tval)
            self.__remove_namespaces(xmltree)

        except Exception as ex:
            #csiutils.LogFile.write("\nexception step %d: %s\nurlCap: %s\n\nxmlContent \n" % (logstep, ex, urlCap), True)
            #csiutils.LogFile.write(xmlContent, True)
            #csiutils.LogFile.write("\n\n", True)
            QgsMessageLog.logMessage("xml format error [%s] " % urlCap, 'wmstree')
            QgsMessageLog.logMessage(str(ex), 'wmstree')

            return

        msg = ['ParseCapabilities try...']
        try:
            captree = xmltree.find('Capability')
            if captree is None:
                #logstep = 5
                #csiutils.LogFile.write("\nlogstep = %s\n" % (logstep), True)
                msg.append('\nTag Capability non trovato')
                #QMessageBox.information(None, "wmstree::__ParseCapabilities", "DEBUG: xmltree\n" + str(xmltree))

            else:
                #logstep = 5.5
                #csiutils.LogFile.write("\nlogstep = %s\n" % (logstep), True)
                layertree = captree.findall('./Layer')
                if layertree is None:
                    #logstep = 6
                    #csiutils.LogFile.write("\nlogstep = %s\n" % (logstep), True)
                    msg.append('\nTag Layer non trovato')

                if len(layertree) == 0:
                    #logstep = 7
                    #csiutils.LogFile.write("\nlogstep = %s\n" % (logstep), True)
                    msg.append('\nTag Layer trovato ma di lunghezza 0')
                else:
                    for layer in layertree:
                        try:
                            self.layers.append(WMSLayer(self, None, layer))
                        except:
                            msg.append(str(sys.exc_info()[0]))

                formattree = captree.findall('./Request/GetMap/Format')
                if formattree is None:
                    msg.append('\nTag ./Request/GetMap/Format non trovato')
                else:
                    self.aformat = [t.text for t in formattree]

        except Exception as ex:
            msg.append(str(ex))

        if len(msg) > 0:
            s = urlCap + '\n' + '\n'.join(msg)
            QgsMessageLog.logMessage(s, 'wmstree')

    def GetLegendHTML(self, filterLayerList=None):
        s = "<html><body>\n"
        for l in self.layers[:]:
            s = s + l.GetLegendHTML(filterLayerList)
        s = s + "</body></html>"
        return s

#     def __ParseCapabilitiesWebKit(self, urlCap):
#         xmlContent = ''
#         uxml = u''
#         try:
#             #from PyQt4.QtWebKit import QWebView
#             #from PyQt4.QtCore import QUrl
# 
#             webView = QWebView(None)
#             page = webView.page()
#             proxy = self.getProxyFromQgsSettings()
#             if (proxy):
#                 networkAccessManager = page.networkAccessManager()  # QtNetwork.QNetworkAccessManager()
#                 networkAccessManager.setProxy(proxy)
#             else:
#                 # @TODO: log & manage
#                 pass
# 
#             webView.load(QUrl(urlCap))
#             frame = page.mainFrame()
#             uxml = frame.toHtml()
#             uxml = uxml.replace('\n', '')
# 
#             xmlContent = str(uxml)
# 
#             if REMOTE_DBG:
#                 fw = open("C:\\temp\\parsecapabilities.txt", 'w')  # , encoding='utf-8')
#                 fw.write(urlCap)
#                 fw.write('----------------------')
#                 fw.write(xmlContent)
#                 fw.flush()
#                 fw.close()
# 
#             #csiutils.LogFile.write(xmlContent, True)
#         except Exception as ex:
#             self.name = self.name + ' - ' + str(ex)
#             #csiutils.LogFile.write('###filehandle read error: ' + str(ex), True)
#             QgsMessageLog.logMessage('filehandle read error: ' + str(ex), 'wmstree')
#             QgsMessageLog.logMessage(urlCap, 'wmstree')
#             return
# 
#         try:
#             tval = cStringIO.StringIO(xmlContent)
#             xmltree = ET.parse(tval)
#             self.__remove_namespaces(xmltree)
# 
#         except Exception as ex:
#             #csiutils.LogFile.write("\nexception step %d: %s\nurlCap: %s\n\nxmlContent \n" % (logstep, ex, urlCap), True)
#             #csiutils.LogFile.write(xmlContent, True)
#             #csiutils.LogFile.write("\n\n", True)
#             QgsMessageLog.logMessage("xml format error [%s] " % urlCap, 'wmstree')
#             QgsMessageLog.logMessage(str(ex), 'wmstree')
# 
#             return
# 
#         msg = ['wmstree.__ParseCapabilitiesWebKit try\n']
#         try:
#             captree = xmltree.find('Capability')
#             if captree == None:
#                 #logstep = 5
#                 #csiutils.LogFile.write("\nlogstep = %s\n" % (logstep), True)
#                 msg.append('Tag Capability non trovato')
#             else:
#                 #logstep = 5.5
#                 #csiutils.LogFile.write("\nlogstep = %s\n" % (logstep), True)
#                 layertree = captree.findall('./Layer')
#                 if layertree == None:
#                     #logstep = 6
#                     #csiutils.LogFile.write("\nlogstep = %s\n" % (logstep), True)
#                     msg.append('Tag Layer non trovato')
# 
#                 if len(layertree) == 0:
#                     #logstep = 7
#                     #csiutils.LogFile.write("\nlogstep = %s\n" % (logstep), True)
#                     msg.append('Tag Layer trovato ma di lunghezza 0')
#                 else:
#                     for layer in layertree:
#                         try:
#                             self.layers.append(WMSLayer(self, None, layer))
#                         except:
#                             msg.append(str(sys.exc_info()[0]))
# 
#                 formattree = captree.findall('./Request/GetMap/Format')
#                 if formattree == None:
#                     msg.append('Tag ./Request/GetMap/Format non trovato')
#                 else:
#                     self.aformat = [t.text for t in formattree]
# 
#         except Exception as ex:
#             msg.append(str(ex))
# 
#         if len(msg) > 0:
#             s = urlCap + '\n' + '\n'.join(msg)
#             QgsMessageLog.logMessage(s, 'wmstree')
# 
#     def getProxyFromQgsSettings(self):
#         #from PyQt4 import QtNetwork
#         proxy = QtNetwork.QNetworkProxy()
# 
#         # getting proxy from qgis options settings
#         # @TODO: externalize
#         s = QSettings()
#         proxyEnabled = s.value("proxy/proxyEnabled", "")
#         proxyType = s.value("proxy/proxyType", "")
#         proxyHost = s.value("proxy/proxyHost", "")
#         proxyPort = s.value("proxy/proxyPort", "")
#         proxyUser = s.value("proxy/proxyUser", "")
#         proxyPassword = s.value("proxy/proxyPassword", "")
#         if proxyEnabled == "true":    # test if there are proxy settings
#             if proxyType == "DefaultProxy":
#                 proxy.setType(QtNetwork.QNetworkProxy.DefaultProxy)
#             elif proxyType == "Socks5Proxy":
#                 proxy.setType(QtNetwork.QNetworkProxy.Socks5Proxy)
#             elif proxyType == "HttpProxy":
#                 proxy.setType(QtNetwork.QNetworkProxy.HttpProxy)
#             elif proxyType == "HttpCachingProxy":
#                 proxy.setType(QtNetwork.QNetworkProxy.HttpCachingProxy)
#             elif proxyType == "FtpCachingProxy":
#                 proxy.setType(QtNetwork.QNetworkProxy.FtpCachingProxy)
#             proxy.setHostName(proxyHost)
#             proxy.setPort(int(proxyPort))
#             proxy.setUser(proxyUser)
#             proxy.setPassword(proxyPassword)
#         return proxy


class ScrapeCapabilities():
    """
    Scraping WMS Capabilities with QWebElement
    """
    def __init__(self, url):
        #self.url = url
        self.xmlContent = ''
        self.webView = QWebView()
        self.page = self.webView.page()
        self.proxy = self.getProxy()
        if (self.proxy):
            networkAccessManager = self.page.networkAccessManager()
            networkAccessManager.setProxy(self.proxy)
        else:
            # @TODO: log & manage
            pass
        # Connect our loadFinished method to the loadFinished signal of this new QWebView.
        self.webView.loadFinished.connect(self.loadFinished)
        # Old Style
        #QObject.connect(self.webView, SIGNAL("loadFinished(bool)"), self.loadFinished)
        #self.page.frameCreated.connect(self.onFrame)
        self.load(url)

    def load(self, url):
        # In the __init__ we stored a QWebView instance into self.webView so
        # we can load a url into it. It needs a QUrl instance though.
        self.webView.load(QUrl(url))
        # e.c : richiamo qui di brutto perche' se no l'evento non viene scatenato!!!!!!
        #self.loadFinished()

    def onFrame(self, val):
        #QMessageBox.information(None, "ScrapeCapabilities::onFrame", "DEBUG: 'Frame Created:"+ val.frameName())
        pass

    def loadStarted(self):
        QMessageBox.information(None, "ScrapeCapabilities::loadStarted", "DEBUG: passo da qui!!!")
        pass

    def loadFinished(self):
        # We landed here because the load is finished. Now, load the root document element.
        #QMessageBox.information(None, "ScrapeCapabilities::loadFinished", "DEBUG: passo da qui!!!")
        #documentElement = self.webView.page().currentFrame().documentElement()
        #QMessageBox.information(None, "ScrapeCapabilities::loadFinished", "DEBUG: \n" + documentElement.toOuterXml())
        pass

        frame = self.page.mainFrame()
        uxml = frame.toHtml()
        uxml = uxml.replace('\n', '')

        self.xmlContent = uxml

#         if REMOTE_DBG:
#             logfile = ''.join([QFileInfo(os.path.realpath(__file__)).path(), '/', 'debug_parsecapabilities', '.log'])
#             wlog = open(logfile, "w")  # , encoding='utf-8')
#             wlog.write(self.xmlContent.decode('utf-8'))
#             wlog.flush()
#             wlog.close()

#         documentElement = self.webView.page().currentFrame().documentElement()
#         # Let's find the search input element.
#         inputSearch = documentElement.findFirst('input[title="Google Search"]')
#         # Print it out.
#         print unicode(inputSearch.toOuterXml())
        # We are inside a QT application and need to terminate that properly.
        #self.exit()

    def exit(self):
        self.webView.loadFinished.disconnect(self.loadFinished)

    def getXmlContent(self):
        return self.xmlContent

    def getProxy(self):
        #from PyQt4 import QtNetwork
        proxy = QtNetwork.QNetworkProxy()

        # getting proxy from qgis options settings
        s = QSettings()
        proxyEnabled = s.value("proxy/proxyEnabled", "")
        proxyType = s.value("proxy/proxyType", "")
        proxyHost = s.value("proxy/proxyHost", "")
        proxyPort = s.value("proxy/proxyPort", "")
        proxyUser = s.value("proxy/proxyUser", "")
        proxyPassword = s.value("proxy/proxyPassword", "")
        if proxyEnabled == "true":    # test if there are proxy settings
            if proxyType == "DefaultProxy":
                proxy.setType(QtNetwork.QNetworkProxy.DefaultProxy)
            elif proxyType == "Socks5Proxy":
                proxy.setType(QtNetwork.QNetworkProxy.Socks5Proxy)
            elif proxyType == "HttpProxy":
                proxy.setType(QtNetwork.QNetworkProxy.HttpProxy)
            elif proxyType == "HttpCachingProxy":
                proxy.setType(QtNetwork.QNetworkProxy.HttpCachingProxy)
            elif proxyType == "FtpCachingProxy":
                proxy.setType(QtNetwork.QNetworkProxy.FtpCachingProxy)
            proxy.setHostName(proxyHost)
            proxy.setPort(int(proxyPort))
            proxy.setUser(proxyUser)
            proxy.setPassword(proxyPassword)
        return proxy
