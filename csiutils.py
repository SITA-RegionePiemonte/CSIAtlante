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

from PyQt4.QtGui import *   # @UnusedWildImport
from PyQt4.QtCore import *   # @UnusedWildImport
from qgis.core import QGis  # @UnusedImport
import json
import os
import re
import urllib
import urllib2


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


def GetGenericJSONObj(url, **kwargs):
    """
    Restituisce un json ricavandolo via http da un web service.

    @param url: url del servizio es: http://osgis.csi.it/servizio.php
    @param kwargs: keyworded variable length of arguments
    """
    jsonObj = json.loads('{}')
    query_args = {}
    if kwargs is not None:
        query_args = kwargs
#         for key, value in kwargs.iteritems():
#            query_args.add(key, value)
    else:
        return None

    try:
        encoded_args = urllib.urlencode(query_args)
        filehandle = urllib2.urlopen(url, encoded_args)
    except urllib2.HTTPError as e:
        if (e.code == 500):
            #tx = "mod_fcgid: HTTP request length (so far) exceeds MaxRequestLen"
            msg = "HTTPError %s \nInternal Server Error\n%s" % (e.code, e.read())
            QMessageBox.information(None, "GetGenericJSONObj", msg)
    except urllib2.URLError as e:
        msg = 'Failed to reach server.\nReason:\n%s' % (str(e.reason))
        QMessageBox.information(None, "GetGenericJSONObj", msg)
    finally:
        if (filehandle != None):
            lines = filehandle.readlines()
            filehandle.close()
            if lines[0][0] == '<':
                return None
            rows = '\n'.join(lines)

            # log per DEBUG
            s = QSettings()
            REMOTE_DBG = s.value(''.join([PROJECT_NAME, "/debug"]), False, type=bool)
            if REMOTE_DBG:
                #import inspect
                #logfile = os.path.abspath(os.path.join(os.path.dirname(inspect.getfile(csiatlanteclouddialog)), ''.join(['debug_json_', 'generic', '.log'])))
                logfile = ''.join([QFileInfo(os.path.realpath(__file__)).path(), '/', 'debug_json_', 'generic', '.log'])
                wlog = open(logfile, "wt")
                wlog.write(rows)
                wlog.close()
                pass
                #QMessageBox.information(None, "GetGenericJSONObj", "scritto C:\Users\xxx\.qgis2\python\plugins\CSIAtlanteCloud\debug_json_generic.log")

            jsonObj = json.loads(rows)
    pass
    return jsonObj


def RemoveCR(strlist):
    """
    Rimuove Carriage Return '\n' in tutti gli elementi di una lista di stringhe
    @return: list
    """
    a = []
    for t in strlist:
        if t[-1] == '\n':
            a.append(t[:-1])
        else:
            a.append(t)
    return a


def RemoveFirstElement(alist):
    """
    Rimuove primo elemento di una lista
    @return: list
    """
    first = alist[0]
    try:
        alist.remove(first)
    except ValueError:
        pass
    return alist


def getCompactXMLStringFromQGSFile(qgsfile):
    """
    Restituisce da un file QGS una stringa di testo in puro XML :
        - senza spazi iniziali e finali
        - senza prima riga <!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
    """
    with open(qgsfile, 'r') as f:
        lines = f.readlines()
        # rimuove prima linea if string.find(lines[0], 'DOCTYPE')<0 :
        del lines[0]
        clean_lines = [l.strip() for l in lines if l.strip()]

    # genera e restituisce stringa
    purexml = ''.join(clean_lines)

    # ------------------------------------------------------
    #purexml = purexml.rstrip('\n')
    # # unescape HTML Entities, es: "&lt;" diventa "<"
    #purexml = unescapeHTMLEntities(purexml)
    # ------------------------------------------------------
    return purexml


def escapeLeftRightDirectionSymbol(text):
    """ Escape mirato di alcuni valori
        <property key="labeling/rightDirectionSymbol" value=">"/>" diventa: value="&gt;"
        <property key="labeling/leftDirectionSymbol" value="<"/>" diventa: value="&lt;"
    """
    text = text.replace("value=\">\"", "value=\"&gt;\"")
    text = text.replace("value=\"<\"", "value=\"&lt;\"")
    return text


def getXMLStringFromQGSFile(qgsfile):
    """
    Restituisce da un file QGS una stringa di testo in XML
    senza prima riga <!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
    """
    with open(qgsfile, 'r') as f:
        lines = f.readlines()
        # rimuove prima linea if string.find(lines[0], 'DOCTYPE')<0 :
        del lines[0]

    # genera e restituisce stringa
    xml = ''.join(lines)
    #purexml = purexml.rstrip('\n')
    return xml


