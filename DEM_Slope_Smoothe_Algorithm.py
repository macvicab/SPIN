## This script creates segments from reaches when the difference ratio in drainage area from one reach to another is less than 10%. Slope is smoothed using a maximum of 25 cells upstream and 25 cells downstream for each segment.
## Inputs = table of reach data from reach segmentation, slope and discharge tool. They are existing field names (flow fill, hecras model- yes/no, raw elevation values, unique reach ids, elevation at the ending node of the reaches called “down_elev” and drainage area).
## Written by Kimisha Ghunowa, River Hydraulics Research Group, University of Waterloo. 
## Last edited: Sept 5, 2019
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
faccell = int(GetParameterAsText(1))

# Add Field to calculate slope
arcpy.AddField_management(tbl,"S_mperm", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
expressionslope= "(!downelev!-!upelev!)/!lengthr_m!"
arcpy.CalculateField_management(tbl, "S_mperm", str(expressionslope), "PYTHON_9.3", "")
AddMessage("The calculated slope is saved in final_segments.")


#---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# Slope Averaging

raw_value = "S_mperm"
unique_id = "OBJECTID"
down_elev = "downelev"
da = "drainarea_km2"
SAvg_length = int(((math.ceil(500/faccell))*2) + 1)

# new field name for average
savg = raw_value + str("_SAVG")

#add new fields to store results
fields_list = [field.name for field in arcpy.ListFields(tbl)]
new_fields_list = ["xstartSAVG", "ystartSAVG", "xendSAVG", "yendSAVG"]
new_fields_list2 = ["x_ystartSAVG", "x_yendSAVG"]
new_fields_list3 =["delta_DA","SAvg_ID","SAvg_Reaches", savg]

for new_field in new_fields_list:
    if new_field in fields_list:
        #print new_field + " exists: deleted"
       arcpy.DeleteField_management(tbl, new_field)
    arcpy.AddField_management(tbl, new_field,"DOUBLE")
    AddMessage("Add field:")

for new_field2 in new_fields_list2:
    if new_field2 in fields_list:
        #print new_field2 + " exists: deleted"
       arcpy.DeleteField_management(tbl, new_field2)
    arcpy.AddField_management(tbl, new_field2 ,"TEXT")

for new_field3 in new_fields_list3:
    if new_field3 in fields_list:
        #print new_field2 + " exists: deleted"
       arcpy.DeleteField_management(tbl, new_field3)
    arcpy.AddField_management(tbl, new_field3 ,"DOUBLE") 


# add start and end xy coordinates in new fields
arcpy.CalculateField_management(tbl, "xstartSAVG", "!SHAPE.firstPoint.X!", "PYTHON_9.3", "")
arcpy.CalculateField_management(tbl, "ystartSAVG", "!SHAPE.firstPoint.Y!", "PYTHON_9.3", "")
arcpy.CalculateField_management(tbl, "x_ystartSAVG", "str(float(!xstartSAVG!))+\",\"+ str(float(!ystartSAVG!))",  "PYTHON_9.3", "")
       
arcpy.CalculateField_management(tbl, "xendSAVG", "!SHAPE.lastPoint.X!", "PYTHON_9.3", "")
arcpy.CalculateField_management(tbl, "yendSAVG", "!SHAPE.lastPoint.Y!", "PYTHON_9.3", "")
arcpy.CalculateField_management(tbl, "x_yendSAVG", "str(float(!xendSAVG!))+\",\"+ str(float(!yendSAVG!))",  "PYTHON_9.3", "")

#----------------------------------------------------------------------------------------------------------------------------------------
# Create segments

# create list with all elevation values and sort in descending order.
elev_list = set()
cursor1 = arcpy.SearchCursor(tbl)

for row in cursor1:
    elev_v = row.getValue(down_elev)
    elev_id = row.getValue(unique_id)
    pair = (elev_id, elev_v)
    elev_list.add(pair)
del row, cursor1

elev_list_sorted = sorted(elev_list, key = lambda x: x[0])
elev_list_sorted = sorted(elev_list_sorted, key = lambda x: x[1], reverse= True)
#print len(elev_list_sorted)

#start from the reach with highest elevation, assign the same segment id while tracing downstream of the reach until the difference ratio in drainage area is >=0.1.
seg_id = 0
elev_list_count = elev_list_sorted

while len(elev_list_count) != 0:
    cursor2 = arcpy.UpdateCursor(tbl)
    max_elev = elev_list_count[0][1]
    max_id = elev_list_count[0][0]
    #print max_elev, max_id
    seg_id = seg_id + 1
    del elev_list_count[0]
    #print "max elev " + str(max_elev)
    for row in cursor2:
        r_elev = row.getValue(down_elev)
        r_id = row.getValue(unique_id)
        if max_elev == r_elev and max_id == r_id:  
            #print "r_elev " + str(r_elev)
            #print "r_id" + str(r_id)
            seg_r_id = 0
            start_endxy = row.getValue("x_yendSAVG")
            start_da =  row.getValue(da)
            #print "start da: " + str(start_da)
            row.setValue("SAvg_ID", seg_id)
            row.setValue("SAvg_Reaches", seg_r_id)
            cursor2.updateRow(row) 
            break
    del row, cursor2

    if start_da == None or start_da == 0:
        start_da = 0.0

    cursor3 = arcpy.UpdateCursor(tbl)
    for row in cursor3:
        r_startxy = row.getValue("x_ystartSAVG")
        if r_startxy == start_endxy:
            r_da = row.getValue(da)
            #print r_da
            r_seg_id = row.getValue("SAvg_ID")
            if r_da == 0 or r_da == None:
                delta_da = 0.0
            else:
                diff_da = r_da - start_da
                delta_da = (diff_da)/ r_da
            #print delta_da
            if delta_da <0.1 and r_seg_id == None:
                seg_r_id = seg_r_id + 1
                #print seg_r_id
                row.setValue("SAvg_ID", seg_id)
                row.setValue("SAvg_Reaches", seg_r_id)
                row.setValue("delta_DA", delta_da)
                start_endxy = row.getValue("x_yendSAVG")
                cursor3.updateRow(row)
                #delete pair in list if exist
                r_elev = row.getValue(down_elev)
                r_id = row.getValue(unique_id)
                pair = (r_id,r_elev)
                #print pair
                if pair in elev_list_count:
                    elev_list_count.remove(pair)
    del row, cursor3

#-------------------------------------------------------------------------------------
# Calculate rolling mean of segment using 25 reaches upstream and 25 reaches downstream in a segment
# get unique segment ids and their reaches as lists

import pandas as pd

seg_id_l = []
cursor4 = arcpy.SearchCursor(tbl)

for row in cursor4:
    seg_id = row.getValue("SAvg_ID")
    seg_id_l.append(seg_id)
del row, cursor4

seg_id_l_c = set(seg_id_l)
seg_id_l_unique = list(seg_id_l_c)

#loop through table and collect reachids
avg_window = {}

for seg_id in seg_id_l_unique:
    cursor5 = arcpy.SearchCursor(tbl)
    
    for row in cursor5:
        seg_id_row = row.getValue("SAvg_ID")
        if seg_id == seg_id_row: #change to seg_id
            #print seg_id_row
            seg_r_id = row.getValue("SAvg_Reaches")
            strm_pow = row.getValue(raw_value)
            avg_window[seg_r_id] = strm_pow
    del row, cursor5

    #print avg_window
    avg_window_df = pd.Series(avg_window)
    #avg_window_df = avg_window_df[~((avg_window_df-avg_window_df.mean()).abs() > 3*avg_window_df.std())] # remove outliers within 3 stds
    roll_avg_df = pd.rolling_mean(avg_window_df, window = SAvg_length , min_periods = 1, center = True)
    #print roll_avg_df

    # loop through set and calculate rolling mean
    for i, j in roll_avg_df.iteritems():
        seg_r_id_avg = i
        avg_value = j
        cursor6 = arcpy.UpdateCursor(tbl)
        for row in cursor6:
            seg_r_id = row.getValue("SAvg_Reaches")
            seg_id_c = row.getValue("SAvg_ID")
            if seg_id_c == seg_id and seg_r_id_avg == seg_r_id:
                row.setValue(savg, avg_value)
                cursor6.updateRow(row)
        del row, cursor6

AddMessage("The calculated smoothed slope is saved in final_segments.")
#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
