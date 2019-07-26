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

 Note:

 The content of this file is based on
 - DB Manager by Giuseppe Sucameli <brush.tyler@gmail.com> (GPLv2 license)
 - PG_Manager by Martin Dobias <wonder.sk@gmail.com> (GPLv2 license)

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

from qgis.PyQt import QtCore, QtGui
from qgis.PyQt.QtWidgets import QMessageBox
from qgis.PyQt.QtCore import QSettings

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

#2to3 from qgis.core import (QgsDataSourceURI, QgsVectorLayer)  # @UnusedImport
from qgis.core import QgsVectorLayer

# C:\OSGeo4W\apps\qgis\python\plugins\db_manager
from db_manager.db_plugins.postgis import connector


class CSIPostGisDBConnector(connector.PostGisDBConnector):
    """ Extends PostGisDBConnector
    """
    def __init__(self, uri):
        connector.PostGisDBConnector.__init__(self, uri)

    def connected(self):
        if self.connection is None:
            return False
        else:
            return True

    def close(self):
        if self.connection is not None:
            self.connection.close()

    def getVectorLayer(self, schema, table, keycolumn, where_clause="", legendDescription=None):
        """
        Costruisce un vectorlayer dai parametri in input
        @param schema: schema
        @param table: nome della tabella o vista
        @param keycolumn: eventuale primary key (necessaria per viste, facoltativa per tabelle)
        @param legendDescription: nome del layer in toc (facoltativo)

        @return: vectorlayer
        """
        if legendDescription is None:
            legendDescription = table

        # ricava uri dal connector
        uri = self._uri

        # ricava geometry column dal db
        geometryColumn = self.getGeometryColumn(schema, table)

        # QgsDataSourceURI.setDataSource() has an additional fifth argument to specify the key column
        uri.setDataSource(schema, table, geometryColumn, where_clause, keycolumn)

        # risolvere bug su stringa restituita da uri.uri() in caso di tabella senza geometria
        # eliminare stringa "()" da uri.uri()
        gooduripath = uri.uri().replace('()', '')

        # costruisce vectorlayer
        vlayer = QgsVectorLayer(gooduripath, legendDescription, "postgres")

        return vlayer

    def getGeometryColumn(self, schema, table):
        """
        Ricava il nome della geometry column
        in caso di eccezione assume il default: u""

        @param schema: proprietario
        @param table: nome della tabella o vista

        @return: geometryColumn: nome della geometry column - unicode string
        """
        geometryColumn = u""
        sql = u"select f_geometry_column  from public.geometry_columns where f_table_schema=%s and  f_table_name=%s" % (self.quoteString(schema), self.quoteString(table))
        try:
            c = self._get_cursor()
            self._execute(c, sql)
            res = c.fetchone()[0]
            if res:
                geometryColumn = res
        except:
            geometryColumn = u""

        return geometryColumn
