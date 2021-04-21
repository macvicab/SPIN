##Python script: This script delineates the stream network from a DEM by 1) filling errors in the DEM, 2) creating a flow direction raster, 3) creating a flow accumulation raster, 4) applying a drainage area threshold to the raster to extract the cells which belong to the stream network and 5) convert the cells which belong to the stream network into a linear feature.
##Inputs: DEM, Drainage Area Threshold
##Written by Kimisha Ghunowa, River Hydraulics Research Group, University of Waterloo. 
# Last edited: Sept 5, 2019.
#-----------------------------------------------------------------------------------------------#

#Import the Arc Package
import arcpy
import os
from arcpy import *
from arcpy import env
from arcpy.sa import *

#Enable the Spatial Analyst Extension license
arcpy.CheckOutExtension("Spatial")

#Allow overwrite of files
arcpy.env.overwriteOutput = True

#Set the current workspace for geoprocessing
workspace_folder = GetParameterAsText(0)
env.workspace= workspace_folder

#Ask User Input for Folder Path and Geodatabase name
out_folder_path = workspace_folder

# Importing DEM as a parameter
dem=GetParameterAsText(1)

# Import drainage threshold as parameter
thres=GetParameterAsText(2)

# Process: Fill the depressions and shave the peaks in the DEM to represent continuous flow downstream and Save 
dem_fill=Fill(dem)
dem_fill.save(str(out_folder_path) +"\\flow_fill")
AddMessage("Creating fill raster where holes/sinks in the DEM are corrected.")

# Process: Find the direction of steepest descent (Flow Direction) from cell to cell and Save
dem_flow_direction= FlowDirection(dem_fill)
dem_flow_direction.save(str(out_folder_path) + "\\flow_dir")
AddMessage("Creating flow direction raster to define direction of flow to steepest downslope cell") 

# Process: Find the cumulative number of cells which flow into each cell (Flow Accumulation) and Save
dem_accum = FlowAccumulation(dem_flow_direction)
dem_accum.save(str(out_folder_path) + "\\flow_accum")
AddMessage("Creating flow accumulation raster to define the accumulated flow in each cell.")

# Process: Extract cells which belong to the Stream by applying a Drainage Threshold and Save
thres=GetParameterAsText(2)
accum_path= str(out_folder_path) + "\\flow_accum"
expression= "Value >=" + str(thres)
strm_thres = Con(accum_path, 1 , "", expression)
strm_thres.save(str(out_folder_path) + "\\strm_thres")
AddMessage("Creating flow accumulation raster to define the stream by a threshold accumulated flow." + str(expression) + "in m^2.")

# Process: Assign a unique identifier to the cells which belong to the same branch in the stream network (Stream Link). The longest branch is assigned the unique identifier 1 and is considered the main branch of the network. All tributaries connected to the main branch are assigned their own identifiers and Save
strm_link= StreamLink(strm_thres, dem_flow_direction)
strm_link.save(str(out_folder_path) + "\\strm_link")
AddMessage("Creating stream network raster with values assigned to each tributary.")

#Process: Assign each branch an order number according to the Shreve’s method (Stream Order) and save
strm_order = StreamOrder(strm_thres, dem_flow_direction, "SHREVE")
strm_order.save(str(out_folder_path) + "\\strm_order")
AddMessage("Creating stream order raster with values assigned to each tributary.")

# Process: Convert cells belonging to the stream (Raster Stream) to Polyline feature
strm_network=StreamToFeature(strm_thres, dem_flow_direction, "strm_net.shp", "NO_SIMPLIFY")
AddMessage("Creating final stream network polyline called strm_net.shp.")

# Optional Process: Convert stream cells (Stream Link) to Polygons
strm_fishnet= str(out_folder_path) + "\\strm_fishnet.shp"
fishnet = arcpy.RasterToPolygon_conversion(strm_link,strm_fishnet, "NO_SIMPLIFY", "VALUE", "MULTIPLE_OUTER_PART")
AddMessage("Converting the raster cells into polygons called demcellspolygon.shp.")