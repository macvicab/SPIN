## Python Script: This script delineates the cumulative drainage area as polygons for each discharge point.
## Written by Kimisha Ghunowa, River Hydraulics Research Group, University of Waterloo.
## Last edited on Sept 5, 2019.
#-------------------------------------------------------------------------------------------------------#

#import Arc Packages
import arcpy
import numpy as np
from arcpy import *
from arcpy.sa import *
import os
import csv
#import domainvalues

#Set workspace folder
workspace_folder = GetParameterAsText(0)
env.workspace= str(workspace_folder)

#Allow overwrite of results
arcpy.env.overwriteOutput = True

# Import discharge points shapefile
dischargepts = GetParameterAsText(1)

# Make a copy of discharge points shapefile
pointspath = str(workspace_folder) + "\\pointscopy.shp"
arcpy.CopyFeatures_management(dischargepts, pointspath)
arcpy.DeleteField_management(pointspath, ["Join_Count","TARGET_FID","Id","GRID_CODE", "ORIG_FID"])

#Import flow accumulation raster
flow_accum= GetParameterAsText(2)

#Import flow direction raster
flow_dir= GetParameterAsText(3)

#Import stream network
strm_net= GetParameterAsText(4)

##----------------------------------------------------------------------------------------------

# Create a folder to store the point shapefiles and use the shapefiles to create their drainage area polygons
arcpy.CreateFolder_management(str(workspace_folder), "pointshp")
arcpy.CreateFolder_management(str(workspace_folder), "dashp")
pointshppath= str(workspace_folder)+ "\\pointshp"
dashppath= str(workspace_folder)+ "\\dashp"
AddMessage("Creating folders to store discharge points and drainage area polygons.")

# select points on streams only
outintegrate= str(strm_net)
withintegrate= str(pointspath)
arcpy.Integrate_management([[outintegrate],[withintegrate]], "")

arcpy.MakeFeatureLayer_management(pointspath, "points_lyr")
arcpy.SelectLayerByLocation_management("points_lyr", "WITHIN_A_DISTANCE", strm_net, "0.01 Meters", "NEW_SELECTION", "NOT_INVERT")

#copy selected layer
select_points = str(workspace_folder)+ "\\select_points.shp"
arcpy.CopyFeatures_management("points_lyr", select_points)

#loop through point ids and create polygons
cursor= arcpy.da.SearchCursor(select_points, ["FID"])
for row in cursor:
	attribute=row[0]
	point_name = str(pointshppath) + "\\" + str(attribute) + u".shp"
	da_name = str(dashppath) + "\\" + str(attribute) + u".shp"
	where = "\"FID\" = " + str(attribute)
	arcpy.Select_analysis(select_points, point_name, where)
	snappour= SnapPourPoint(point_name, flow_accum, "10", "POINTID")
	wshed= Watershed(flow_dir, snappour, "Value")
	arcpy.RasterToPolygon_conversion(wshed, da_name, "NO_SIMPLIFY", "Value")

# Merge all watershed shapefiles together 
arcpy.env.workspace = dashppath
dashplist=arcpy.ListFeatureClasses()
arcpy.Merge_management(dashplist, os.path.join(dashppath, 'all_dashps.shp'))
AddMessage("Merging all drainage areas together.")

# Some drainage areas need to be dissolved
alldapath= str(dashppath)+ "\\all_dashps.shp"
alldapathlyr= str(dashppath)+ "\\all_dashpslyr"
final_da = str(dashppath)+ "\\final_da.shp"
arcpy.MakeFeatureLayer_management(alldapath, alldapathlyr)
arcpy.Dissolve_management(alldapathlyr, final_da, ["GRIDCODE"])
AddMessage("Dissolving drainage area polygons together.")

#Create file geodatabase to store final results
#Process: Delete geodatabase with same name and create new file geodatabase 
gdb_name=str(workspace_folder)+ "\\drainagearea.gdb"
arcpy.Delete_management(gdb_name)
arcpy.CreateFileGDB_management(str(workspace_folder), "drainagearea.gdb")

# Copy final drainage area polygons to geodatabase 
arcpy.FeatureClassToGeodatabase_conversion(final_da,gdb_name)
dischdagdb= gdb_name + "\\final_da"

# Edit field "GRIDCODE" to PointID
arcpy.AlterField_management(dischdagdb, "GRIDCODE", "POINTID", "", "", "", "NON_NULLABLE", "false")
AddMessage("The final drainage area polygons are saved in final_da.")