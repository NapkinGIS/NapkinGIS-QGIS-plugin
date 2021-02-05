# -*- coding: utf-8 -*-
"""
/***************************************************************************
 NapkinGIS plugin
 Publish your projects to NapkinGIS
 ***************************************************************************/
"""

import os

# Import the PyQt and QGIS libraries
from qgis.PyQt.QtWidgets import QWizard, QTreeWidgetItem

from .utils import opt_value, create_formatted_tree, Decimal
from .wizard import WizardPage


class PublishPage(WizardPage):

	def __init__(self, plugin, page):
		super(PublishPage, self).__init__(plugin, page)
		self.dialog.setButtonText(QWizard.CommitButton, self.dialog.buttonText(QWizard.NextButton))
		page.setCommitPage(True)

	def on_show(self):
		"""Creates configuration summary of published project."""

		def format_template_data(data):
			iterator = iter(list(data.items())) if type(data) == dict else enumerate(data)
			for key, value in iterator:
				if type(value) in (list, tuple):
					if value and isinstance(value[0], Decimal):
						value = ['{0:.5f}'.format(v) for v in value]
					data[key] = ', '.join(map(str, value))
			return data

		metadata = self.plugin.metadata
		data = {
			'DEFAULT_BASE_LAYER': self.dialog.default_baselayer.currentText(),
			'SCALES': self.plugin.resolutions_to_scales(metadata['tile_resolutions']),
			'PROJECTION': metadata['projection']['code'],
			'AUTHENTICATION': self.dialog.authentication.currentText(),
			'MESSAGE_TEXT': opt_value(metadata, 'message.text'),
			'MESSAGE_VALIDITY': opt_value(metadata, 'message.valid_until'),
			'EXPIRATION': metadata.get('expiration', ''),
		}

		for param in (
				'gislab_user',
				'plugin_version',
				'title',
				'abstract',
				'contact_person',
				'contact_mail',
				'contact_organization',
				'extent',
				'tile_resolutions',
				'units',
				'measure_ellipsoid',
				'use_mapcache'):
			data[param.upper()] = metadata[param]

		# collect base layer summary
		def collect_base_layer_summary(root, layer_data):
			sublayers = layer_data.get('layers')
			if sublayers:
				item = QTreeWidgetItem(root)
				item.setText(0, layer_data['name'])
				for sublayer_data in sublayers:
					collect_base_layer_summary(item, sublayer_data)
			else:
				resolutions = layer_data['resolutions']
				if 'min_resolution' in layer_data:
					resolutions = [
						res for res in resolutions if res >= layer_data['min_resolution'] \
						and res <= layer_data['max_resolution']]
				scales = self.plugin.resolutions_to_scales(resolutions)
				# Regular QGIS base layers
				if layer_data['type'] not in ('blank', 'osm', 'mapbox', 'bing'):
					if 'visibility_scale_max' in layer_data:
						scale_visibility = 'Maximum (inclusive): {0}, Minimum (exclusive): {1}'.format(
							layer_data['visibility_scale_max'],
							layer_data['visibility_scale_min']
						)
					else:
						scale_visibility = ''

					create_formatted_tree(root,
										  { '{0}': [
											  "Extent: {1}",
											  "CRS: {2}",
											  "Scale based visibility: {3}",
											  "Visible scales: {4}",
											  "Visible resolutions: {5}",
											  "Provider type: {6}",
											  "Attribution", ["Title: {7}", "URL: {8}"],
											  "Metadata", ["Title: {9}", "Abstract: {10}", "Keyword list: {11}"] ]
										  },
										  [
											  layer_data['name'],
											  layer_data['extent'],
											  layer_data['projection'],
											  scale_visibility,
											  scales,
											  resolutions,
											  layer_data.get('provider_type', ''),
											  opt_value(layer_data, 'attribution.title'),
											  opt_value(layer_data, 'attribution.url'),
											  layer_data['metadata']['title'],
											  layer_data['metadata']['abstract'],
											  layer_data['metadata']['keyword_list']
										  ]
					)

				# Special base layers
				else:
					layer_summary = [
						"Name: {0}",
						"Abstract: {1}",
						"Keywords: {2}",
						"Extent: {3}",
						"Visible scales: {4}",
						"Visible resolutions: {5}"
					]
					if layer_data['type'] == 'mapbox':
						layer_summary.append("MapId: {}".format(layer_data['mapid']))
						layer_summary.append("ApiKey: {}".format(layer_data['apikey']))
					elif layer_data['type'] == 'bing':
						layer_summary.append("ApiKey: {}".format(layer_data['apikey']))

					create_formatted_tree(root,
										  { '{0}' : layer_summary },
										  [
											  layer_data['name'],
											  opt_value(layer_data, 'metadata.abstract'),
											  opt_value(layer_data, 'metadata.keyword_list'),
											  layer_data['extent'],
											  scales,
											  resolutions,
										  ]
					)

		def collect_overlays_summary(root, layer_data):
			sublayers = layer_data.get('layers')
			if sublayers:
				item = QTreeWidgetItem(root)
				item.setText(0, layer_data['name'])
				for sublayer_data in sublayers:
					collect_overlays_summary(item, sublayer_data)
				item.setExpanded(True)
			else:
				if 'visibility_scale_max' in layer_data:
					scale_visibility = 'Maximum (inclusive): {0}, Minimum (exclusive): {1}'.format(
						layer_data['visibility_scale_max'],
						layer_data['visibility_scale_min']
					)
				else:
					scale_visibility = ''

				if layer_data.get('hidden'):
					create_formatted_tree(
						root,
						{ layer_data['name'] : "Hidden: True" }
					)
					return
				create_formatted_tree(root,
									  { '{0}' : [
										  "Visible: {1}",
										  "Queryable: {2}",
										  "Extent: {3}",
										  "CRS: {4}",
										  "Geometry type: {5}",
										  "Scale based visibility: {6}",
										  "Labels: {7}",
										  "Provider type: {8}",
										  "Attributes: {9}",
										  "Attribution:", ["Title: {10}", "URL: {11}"],
										  "Metadata:", ["Title: {12}", "Abstract: {13}", "Keyword list: {14}"] ]
									  },
									  [
										  layer_data['name'],
										  layer_data['visible'],
										  layer_data['queryable'],
										  layer_data['extent'],
										  layer_data['projection'],
										  layer_data.get('geom_type', ''),
										  scale_visibility,
										  layer_data.get('labels', False),
										  layer_data['provider_type'],
										  ", ".join([
											  attribute.get('title', attribute['name'])
											  for attribute in layer_data.get('attributes', [])
										  ]),
										  opt_value(layer_data, 'attribution.title'),
										  opt_value(layer_data, 'attribution.url'),
										  layer_data['metadata']['title'],
										  layer_data['metadata']['abstract'],
										  layer_data['metadata']['keyword_list'],
									  ]
				)

		# construct tree item
		tree = self.dialog.config_summary
		tree.setColumnCount(1)

		project_item = create_formatted_tree(tree.invisibleRootItem(),
											 { "Project" : [
												 "Title: {TITLE}",
												 "Abstract: {ABSTRACT}",
												 "Contact person: {CONTACT_PERSON}",
												 "Contact mail: {CONTACT_MAIL}",
												 "Contact organization: {CONTACT_ORGANIZATION}",
												 "Extent: {EXTENT}",
												 "Scales: {SCALES}",
												 "Resolutions: {TILE_RESOLUTIONS}",
												 "Projection: {PROJECTION}",
												 "Units: {UNITS}",
												 "Measure ellipsoid: {MEASURE_ELLIPSOID}",
												 "Use cache: {USE_MAPCACHE}",
												 "Authentication: {AUTHENTICATION}",
												 "Expiration date: {EXPIRATION}",
												 "Message text: {MESSAGE_TEXT}",
												 "Message validity: {MESSAGE_VALIDITY}" ]
											 },
											 data
		)

		item = create_formatted_tree(tree.invisibleRootItem(),
									 "Base layers (default: {DEFAULT_BASE_LAYER})",
									 data)
		for layer_data in metadata['base_layers']:
			collect_base_layer_summary(item, layer_data)
		item.setExpanded(True)

		item = create_formatted_tree(tree.invisibleRootItem(),
									 "Overlay layers")
		for layer_data in metadata['overlays']:
			collect_overlays_summary(item, layer_data)
		item.setExpanded(True)

		print_composers = []
		for composer_data in metadata['composer_templates']:
			print_composers.append('{0} ( {1} x {2}mm )'.format(
				composer_data['name'],
				int(round(composer_data['width'])),
				int(round(composer_data['height']))
				)
			)

		create_formatted_tree(tree.invisibleRootItem(),
							  { "Print composers" : print_composers }
		).setExpanded(True)



	def validate(self):
		return True
