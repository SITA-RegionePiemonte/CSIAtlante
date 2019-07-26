# not updated, in windows we use makefile_experimental.bat
# TODO: win gnu make

ECLIPSE_WORKSPACE = D:\Sviluppi\python\workspace
ECLIPSE_PROJECT = CSIAtlante
QGISPLUGINSPATH = C:\Users\dragonfly\.qgis\python\plugins
PLUGINNAME = CSIAtlante

UICPATH = C:\OSGeo4W\apps\Python27\Lib\site-packages\PyQt4\uic\pyuic.py
UIC = C:\OSGeo4W\bin\python.exe $(UICPATH)
RCC = C:\OSGeo4W\bin\pyrcc4
MKDIR2 = C:\mkdir2.bat

QRCPYFILES := $(patsubst %.qrc,%.py,$(wildcard *.qrc))
UIPYFILES := $(patsubst %.ui,%.py,$(wildcard *.ui))

all: build

build: $(QRCPYFILES) $(UIPYFILES)

%.py: %.qrc
	$(RCC) -o $(basename $@)_rc$(suffix $@) $<
	
%.py: %.ui
	$(UIC) -o $@ $<


install:
    $(MKDIR2) "$(QGISPLUGINSPATH)\$(PLUGINNAME)"
    copy metadata.txt "$(QGISPLUGINSPATH)\$(PLUGINNAME)"
    copy __init__.py "$(QGISPLUGINSPATH)\$(PLUGINNAME)"
    copy resources_rc.py "$(QGISPLUGINSPATH)\$(PLUGINNAME)"
    copy ui_csiatlante.py "$(QGISPLUGINSPATH)\$(PLUGINNAME)"

#    copy icon.png "$(QGISPLUGINSPATH)\$(PLUGINNAME)"
    copy csiatlante.py "$(QGISPLUGINSPATH)\$(PLUGINNAME)"
    copy csiatlantedialog.py "$(QGISPLUGINSPATH)\$(PLUGINNAME)"
    copy LUtils.py "$(QGISPLUGINSPATH)\$(PLUGINNAME)"
	copy wmstree.py "$(QGISPLUGINSPATH)\$(PLUGINNAME)"
	
	copy pyogr "$(QGISPLUGINSPATH)\$(PLUGINNAME)"


clean:
	del resources_rc.py
	del ui_csiatlante.py
	del *.pyc
    
test:
	echo "it works!"