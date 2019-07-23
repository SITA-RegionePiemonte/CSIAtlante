rem ----------------------------------------------------------------
rem build of qgis plugin from Eclipse IDE
rem 
rem TODO: win gnu make !!!
rem ------------------------------------------------------

SET PLUGIN_NAME=CSIAtlante
SET PLUGINS_PATH=C:\Users\dragonfly\.qgis2\python\plugins
SET ECLIPSE_WORKSPACE=D:\Sviluppi\python\workneon
SET ECLIPSE_PROJECT=CSIAtlante

rem ----------------------------------------------------------------
rem OSGeo4W + QGIS 2.0 + Python settings
rem C:\OSGeo4W\bin\qgis.bat
rem ----------------------------------------------------------------
SET OSGEO4W_ROOT=C:\OSGeo4W
call "%OSGEO4W_ROOT%"\bin\o4w_env.bat

rem SET GDAL_DRIVER_PATH=%OSGEO4W_ROOT%\bin\gdalplugins

path %PATH%;%OSGEO4W_ROOT%\apps\qgis\bin
path %PATH%;%OSGEO4W_ROOT%\apps\Python27\Scripts
path %PATH%;%OSGEO4W_ROOT%\bin

IF DEFINED PYTHONPATH (set PYTHONPATH=%PYTHONPATH%;%OSGEO4W_ROOT%\apps\qgis\python\qgis) ELSE (set PYTHONPATH=%OSGEO4W_ROOT%\apps\qgis\python)
set PYTHONPATH=%PYTHONPATH%;%OSGEO4W_ROOT%\apps\qgis\python\qgis
set PYTHONPATH=%PYTHONPATH%;%OSGEO4W_ROOT%\apps\qgis\python\plugins
set PYTHONPATH=%PYTHONPATH%;%OSGEO4W_ROOT%\apps\Python27
set PYTHONPATH=%PYTHONPATH%;%OSGEO4W_ROOT%\apps\Python27\Lib\site-packages

set QGISPATH=%OSGEO4W_ROOT%\apps\qgis

echo.
echo Delete *.pyc...
cd /d %ECLIPSE_WORKSPACE%\%ECLIPSE_PROJECT%
del *.pyc
cd /d %ECLIPSE_WORKSPACE%\%ECLIPSE_PROJECT%\i18n
del *.pyc

echo.
echo Build resources...
cd /d %ECLIPSE_WORKSPACE%\%ECLIPSE_PROJECT%
call pyrcc4 -o resources_rc.py resources.qrc

echo.
echo Build ui ...
call pyuic4 -o ui_csiatlante.py ui_csiatlante.ui
call pyuic4 -o ui_about.py ui_about.ui
call pyuic4 -o ui_newserviceconnection.py ui_newserviceconnection.ui
call pyuic4 -o ui_newconnection.py ui_newconnection.ui
call pyuic4 -o ui_graphidentify.py ui_graphidentify.ui

echo Delete plugin distribution folder without confirm!
IF EXIST %PLUGINS_PATH%\%PLUGIN_NAME% (rmdir /s /q %PLUGINS_PATH%\%PLUGIN_NAME%)

echo Make plugin dir...
mkdir %PLUGINS_PATH%\%PLUGIN_NAME%

echo Copy files in plugin dir...
copy *.py %PLUGINS_PATH%\%PLUGIN_NAME%
copy *.txt %PLUGINS_PATH%\%PLUGIN_NAME%
copy *.qrc %PLUGINS_PATH%\%PLUGIN_NAME%
copy *.ui %PLUGINS_PATH%\%PLUGIN_NAME%
copy *.json %PLUGINS_PATH%\%PLUGIN_NAME%
copy *.xml %PLUGINS_PATH%\%PLUGIN_NAME%

echo Copy folders in plugin dir...
xcopy /s /e /i /k /y i18n %PLUGINS_PATH%\%PLUGIN_NAME%\i18n
xcopy /s /e /i /k /y icons %PLUGINS_PATH%\%PLUGIN_NAME%\icons
xcopy /s /e /i /k /y cache %PLUGINS_PATH%\%PLUGIN_NAME%\cache
xcopy /s /e /i /k /y graphs %PLUGINS_PATH%\%PLUGIN_NAME%\graphs

rem pause
echo Done!