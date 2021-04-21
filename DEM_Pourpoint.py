## Python Script: This script creates a point feature to represent the pourpoint/outlet of the stream network. The flow accumulation raster is converted to a point feature class and the point with the maximum value is selected as the pourpoint location.
## Written by Kimisha Ghunowa, River Hydraulics Research Group, University of Waterloo.
## Last edited on Sept 9, 2019
#---------------------------------------------------------------------------------------#

#import Arc Packages
import arcpy
from arcpy import *
from arcpy.sa import *
import arceditor


#Set workspace folder
workspace_folder = GetParameterAsText(0)
env.workspace= str(workspace_folder)

#Allow overwrite of results
arcpy.env.overwriteOutput = True

#Import flow accumulation raster
f_accum = GetParameterAsText(1)
flow_accum = Raster(f_accum)

# Process: Convert raster into point and Save as acc_points.shp
arcpy.RasterToPoint_conversion(flow_accum, "acc_points")

# Process: Find maximum point and Save as table
accum_points_path= str(workspace_folder) + "\\acc_points.shp"
arcpy.Statistics_analysis(accum_points_path,"maxaccum_value", [["GRID_CODE", "MAX"]])
AddMessage("Finding maximum flow accumulation.")

# Process: Use maximum point as variable
maxaccum_tbl= str(workspace_folder) + "\\maxaccum_value"

#Select maxaccumulation value from table
cursor=arcpy.da.SearchCursor(maxaccum_tbl, ["MAX_GRID_CODE"])
for row in cursor:
	maxaccum= "{0}".format(row[0])
	maxaccum_flt= str(maxaccum)

#Save maxaccumumulation point as point feature

expression= "GRID_CODE =" + str(maxaccum_flt)

arcpy.MakeFeatureLayer_management (accum_points_path, "pourpoint")
arcpy.gp.SelectLayerByAttribute_management("pourpoint","NEW_SELECTION",expression)
arcpy.CopyFeatures_management("pourpoint", "pour_point")

# Process: Snap
pourpt= str(workspace_folder) + "\\pour_point.shp"
cell_size = GetParameterAsText(2)
strmnet= GetParameterAsText(3)
cell_info = str(cell_size) + " Meters"
vertex_type= "END"
strmnet_info = [str(strmnet), str(vertex_type), str(cell_info)]
arcpy.Snap_edit(pourpt, [strmnet_info])
AddMessage("Creating final pourpoint point called pour_point.shp.")






