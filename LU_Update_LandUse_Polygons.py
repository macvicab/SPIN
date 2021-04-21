## This script updates the old land use cover with the new land use polygons.
## Written by Kimisha Ghunowa, River Hydraulics Research Group, University of Waterloo.
## Last edited on Sept 5, 2019.
#------------------------------------------------------------------------------------------#

#import Arc Packages
import arcpy
import numpy as np
from arcpy import *
from arcpy.sa import *
import os
import arceditor
import arcinfo

#Set workspace folder
workspace_folder = GetParameterAsText(0)
env.workspace= str(workspace_folder)

#Allow overwrite of results
arcpy.env.overwriteOutput = True

#Import old land use shapefile
oldlu = GetParameterAsText(1)

#Import the new land use shapefile
newlu = GetParameterAsText(2)

# Update old land use with new land use
updatedlu= str(workspace_folder) + "\\modifiedlu.shp"
arcpy.Update_analysis(oldlu, newlu, updatedlu)
