## This script calculates total and specific stream power, difference and ratio between rural and urban stream power for
## different hecras storm events.
## Total stream power = Qchannel * Slope_SAVG (DEM) * weight of water
## Specific stream power = Total stream power/channel width
## Difference in stream power = Stream power for storm - Rural stream power
## Ratio of stream power = Stream power for storm / Rural stream power
## Written by Kimisha Ghunowa, River Hydraulics Research Group, University of Waterloo.
## Last edited on Sept 5, 2019
#----------------------------------------------------------------------------------------------------------------------

#import Arc Packages
import arcpy
from arcpy import *
from arcpy.sa import *
import arcinfo
import os
import sys
import math
import pandas as pd
import numpy as np

#Allow overwrite of results
arcpy.env.overwriteOutput = True

#get inputs
tbl = GetParameterAsText(0)
slope = GetParameterAsText(1) # DEM smoothed slope
disch = GetParameterAsText(2) # hecras Q channel
width = GetParameterAsText(3) # hecras channel width
prefix = GetParameterAsText(4)
#rural_pow = GetParameterAsText(5) #rural total stream power
#rural_spow = GetParameterAsText(6) #rural specific stream power

water_fld = "Wg_Nperm3" # weight of water
da = "drainarea_km2" # drainage area


#-------------------------------------------------------------------------------------------------------------------------------------
#Add new fields to store results
pow_fld = "Power_Wperm" + str(prefix)
spow_fld = "SPower_Wperm2" + str(prefix)
#pow_ratio = "Ratio_Power_Wperm" + str(prefix)
#spow_ratio = "Ratio_SPower_Wperm2" + str(prefix)

#-----------------------------------------------------------------------------------------------------------------------------------------
# add new fields
fields_list = [field.name for field in arcpy.ListFields(tbl)]

if "Wg_Nperm3" not in fields_list:
	# Add Field with specific weight of water(9810 N) and strmpower
	arcpy.AddField_management(tbl,"Wg_Nperm3", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
	arcpy.CalculateField_management(tbl, "Wg_Nperm3", "9810" , "VB", "")

#-----------------------------------------------------------------------------------------------------------------------------------------------------
## Calculate stream power

#new_fields_list = [pow_fld, pow_ratio, spow_fld, spow_ratio]
new_fields_list = [pow_fld, spow_fld]

for new_field in new_fields_list:
    if new_field in fields_list:
        arcpy.AddMessage("Fields exist. Enter a different prefix.")
        sys.exit(0)

for new_field in new_fields_list:
    arcpy.AddField_management(tbl, new_field,"DOUBLE")

# Iterate through rows and make calculations
cursor = arcpy.UpdateCursor(tbl)
for row in cursor:
	r_slope = row.getValue(slope)
	r_disch = row.getValue(disch)
	r_width = row.getValue(width)
	r_weight = row.getValue(water_fld)
	#r_ruralpow = row.getValue(rural_pow)
	#r_ruralspow = row.getValue(rural_spow)
	#if r_slope == None or r_disch == None or r_width == None or r_ruralpow == None or r_ruralspow == None:
	if r_slope == None or r_disch == None or r_width == None:
		row.setValue(pow_fld, None)
		row.setValue(spow_fld, None)
		#row.setValue(pow_ratio, None)
		#row.setValue(spow_ratio, None)
		cursor.updateRow(row)
	else:
		r_pow = r_slope*r_disch*r_weight*-1
		r_spow = r_pow/r_width
		#r_pow_ratio = r_pow/r_ruralpow
		#r_spow_ratio = r_spow/r_ruralspow
		row.setValue(pow_fld, r_pow)
		row.setValue(spow_fld, r_spow)
		#row.setValue(pow_ratio, r_pow_ratio)
		#row.setValue(spow_ratio, r_spow_ratio)
		cursor.updateRow(row)
del row, cursor