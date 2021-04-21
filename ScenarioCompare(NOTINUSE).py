## This script calculates the difference between a user-defined rural and urban stream power.
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


#Allow overwrite of results
arcpy.env.overwriteOutput = True

# Import summarytable from geodatabase
summarytbl = GetParameterAsText(0)

#Inputs fields
rural_tp = GetParameterAsText(1)
urban_tp = GetParameterAsText(2)
statfield_tp = GetParameterAsText(3)

# Check if the label already exist
arcpy.AddMessage("If field already exists, program will end.")

list_field = arcpy.ListFields(summarytbl)
for field in list_field:
	checklabel= statfield_tp
	if field.name == str(checklabel):
		arcpy.AddMessage("Statistic Field already exists. Please, Enter a different fieldname.")
		sys.exit(0)
	
# Add field to summary table
arcpy.AddField_management(summarytbl, statfield_tp, "DOUBLE", "", "", "", "", "NULLABLE", "REQUIRED")
expressiontp = "!" + str(urban_tp) + "!" + "-" + "!" + str(rural_tp) + "!"
arcpy.CalculateField_management(summarytbl, statfield_tp, str(expressiontp), "PYTHON_9.3")

