#/***************************************************************************
# NapkinGIS plugin
# Publish your projects to NapkinGIS
# ***************************************************************************/

# WARNING: Every line in Makefile recipe must begin with a tab character. Don't
#          try to convert them spaces !

QGISDIR = .qgis2
NAPKINGIS_BUILDDIR = build
PLUGINNAME = napkingis-prepare
PY_FILES = webgisplugin.py wizard.py project.py topics.py confirmation.py publish.py utils.py __init__.py
EXTRAS = icon.png metadata.txt
UI_FILES = publish_dialog.ui
RESOURCE_FILES = resources_rc.py
ZIPNAME = napkingis-prepare-plugin
VERSION := $(shell grep version metadata.txt | awk -F "=" '{print $$2}')


default: compile

compile: $(RESOURCE_FILES)

%_rc.py : %.qrc
	pyrcc5 -o $*_rc.py  $<

# The deploy target only works on unix like operating system where the Python
# plugin directory is located at "$HOME/$(QGISDIR)/python/plugins"
deploy: compile
	mkdir -p $(HOME)/$(QGISDIR)/python/plugins/$(PLUGINNAME)
	cp -vf $(PY_FILES) $(HOME)/$(QGISDIR)/python/plugins/$(PLUGINNAME)
	cp -vf $(UI_FILES) $(HOME)/$(QGISDIR)/python/plugins/$(PLUGINNAME)
	cp -vf $(RESOURCE_FILES) $(HOME)/$(QGISDIR)/python/plugins/$(PLUGINNAME)
	cp -vf $(EXTRAS) $(HOME)/$(QGISDIR)/python/plugins/$(PLUGINNAME)

# The derase deletes deployed plugin
derase:
	rm -Rf $(HOME)/$(QGISDIR)/python/plugins/$(PLUGINNAME)

# The zip target creates a zip file with the deployed content.
zip:
	rm -f $(ZIPNAME)*.zip
	rm -Rf $(NAPKINGIS_BUILDDIR)
	mkdir -p $(NAPKINGIS_BUILDDIR)/$(PLUGINNAME)
	cp -vf $(PY_FILES) $(NAPKINGIS_BUILDDIR)/$(PLUGINNAME)
	cp -vf $(UI_FILES) $(NAPKINGIS_BUILDDIR)/$(PLUGINNAME)
	cp -vf $(RESOURCE_FILES) $(NAPKINGIS_BUILDDIR)/$(PLUGINNAME)
	cp -vf $(EXTRAS) $(NAPKINGIS_BUILDDIR)/$(PLUGINNAME)
	cd $(NAPKINGIS_BUILDDIR); zip -9r $(CURDIR)/$(ZIPNAME)-$(VERSION).zip $(PLUGINNAME)
	rm -Rf $(NAPKINGIS_BUILDDIR)

clean:
	rm $(RESOURCE_FILES)
