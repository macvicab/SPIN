## This script interpolates values for reaches without a river station with HECRAS results.
## Inputs: table of stream reaches, field names (reach ids, raw value requiring interpolation, reach length)
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

#Set workspace folder
#workspace_folder = GetParameterAsText(0)
#env.workspace= str(workspace_folder)

# Inputs
tbl = GetParameterAsText(0)
river_sta_id = GetParameterAsText(1) # river_sta
unique_id = GetParameterAsText(2) # sseg id
raw_value = GetParameterAsText(3) # all fields for interpolation 
dist_value = GetParameterAsText(4) # stream length

#add fields to store results
fields_list = [field.name for field in arcpy.ListFields(tbl)]
new_fields_list = ["xstartINTP", "ystartINTP", "xendINTP", "yendINTP"]
new_fields_list2 = ["x_ystartINTP", "x_yendINTP"]

for new_field in new_fields_list:
    if new_field in fields_list:
        arcpy.DeleteField_management(tbl, new_field)
    arcpy.AddField_management(tbl, new_field,"DOUBLE")
        
for new_field2 in new_fields_list2:
    if new_field2 in fields_list:
        arcpy.DeleteField_management(tbl, new_field2)
    arcpy.AddField_management(tbl, new_field2 ,"TEXT")

#add start and end xy coordinates of reaches
arcpy.CalculateField_management(tbl, "xstartINTP", "!SHAPE.firstPoint.X!", "PYTHON_9.3", "")
arcpy.CalculateField_management(tbl, "ystartINTP", "!SHAPE.firstPoint.Y!", "PYTHON_9.3", "")
arcpy.CalculateField_management(tbl, "x_ystartINTP", "str(float(!xstartINTP!))+\",\"+ str(float(!ystartINTP!))",  "PYTHON_9.3", "")
arcpy.CalculateField_management(tbl, "xendINTP", "!SHAPE.lastPoint.X!", "PYTHON_9.3", "")
arcpy.CalculateField_management(tbl, "yendINTP", "!SHAPE.lastPoint.Y!", "PYTHON_9.3", "")
arcpy.CalculateField_management(tbl, "x_yendINTP", "str(float(!xendINTP!))+\",\"+ str(float(!yendINTP!))",  "PYTHON_9.3", "")

# loop through each field for interpolation and create new field names
raw_value_split = raw_value.split(';')

for r in raw_value_split:
    raw_value = str(r)
    calc_name = str("INTP_") + str(r)
    if calc_name in fields_list:
        arcpy.DeleteField_management(tbl, calc_name)
        arcpy.AddField_management(tbl, calc_name, "DOUBLE")
    else:
        arcpy.AddField_management(tbl, calc_name, "DOUBLE")

    # add field to identify reaches that will be interpolated between two selected river stations
    new_fields_list3 = ["INTP_ID", "INTP_LENGTH"]

    for new_field in new_fields_list3:
        if new_field in fields_list:
            arcpy.DeleteField_management(tbl, new_field)
        arcpy.AddField_management(tbl, new_field, "DOUBLE")

    # create list with all river station ids where data exists.
    sta_list = []
    cursor1 = arcpy.SearchCursor(tbl)
    for row in cursor1:
        r_sta = row.getValue(river_sta_id)
        r_id = row.getValue(unique_id)
        raw_v = row.getValue(raw_value)
        if raw_v is not None:
            pair = (r_id, r_sta)
            sta_list.append(pair)
    del row, cursor1

    # loop through table, get first station in list of station with existing data, assign a cumulative length (intp_length) of 0 to the first station, save the value for the field
    # to be interpolated in y_list and save the cumulative distance in the x_list.
    sta_list_c = sta_list
    y_list = []
    x_list = []
    x_intp_list = []

    intp_id = 0

    while len(sta_list_c) != 0:
        x_list=[]
        y_list=[]
        x_intp_list = []

        cursor2 = arcpy.UpdateCursor(tbl)
        first_sta = sta_list_c[0][1]
        first_rid = sta_list_c[0][0]
        print first_sta, first_rid
        intp_id = intp_id + 1
        del sta_list_c[0]
        print "processing station " + str(first_sta)
        for row in cursor2:
            r_sta = row.getValue(river_sta_id)
            r_id = row.getValue(unique_id)
            if first_sta == r_sta and first_rid == r_id:
                print "r_sta " + str(r_sta)
                print "r_id " + str(r_id)
                dist_sum = 0
                y_start = 0
                start_endxy = row.getValue("x_yendINTP") # get end of reach
                first_rawv = row.getValue(raw_value) # get the value to average
                x_list.append(y_start)     # add first x=0 to x list    
                y_list.append(first_rawv) # add first elev to y list
                row.setValue(calc_name, first_rawv)
                row.setValue("INTP_ID", intp_id)
                row.setValue("INTP_LENGTH", dist_sum)
                cursor2.updateRow(row) 
                break
        del row, cursor2

        # trace downstream using end xy coordinates of first reach to find start xy coordinates of subsequent reach
        # if both raw value field (field to be interpolated) and interpolated field (calc_name)are none, then update
        # the reach's cumulength length (INTP_Length), identifier (INTP_ID) and save the reach id. If raw value exists, break loop.
        # e.g. let's interpolate elevation values
        # reach id = [1,2,3,4]  stations 2 and 3 are located between 1 and 4. 1 and 4 have hecras data.
        # intp_length = [0,10,20,30]
        # intp_id = [1,1,1,1]
        # raw value = [120, na, na, 30]
        # x_list = [0,10,20,30] # same as cumulative length
        # y_list = [120, na, na, 30]
        # interpolated raw value = [120, 90, 60,30]

        cursor3 = arcpy.UpdateCursor(tbl)
        for row in cursor3:
            r_startxy = row.getValue("x_ystartINTP")
            if r_startxy == start_endxy:
                distv = row.getValue(dist_value) # get the distance
                rawv = row.getValue(raw_value) # get the elev
                intp_v = row.getValue(calc_name)
                print distv
                print rawv
                print intp_v
                if rawv == None and intp_v == None:
                    dist_sum = dist_sum + distv
                    print "sum distance " + str(dist_sum)
                    x_intp_list.append(dist_sum)
                    row.setValue("INTP_LENGTH", dist_sum)
                    row.setValue("INTP_ID", intp_id)
                    start_endxy = row.getValue("x_yendINTP")
                    cursor3.updateRow(row)
                    #delete pair in list if exist
                    r_sta = row.getValue(river_sta_id)
                    r_id = row.getValue(unique_id)
                    pair = (r_id,r_sta)
                    #print pair
                    if pair in sta_list_c:
                        sta_list_c.remove(pair)
                elif rawv is not None:
                    dist_sum = dist_sum + distv
                    y_list.append(rawv)
                    x_list.append(dist_sum)
                    break      
        del row, cursor3
        
        # Use x_list (cumulative length) and y_list (raw values)
        cursor4 = arcpy.UpdateCursor(tbl)
        for row in cursor4:
            intp_id_tbl = row.getValue("INTP_ID")    
            y_sum_tbl = row.getValue("INTP_LENGTH")
            rawv_tbl = row.getValue(calc_name)
            if intp_id == intp_id_tbl and rawv_tbl == None:
                intp_rawv = np.interp(y_sum_tbl, x_list, y_list)
                if len(x_list) == 1:                       #### must check this. if difference is too small, min elev may stay the same.
                    row.setValue(calc_name, None)
                else:
                    row.setValue(calc_name, intp_rawv)
                    cursor4.updateRow(row)
        del row, cursor4