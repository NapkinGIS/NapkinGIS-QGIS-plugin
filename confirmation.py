# -*- coding: utf-8 -*-
"""
/***************************************************************************
 NapkinGIS plugin
 Publish your projects to NapkinGIS
 ***************************************************************************/
"""

import os
import json
import codecs
import shutil

# Import the PyQt and QGIS libraries
from qgis.core import QgsProject, QgsProviderRegistry, QgsVectorDataProvider, QgsRasterDataProvider, QgsDataSourceUri
from qgis.PyQt.QtWidgets import QWizard, QMessageBox, QApplication
from qgis.PyQt.QtCore import Qt

from .utils import opt_value, create_formatted_tree, Decimal
from .wizard import WizardPage


class ConfirmationPage(WizardPage):

	def __init__(self, plugin, page):
		super(ConfirmationPage, self).__init__(plugin, page)
		page.setButtonText(QWizard.CancelButton, "Close")
		page.setButtonText(QWizard.FinishButton, "Publish")

	def initialize(self):
		self._publish_filename = os.path.splitext( os.path.basename(self.plugin.project.fileName()) )[0]
		self._publish_dir = os.path.join(
			os.path.dirname(self.plugin.project.fileName()),
			self._publish_filename
		)
		self._datasources = {}

		#self.dialog.text_publish_dir.setPlainText(self._publish_dir)
		#self.dialog.button_publish_dir.clicked.connect(self.select_publish_dir)

	#def select_publish_dir(self):
	#	self._publish_dir = str(QFileDialog.getExistingDirectory(self.dialog, "Select Directory"))
	#	if not self._publish_dir:
	#		self._publish_dir = self._publish_dir_default
	#
	#	self.dialog.text_publish_dir.setPlainText(
	#		self._publish_dir
	#	)

	def project_files_short(self):
		# Project files overview
		publish_timestamp = str(self.plugin.metadata['publish_date_unix'])
		project_filename = "{0}_{1}.qgs".format(
			self._publish_filename,
			publish_timestamp
		)
		metadata_filename = "{0}_{1}.meta".format(
			self._publish_filename,
			publish_timestamp
		)

		return project_filename, metadata_filename


	def validate(self):
		return self.copy_published_project()

	def copy_published_project(self):
		metadata = self.plugin.metadata
		project = self.plugin.project
		collected_datafiles = []

		# create publish directory if not exists
		if not os.path.exists(self._publish_dir):
			os.makedirs(self._publish_dir)


		def copy_data_sources():
			messages = [] # error messages

			# collect files to be copied
			#collected_datafiles = []
			for ds in list(self._datasources.values()):
				for dsfile in ds:
					if os.path.exists(dsfile) and os.path.isfile(dsfile):

						if os.path.splitext(dsfile)[1] == '.shp':
							# Esri Shapefile (copy all files)
							shpname = os.path.splitext(dsfile)[0]

							for shpext in ('shp', 'shx', 'dbf', 'sbn', 'sbx',
										   'fbn', 'fbx', 'ain', 'aih', 'atx',
										   'ixs', 'mxs', 'prj', 'xml', 'cpg'):
								shpfile = '{0}.{1}'.format(shpname, shpext)

								if os.path.exists(shpfile):
									collected_datafiles.append(shpfile)

						else:
							# other formats (we expect one file per datasource)
							collected_datafiles.append(dsfile)

					elif 'url' in dsfile.lower():
						# skip OWS layers (ugly: assuming URL in data source)
						continue

					else:
						messages.append("Unsupported data source: {0} is not a file".format(dsfile))

			# set busy cursor
			QApplication.setOverrideCursor(Qt.WaitCursor)

			# copy collected project files
			for dsfile in collected_datafiles: #list(publish_files.items()):
				try:
					dstfile = os.path.join(
						self._publish_dir,
						os.path.basename(dsfile)
					)

					# copy target only if doesn't exist or out-dated
					if not os.path.exists(dstfile) or os.stat(dsfile).st_mtime > os.stat(dstfile).st_mtime:
						shutil.copy(dsfile, dstfile)

				except (shutil.Error, IOError) as e:
					messages.append("Failed to copy data source: {0}".format(e))

			# restore original cursor
			QApplication.restoreOverrideCursor()

			if messages:
				raise Exception("Copying project files failed:\n{0}".format(os.linesep.join(messages)))


		def copy_project_files():
			"""Creates files required for publishing current project for NapkinGIS application."""
			publish_timestamp = str(metadata['publish_date_unix'])

			# create metadata file
			metadata_filename = "{0}/{1}_{2}.meta".format(self._publish_dir, self._publish_filename, publish_timestamp)
			with open(metadata_filename, "w") as f:
				def decimal_default(obj):
					if isinstance(obj, Decimal):
						return float(obj)
					raise TypeError
				json.dump(metadata, f, indent=2, default=decimal_default)

			# Create a copy of project's file with unique layer IDs (with publish timestamp)
			# to solve issue with duplicit layer ID when updating publish project.
			# Also to make sure the datasource-files have the correct path (current path – "./")
			published_project_filename = "{0}/{1}_{2}.qgs".format(self._publish_dir, self._publish_filename, publish_timestamp)
			with codecs.open(project.fileName(), 'r', 'utf-8') as fin,\
				 codecs.open(published_project_filename, 'w', 'utf-8') as fout:
				project_data = fin.read()

				for layer in self.plugin.layers_list():
					project_data = project_data.replace(
						'"{0}"'.format(layer.id()),
						'"{0}_{1}"'.format(layer.id(), publish_timestamp)
					)
					project_data = project_data.replace(
						'>{0}<'.format(layer.id()),
						'>{0}_{1}<'.format(layer.id(), publish_timestamp)
					)

				for dsfile in collected_datafiles:
					dsf = dsfile
					project_data = project_data.replace( dsf, './' + os.path.basename(dsf) )

					dsf = os.path.relpath(dsfile)
					project_data = project_data.replace( dsf, './' + os.path.basename(dsf) )

				fout.write(project_data)

			# If published project contains SpatiaLite layers, make sure they have filled
			# statistics info required to load layers by Mapserver. Without this procedure,
			# newly created layers in DB Manager wouldn't be loaded by Mapserver properly and
			# GetMap and GetLegendGraphics requests with such layers would cause server error.
			# The only way to update required statistics info is to create a new SpatiaLite
			# provider for every published SpatiaLite layer. (This is done automatically
			# when opening QGIS project file again).
			overlays_names = []
			def collect_overlays_names(layer_data):
				sublayers = layer_data.get('layers')
				if sublayers:
					for sublayer_data in sublayers:
						collect_overlays_names(sublayer_data)
				else:
					overlays_names.append(layer_data['name'])

			for layer_data in metadata['overlays']:
				collect_overlays_names(layer_data)

			map_layers = QgsProject.instance().mapLayers()
			providers_registry = QgsProviderRegistry.instance()
			for layer_name in overlays_names:
				layer = [l for l in list(map_layers.values()) \
						 if layer_name in (l.name(), l.shortName())][0]
				if layer.dataProvider().name() == "spatialite":
					provider = providers_registry.createProvider(
						"spatialite",
						layer.dataProvider().dataSourceUri()
					)
					del provider


		def create_zip_project_file():
			# create zip file in the directory of the QGIS project
			dirpath = os.path.dirname(self.plugin.project.fileName())
			filename = self._publish_filename
			zip_out_file = self._publish_dir

			shutil.make_archive(
				base_name=zip_out_file,
				format='zip',
				root_dir=dirpath,
				base_dir=filename
			)

		# copy project and data files into destination folder
		try:
			copy_data_sources()
			copy_project_files()
		except Exception as e:
			QMessageBox.critical(self.dialog, "Error", "{0}".format(e))
			return False

		# create zip archive for published project (in parrent directory)
		try:
			create_zip_project_file()
		except OSError as e:
			QMessageBox.critical(self.dialog, "Error", "Creating zip file failed. {0}".format(e))
			return False

		# remove publish folder
		shutil.rmtree( self._publish_dir )

		return True


	def on_show(self):
		tree = self.dialog.tree_project_files
		create_formatted_tree( tree, list(self.project_files_short()) )
		tree.expandAll()

		# Data sources
		self._datasources = {}
		vector_data_file = opt_value(self.plugin.metadata, 'vector_layers.filename')
		if vector_data_file:
			self._datasources['Vector layers'] = [
				os.path.join(
					os.path.dirname(
						self.plugin.project.fileName()
					),
					vector_data_file
				)
			]

		def collect_layers_datasources(layer_node):
			for index in range(layer_node.rowCount()):
				collect_layers_datasources(
					layer_node.child(index)
				)
			layer = layer_node.data(Qt.UserRole)
			if layer and layer_node.checkState() == Qt.Checked:
				layer_provider = layer.dataProvider()
				if isinstance(layer_provider, QgsVectorDataProvider):
					storage_type = layer_provider.storageType()
				elif isinstance(layer_provider, QgsRasterDataProvider):
					storage_type = 'Raster'
				else:
					storage_type = 'Other'

				datasource_uri = QgsDataSourceUri( layer_provider.dataSourceUri() )
				datasource_db = datasource_uri.database()
				if datasource_db:
					datasource_db = os.path.normpath(datasource_db)
				if storage_type not in self._datasources:
					self._datasources[storage_type] = dict() if datasource_db else set()
				if datasource_db:
					if datasource_db not in self._datasources[storage_type]:
						self._datasources[storage_type][datasource_db] = []
					if datasource_uri.schema():
						table_name = '{0}.{1}'.format(datasource_uri.schema(), datasource_uri.table())
					else:
						table_name = datasource_uri.table()
					table_item = [
						"{0} ({1})".format(table_name, datasource_uri.geometryColumn())
					]
					self._datasources[storage_type][datasource_db].append(table_item)
					if datasource_uri.sql():
						table_item.append(["SQL: {}".format(datasource_uri.sql())])
				else:
					dsfile = layer_provider.dataSourceUri().split('|')[0].strip()
					self._datasources[storage_type].add(os.path.normpath(dsfile))

		collect_layers_datasources(
			self.dialog.treeView.model().invisibleRootItem()
		)
		tree = self.dialog.tree_data_sources
		create_formatted_tree(tree, self._datasources)
		tree.expandAll()
