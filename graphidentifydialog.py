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

#from PyQt4 import QtCore, QtGui, QtNetwork, QtWebKit
from PyQt4.QtCore import *   # @UnusedWildImport
from PyQt4.QtGui import *  # @UnusedWildImport
from PyQt4 import QtNetwork
from PyQt4.QtNetwork import *  # @UnusedWildImport
from PyQt4.QtWebKit import *  # @UnusedWildImport
from qgis.core import *  # @UnusedWildImport
from ui_graphidentify import Ui_GraphIdentifyDialog

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

LOGGER_TAG = 'SGA Tools'


class GraphIdentifyDialog(QDialog, Ui_GraphIdentifyDialog):
    """
    Classe di specializzazione del dialogo ui_identify.ui creato con Qt Designer
    """
    def __init__(self, parent=None, enable_developer=False):
        """
        Estende QDialog
        """
        QDialog.__init__(self, parent)
        self.setupUi(self)

        self.network_proxy = self.getNetworkProxy()
        self.browser = Browser(self.webView, self.network_proxy, enable_developer)

    def getNetworkProxy(self):
        proxy = self.getNetworkProxyFromQgsSettings()
        return proxy

    def getNetworkProxyFromQgsSettings(self):
        """ get (QNetworkProxy) proxy from qgis options settings """
        proxy = QtNetwork.QNetworkProxy()
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


class Browser(object):
    """ classe per fare post di una request tramite qwebkit

    Note:  <input> elements with type="color" are not supported in Internet Explorer or Safari.
    http://trac.webkit.org/wiki/QtWebKitFeatures22#WebDeveloperFeatures
    """
    def __init__(self, web_view, network_proxy=None, enable_developer=False):
        self.web_view = web_view
        self.web_page = self.web_view.page()

        self.network_access_manager = self.web_page.networkAccessManager()
        if (network_proxy):
            self.network_access_manager.setProxy(network_proxy)
        self.network_access_manager.createRequest = self._createRequest
        self.network_access_manager.finished.connect(self._request_finished)

        self.web_page.setNetworkAccessManager(self.network_access_manager)
        self.web_page.loadFinished.connect(self._on_load_finished)
        self.web_page.loadStarted.connect(self._on_load_started)

        if (enable_developer):
            QgsMessageLog.logMessage('Browser::__init__ enable_developer == True', LOGGER_TAG, QgsMessageLog.INFO)
            self._enable_developer()

    def _createRequest(self, operation, request, data):
        reply = QNetworkAccessManager.createRequest(self, operation, request, data)
        return reply

    def _enable_developer(self):
        self.web_view.settings().setAttribute(QWebSettings.PluginsEnabled, True)
        #self.web_view.settings().setAttribute(QWebSettings.AutoLoadImages, True)
        #self.web_view.settings().setAttribute(QWebSettings.LocalStorageEnabled, True)
        self.web_view.settings().setAttribute(QWebSettings.JavascriptEnabled, True)
        self.web_view.settings().setAttribute(QWebSettings.DeveloperExtrasEnabled, True)
        self.web_inspector = QWebInspector()
        self.web_inspector.setPage(self.web_page)
        self.web_inspector.setVisible(True)

    def _request_finished(self, reply):
        """ QNetworkAccessManager has an asynchronous API.
        When the replyFinished slot is called, the parameter it takes is the QNetworkReply object
        containing the downloaded data as well as meta-data
        """
        if not reply.error() == QNetworkReply.NoError:
            QgsMessageLog.logMessage('Browser::_request_finished: %s' % reply.errorString(), LOGGER_TAG, QgsMessageLog.INFO)
        else:
            QgsMessageLog.logMessage('Browser::_request_finished: OK url: %s' % (reply.url()), LOGGER_TAG, QgsMessageLog.INFO)
            QgsMessageLog.logMessage('Browser::_request_finished: OK isFinished: %s' % (reply.isFinished()), LOGGER_TAG, QgsMessageLog.INFO)

    def _on_load_started(self):
        pass

    def _on_load_finished(self):
        pass

    def navigate(self, method, url, data=None, **kwargs):
        method = method.upper()
        if method == '':
            method = 'GET'
        if method == 'GET':
            self.do_get(url, data=data or {}, **kwargs)
        elif method == 'POST':
            self.do_post(url, data=data or {}, **kwargs)
        else:
            QgsMessageLog.logMessage('Browser::navigate: metodo %s sconosciuto' % method, LOGGER_TAG, QgsMessageLog.INFO)

    def do_get(self, url, data, **kwargs):
        """Sends a GET request
        """
        request = self._make_request(url)
        encoded_data = self._urlencode(data)
        self.web_view.load(request, QNetworkAccessManager.GetOperation, encoded_data)

    def do_post(self, url, data, **kwargs):
        """Sends a POST request
        """
        request = self._make_request(url)
        QgsMessageLog.logMessage('Browser::do_post: url : %s' % url, LOGGER_TAG, QgsMessageLog.INFO)

        encoded_data = self._urlencode(data)
        QgsMessageLog.logMessage('Browser::do_post: encoded: %s' % encoded_data, LOGGER_TAG, QgsMessageLog.INFO)

        request.setRawHeader('Content-Type', QByteArray('application/x-www-form-urlencoded'))
        for h in request.rawHeaderList():
            QgsMessageLog.logMessage('Browser::do_post:   %s: %s' % (h, request.rawHeader(h)), LOGGER_TAG, QgsMessageLog.INFO)

        self.web_view.load(request, QNetworkAccessManager.PostOperation, encoded_data)

    def _make_request(self, url):
        request = QNetworkRequest()
        request.setUrl(QUrl(url))
        return request

    def _urlencode(self, data):
        post_params = QUrl()
        for (key, value) in data.items():
            post_params.addQueryItem(key, unicode(value))
        pass
        return post_params.encodedQuery()

    def close(self):
        """Close Browser instance and release resources."""
        if self.network_access_manager:
            del self.network_access_manager