def getEncodedDictionary(in_dict):
    """
    Prende in input un dictionary con potenziali valori unicode e string
    e restituisce un dictionary con valori encoded in UTF-8
    """
    out_dict = {}
    for k, v in in_dict.iteritems():
        if isinstance(v, unicode):
            v = v.encode('utf8')
        elif isinstance(v, str):
            # Must be encoded in UTF-8
            v.decode('utf8')
        out_dict[k] = v
    return out_dict


def getEncodeNonAscii(b):
    """
    Converte in una stringa ascii utilizzabile in urllib
    in input prende stringa url o parte di url con caratteri non ascii
    @param b : stringa url o parte di url con caratteri non ascii
    @return: encoded
    """
    return re.sub('[\x80-\xFF]', lambda c: '%%%02x' % ord(c.group(0)), b)


class Cursor:
    @classmethod
    def Hourglass(cls):
        cursor = QCursor(Qt.WaitCursor)
        QApplication.instance().setOverrideCursor(cursor)
#        # log per DEBUG
#         s = QSettings()
#         REMOTE_DBG = s.value(''.join([PROJECT_NAME, "/debug"]), False, type=bool)
#         if REMOTE_DBG:
#             from time import gmtime, strftime
#             strnow = strftime("%Y-%m-%d %H:%M:%S", gmtime())
#             logfile = ''.join([QFileInfo(os.path.realpath(__file__)).path(), '/', 'debug_csiutils', '.log'])
#             fw = open(logfile, 'a')
#             fw.write(''.join([strnow, ' : ', 'Cursor :: ', 'Cursor.Hourglass', '\n']))
#             fw.flush()
#             fw.close()

    @classmethod
    def Arrow(cls):
        cursor = QCursor(Qt.ArrowCursor)
        QApplication.instance().setOverrideCursor(cursor)
#         # log per DEBUG
#         s = QSettings()
#         REMOTE_DBG = s.value(''.join([PROJECT_NAME, "/debug"]), False, type=bool)
#         if REMOTE_DBG:
#             from time import gmtime, strftime
#             strnow = strftime("%Y-%m-%d %H:%M:%S", gmtime())
#             logfile = ''.join([QFileInfo(os.path.realpath(__file__)).path(), '/', 'debug_csiutils', '.log'])
#             fw = open(logfile, 'a')
#             fw.write(''.join([strnow, ' : ', 'Cursor :: ', 'Cursor.Arrow', '\n']))
#             fw.write('\n')
#             fw.flush()
#             fw.close()

    @classmethod
    def Restore(cls):
        QApplication.instance().restoreOverrideCursor()

    @classmethod
    def EmptyStack(cls):
        while QApplication.instance().overrideCursor() > 0:
            QApplication.instance().restoreOverrideCursor()
#
#         REMOTE_DBG = s.value(''.join([PROJECT_NAME, "/debug"]), False, type=bool)
#         if REMOTE_DBG:
#             from time import gmtime, strftime
#             strnow = strftime("%Y-%m-%d %H:%M:%S", gmtime())
#             logfile = ''.join([QFileInfo(os.path.realpath(__file__)).path(), '/', 'debug_csiutils', '.log'])
#             fw = open(logfile, 'a')
#         while QApplication.instance().overrideCursor() > 0:
#             if REMOTE_DBG:
#                 strnow = strftime("%Y-%m-%d %H:%M:%S", gmtime())
#                 currentstack = QApplication.instance().overrideCursor()
#                 fw.write(''.join([strnow, ' : ''AggiornaElenco :: ', 'overrideCursor(): ', str(currentstack), '\n']))
#                 fw.flush()
#             QApplication.instance().restoreOverrideCursor()
#         if REMOTE_DBG:
#             fw.close()

    @classmethod
    def Custom(cls):
        cursor = QCursor(QPixmap(["16 16 3 1",
                                  "      c None",
                                  ".     c #FF0000",
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
        #cursor.setShape(0)
        QApplication.instance().setOverrideCursor(cursor)


# class LogFile:
#     @classmethod
#     def deleteFile(cls):
#         fw = open(LogFile.fileName(), "w")
#         fw.close()
# 
#     @classmethod
#     def fileName(cls):
#         return 'd:/csiatlante.log'
# 
#     @classmethod
#     def write(cls, txt, append=True):
#         if append:
#             fw = open(LogFile.fileName(), "a+")
#         else:
#             fw = open(LogFile.fileName(), "w")
#         try:
#             fw.write(txt)
#             fw.write("\n")
#             fw.flush()
#         finally:
#             fw.close()
# --- END COMMON ---
