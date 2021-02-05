# -*- coding: utf-8 -*-
"""
/***************************************************************************
 NapkinGIS plugin
 Publish your projects to NapkinGIS
 ***************************************************************************/
"""

def classFactory(iface):
	from .webgisplugin import WebGisPlugin
	return WebGisPlugin(iface)
