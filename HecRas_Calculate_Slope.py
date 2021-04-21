## This script creates segments from reaches when the difference ratio in drainage area from one reach to another is less than 0.1.
## Written by Kimisha Ghunowa, River Hydraulics Research Group, University of Waterloo.
## Last edited on Sept 5, 2019.
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

#Set workspace folder
#workspace_folder = GetParameterAsText(0)
#env.workspace= str(workspace_folder)

# Inputs
tbl = GetParameterAsText(0)

raw_elev = GetParameterAsText(1)
unique_id = "OBJECTID" # reach id
dist = "SHAPE_LENGTH"
slope_name = GetParameterAsText(2)


#add fields to store results
fields_list = [field.name for field in arcpy.ListFields(tbl)]
new_fields_list = [slope_name]

for new_field in new_fields_list:
    if new_field in fields_list:
        arcpy.DeleteField_management(tbl, new_field)
    arcpy.AddField_management(tbl, new_field,"DOUBLE")
    
# get the start of each reach
rid_list = []
cursor = arcpy.SearchCursor(tbl)
for row in cursor:
    r_id = row.getValue(unique_id)
    rid_list.append(r_id)
del row, cursor

while len(rid_list) !=0: 
    start_rid = rid_list[0]
    print start_rid
    rid_list.remove(start_rid)
    cursor1 = arcpy.SearchCursor(tbl)
    for row in cursor1:
        rid = row.getValue(unique_id)
        if start_rid == rid:
            up_elev = row.getValue(raw_elev)
            print up_elev
            start_endxy = row.getValue("x_yendINTP") # get end of reach
            break
    del row, cursor1

    cursor2 = arcpy.UpdateCursor(tbl)
    for row in cursor2:
        r_startxy = row.getValue("x_ystartINTP")
        if r_startxy == start_endxy:
            down_elev = row.getValue(raw_elev) # get the elev
            distance = row.getValue(dist)
            slope_tbl = row.getValue(slope_name)
            if slope_tbl == None:
                if down_elev == None or up_elev == None:
                    slope = None
                    row.setValue(slope_name, slope)
                    cursor2.updateRow(row)
                else:
                    diff = down_elev-up_elev
                    slope = diff/distance
                    row.setValue(slope_name, slope)  
                    cursor2.updateRow(row)
            # delete id if exists
            rid = row.getValue(unique_id)
            if rid in rid_list:
                rid_list.remove(rid)
            # next reach
            start_endxy = row.getValue("x_yendINTP")
            up_elev = down_elev
    del row, cursor2