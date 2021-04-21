## Python Script: This script finds the elevation points along the stream network, uses the elevation points to create reaches, calculates slope and discharge for each reach and calculates the distance of each tributary and main branch to the outlet.
## Inputs for this tool were created from the Stream Network script. They are flow fill raster, flow accumulation (threshold applied) raster, flow accumulation raster, flow direction raster and stream network linear feature.
## Written by Kimisha Ghunowa, River Hydraulics Research Group, University of Waterloo. 
## Last edited on Sept 5, 2019
#------------------------------------------------------------------------------------------#

#import Arc Packages
import arcpy
import numpy as np
from arcpy import *
from arcpy.sa import *
import os
import arceditor
import arcinfo
import math
import sys
import pandas as pd

#Set workspace folder
workspace_folder = GetParameterAsText(0)
env.workspace= str(workspace_folder)

#Allow overwrite of results
arcpy.env.overwriteOutput = True

#Import elevation fill sink data
edemflowfill = GetParameterAsText(1)

# Import flow accumulation (threshold applied) data
faccumthres = GetParameterAsText(2)

# Import flow accumulation
edemfacc = GetParameterAsText(3)

# Import flow direction
strm_net = GetParameterAsText(4)

#-------------------------------------------------------------------------------------------------------
# Create network ids and calculate lengths before creating reaches

# get list of arc id (i.e. the unique ids for each branch) and sort in ascending.
arc_list =[]
cursor = arcpy.SearchCursor(strm_net)
for row in cursor:
    id = row.getValue("ARCID")
    arc_list.append(id)
del row, cursor 

sort_arc = sorted(arc_list)
print(sort_arc)

# create new field to label mainstem and tributaries
fields_list = [field.name for field in arcpy.ListFields(strm_net)]
new_fields_list = ["WID", "ConnectID", "PolyLength", "WIDTLength"]
for new_field in new_fields_list:
    if new_field in fields_list:
        #print new_field + " exists: deleted"
        arcpy.DeleteField_management(strm_net, new_field)
    arcpy.AddField_management(strm_net, new_field,"DOUBLE")
    AddMessage("Adding new fields")

# loop though arc id, get the unique ids of the branch (from_node) and copy it to the field “WID”. Get the branch to which it connects (to_node) and copy it to the field “ConnectID”. Calculate the length of each branch as “Polylength”. Calculate the sum of lengths of each unique WID as “WIDTLength”.
netid = 0
while len(sort_arc) != 0:
    netid = netid + 1
    min_arc = sort_arc[0]
    del sort_arc[0]
    cursor = arcpy.UpdateCursor(strm_net)
    for row in cursor:
        arcid = row.getValue("ARCID")
        if arcid == min_arc:
            tonode = row.getValue("TO_NODE") #get downstream id of node ("TO_NODE") of first/next branch
            print("tonode " + str(tonode))
            row.setValue("WID", netid)
            cursor.updateRow(row)
            break
    del row, cursor

    # find the branch whose upstream id of node (FROM_NODE) matches/connects to the TO_NODE of the first/upstream branch. Trace downstream in this manner, update the WID and delete the id (arcid) of the branch that has already been traced. 
    cursor = arcpy.UpdateCursor(strm_net)
    for row in cursor:
        fromnode = row.getValue("FROM_NODE")
        print("fromnode " + str(fromnode))
        if tonode == fromnode:
            strm_net_netid = row.getValue("WID")
            print("strm_net_netid " + str(strm_net_netid))
            tonode = row.getValue("TO_NODE")
            print("tonode " + str(tonode))
            print tonode
            if strm_net_netid == 0:
                arcid = row.getValue("ARCID")
                row.setValue("WID", netid)
                cursor.updateRow(row)
                if arcid in sort_arc:
                    sort_arc.remove(arcid)
    del row, cursor

#---------------------------------------------------------
# Get connections of network (part 1): find which branch is connected to another branch and store the wid of the connected branch in "CONNECTID"

# get the wids of the branches
wid_list = []
cursor = arcpy.SearchCursor(strm_net)
for row in cursor:
    wid = row.getValue("WID")
    wid_list.append(wid)
del row, cursor

wid_l_set = set(wid_list)
wid_l_u = list(wid_l_set)

# loop through list of wid to get connect id
for wid in wid_l_u:
    fromnode_wid = []
    cursor = arcpy.SearchCursor(strm_net)
    for row in cursor:
        strm_net_wid = row.getValue("WID")
        if wid == strm_net_wid:
            fromnode = row.getValue("FROM_NODE")
            fromnode_wid.append(fromnode)
    del row, cursor

    # get the pairs of connections with tonode
    connect_wid = set()
    cursor = arcpy.SearchCursor(strm_net)
    for row in cursor:
        strm_net_wid = row.getValue("WID")
        if wid != strm_net_wid:
            tonode = row.getValue("TO_NODE")
            if tonode in fromnode_wid:
                p = (strm_net_wid,tonode)
                connect_wid.add(p)
    del row, cursor

    cursor = arcpy.UpdateCursor(strm_net)
    for row in cursor:
        strm_net_wid = row.getValue("WID")
        if strm_net_wid == wid:
            fromnode_wid = row.getValue("FROM_NODE")
            for p_id, pnode in connect_wid:
                if fromnode_wid == pnode:
                    row.setValue("ConnectID", p_id)
                    cursor.updateRow(row)
    del row, cursor

# calculate total length of each branch in meters
arcpy.CalculateField_management(strm_net, "PolyLength", "!SHAPE.LENGTH@METERS!", "PYTHON")

# calculate total length of branches with same WIDs in meters
for wid in wid_l_u:
    sum_l = []
    cursor = arcpy.SearchCursor(strm_net)
    for row in cursor:
        strm_net_wid = row.getValue("WID")
        if strm_net_wid == wid:
            l = row.getValue("PolyLength")
            sum_l.append(l)
    del row, cursor

    total = sum(sum_l)
    cursor = arcpy.UpdateCursor(strm_net)
    for row in cursor:
        strm_net_wid = row.getValue("WID")
        if strm_net_wid == wid:
            row.setValue("WIDTLength", total)
            cursor.updateRow(row)
    del row, cursor


#-----------------------------------------------------------------------------------------------------
#Creating segments by dividing the stream network into small sections defined from 1 elevation point to another elevation point downstream. Therefore, the starting node of a reach is defined at the upstream location of the elevation point and the ending node of a reach is defined at the downstream location of the elevation point.

# Process: Raster to Point - Converting the center of elevation cells into points
strm_pts= str(workspace_folder) + "\\strmthrespts.shp"
arcpy.RasterToPoint_conversion(faccumthres, strm_pts, "Value")
AddMessage("Converting stream cells to points.")

# add values of filled dem and flow accumulation to stream points
ExtractMultiValuesToPoints(strm_pts, [[edemflowfill, "elev"], [edemfacc, "flow_accum"]])

# Process: Integrate- It is used to maintain integrity of shared feature boundaries, i.e. the stream network is modified to contain the elevation points as its vertices.
outintegrate= str(strm_net)
withintegrate= str(strm_pts)
arcpy.Integrate_management([[outintegrate],[withintegrate]], "")
AddMessage("Points are integrated as the vertices of the stream network.")

# Process: Split Line at Point- split lines at each point(note: location of both slope points and discharge points coincide).
splitstrmpath=str(workspace_folder) + "\\segments.shp"
arcpy.SplitLine_management(strm_net,splitstrmpath)
AddMessage("The stream network is split into segments.")

#Process: Delete geodatabase with same name and create new file geodatabase 
gdb_name=str(workspace_folder)+ "\\segments.gdb"
arcpy.Delete_management(gdb_name)
arcpy.CreateFileGDB_management(str(workspace_folder), "Segments.gdb")

#Save shapefile to file geodatabase
arcpy.FeatureClassToGeodatabase_conversion(splitstrmpath,gdb_name)
reachgdb= gdb_name + "\\segments"

#Save shapefile to file geodatabase
arcpy.FeatureClassToGeodatabase_conversion(strm_pts,gdb_name)
ptgdb= gdb_name + "\\strmthrespts"


#---------------------------------------------------------------------------------------------------------------------------
# Add Fields to reach to obtain the first x,y coordinates.
arcpy.AddField_management(reachgdb,"xstartr", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
arcpy.AddField_management(reachgdb,"ystartr","DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
arcpy.AddField_management(reachgdb,"x_ystartr", "TEXT")
arcpy.CalculateField_management(reachgdb, "xstartr", "!SHAPE.firstPoint.X!", "PYTHON_9.3", "")
arcpy.CalculateField_management(reachgdb, "ystartr", "!SHAPE.firstPoint.Y!", "PYTHON_9.3", "")
arcpy.CalculateField_management(reachgdb, "x_ystartr", "str(float(!xstartr!))+\",\"+ str(float(!ystartr!))",  "PYTHON_9.3", "")

# Add Fields to reach to obtain the last x,y coordinates.
arcpy.AddField_management(reachgdb,"xendr", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
arcpy.AddField_management(reachgdb,"yendr","DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
arcpy.AddField_management(reachgdb,"x_yendr", "TEXT")
arcpy.CalculateField_management(reachgdb, "xendr", "!SHAPE.lastPoint.X!", "PYTHON_9.3", "")
arcpy.CalculateField_management(reachgdb, "yendr", "!SHAPE.lastPoint.Y!", "PYTHON_9.3", "")
arcpy.CalculateField_management(reachgdb, "x_yendr", "str(float(!xendr!))+\",\"+ str(float(!yendr!))",  "PYTHON_9.3", "")

# Add Field to reach to calculate length of line in metres
arcpy.AddField_management(reachgdb,"lengthr_m", "FLOAT", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
arcpy.CalculateField_management(reachgdb, "lengthr_m", "!SHAPE.length@meters!", "PYTHON_9.3", "")


#---------------------------------------------------------------------------------------------------------------------
#Calculate Drainage area

#Get the raster properties
elevCellX = arcpy.GetRasterProperties_management(edemflowfill, "CELLSIZEX")

#Get the elevation cell size from the properties
faccell = float(elevCellX.getOutput(0))

# Add field to calculate drainage area of each point
arcpy.AddField_management(ptgdb, "drainarea_km2", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

# Calculate drainage area based on 30x30m cell(given by elevation cell dimension)
cell_area= math.pow(float(faccell),2)
expressiondarea= "([flow_accum]/1000000)*" + str(cell_area)
arcpy.CalculateField_management(ptgdb, "drainarea_km2", str(expressiondarea), "VB", "")

# Add field to discharge points to obtain the x,y coordinates of the points.
arcpy.AddField_management(ptgdb,"xp", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
arcpy.AddField_management(ptgdb,"yp","DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
arcpy.AddField_management(ptgdb,"x_yp", "TEXT")
arcpy.CalculateField_management(ptgdb, "xp", "!SHAPE.CENTROID.X!", "PYTHON_9.3", "")
arcpy.CalculateField_management(ptgdb, "yp", "!SHAPE.CENTROID.Y!", "PYTHON_9.3", "")
arcpy.CalculateField_management(ptgdb, "x_yp", "str(float(!xp!))+\",\"+ str(float(!yp!))",  "PYTHON_9.3", "")

# Add Fields to discharge_reaches to obtain the first x,y coordinates.
arcpy.AddField_management(reachgdb,"xstartr", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
arcpy.AddField_management(reachgdb,"ystartr","DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
arcpy.AddField_management(reachgdb,"x_ystartr", "TEXT")
arcpy.CalculateField_management(reachgdb, "xstartr", "!SHAPE.firstPoint.X!", "PYTHON_9.3", "")
arcpy.CalculateField_management(reachgdb, "ystartr", "!SHAPE.firstPoint.Y!", "PYTHON_9.3", "")
arcpy.CalculateField_management(reachgdb, "x_ystartr", "str(float(!xstartr!))+\",\"+ str(float(!ystartr!))",  "PYTHON_9.3", "")

# Join discharge values based on x,y coordinates of discharge points and start x,y of discharge reaches
arcpy.JoinField_management(reachgdb, "x_ystartr", ptgdb, "x_yp", "drainarea_km2")

#-----------------------------------------------------------------------------------------------------------------------
# get connections (part2) - calculate distance of each reach to outlet in new fields called “down_distance”. Start at the source of each stream where the drainage area is null, move towards the outlet and save all the reach ids. At the outlet, the “down_ distance” is 0. Move back along the same reaches and record the cumulative distance from the outlet.

# create new field to get sum of length and cum length
fields_list = [field.name for field in arcpy.ListFields(reachgdb)]
new_fields_list = ["Down_Distance"]
for new_field in new_fields_list:
    if new_field in fields_list:
        #print new_field + " exists: deleted"
        arcpy.DeleteField_management(reachgdb, new_field)
    arcpy.AddField_management(reachgdb, new_field,"DOUBLE")
    AddMessage("Adding new fields")

# get all drainage area which is null, i.e. at the source of every headwater stream
source_list = []
cursor = arcpy.SearchCursor(reachgdb)
for row in cursor:
    da = row.getValue("drainarea_km2")
    if da == None:
        endxy = row.getValue("x_yendr")
        source_list.append(endxy)
del row, cursor

# start from every source, get all reach ids (rids) by tracing downstream and only update those rids
for source in source_list:
    # get all reaches for source 
    rid_list = []
    cursor = arcpy.SearchCursor(reachgdb)
    for row in cursor:
        tbl_endxy = row.getValue("x_yendr")
        #start at source
        if  tbl_endxy == source:
            s_id = row.getValue("OBJECTID")
            s_endxy = row.getValue("x_yendr")
            rid_list.append(s_id)
            break
    del row, cursor

    # continue after source and add ids to list
    cursor = arcpy.SearchCursor(reachgdb)
    for row in cursor:
        r_startxy = row.getValue("x_ystartr")
        if s_endxy == r_startxy:
            r_id = row.getValue("OBJECTID")
            rid_list.append(r_id)
            #print(s_endxy)
            #print(r_startxy)
            s_endxy = row.getValue("x_yendr")
            #print(s_endxy)  
    del row, cursor
    
    #get reverse list of reach ids to trace upstream towards the source and loop through reverse list and update table
    sum_dist = 0
    for rid in reversed(rid_list):
        cursor = arcpy.UpdateCursor(reachgdb)
        for row in cursor:
            tbl_rid = row.getValue("OBJECTID")
            if rid == tbl_rid:
                rlen = row.getValue("lengthr_m")
                sum_dist = sum_dist + rlen
                dist = row.getValue("Down_Distance")
                #print(sum_dist)
                #print(rid)
                if dist == None:
                    row.setValue("Down_Distance", sum_dist)
                    cursor.updateRow(row)
        del row, cursor


#---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# Sort reaches by downstream distance
reachgdb_sorted= gdb_name + "\\final_segments"
arcpy.Sort_management(reachgdb, reachgdb_sorted, [["Down_Distance", "DESCENDING"]])

#-----------------------------------------------------------------------------------------------------------------
# Add elevation values to segments

#Add Fields to elevation points to obtain the x,y coordinates.
arcpy.AddField_management(ptgdb,"xelev", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
arcpy.AddField_management(ptgdb,"yelev","DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
arcpy.AddField_management(ptgdb,"x_yelev", "TEXT")
arcpy.CalculateField_management(ptgdb, "xelev", "!SHAPE.CENTROID.X!", "PYTHON_9.3", "")
arcpy.CalculateField_management(ptgdb, "yelev", "!SHAPE.CENTROID.Y!", "PYTHON_9.3", "")
arcpy.CalculateField_management(ptgdb, "x_yelev", "str(float(!xelev!))+\",\"+ str(float(!yelev!))",  "PYTHON_9.3", "")

# Join upstream elevation point (upelev) and downstream elevation point (downelev) to reaches based on their respective coordinates
arcpy.JoinField_management(reachgdb_sorted, "x_ystartr", ptgdb, "x_yelev", "elev")
arcpy.AlterField_management(reachgdb_sorted, "elev", "upelev", "", "", "", "NON_NULLABLE", "false")
arcpy.JoinField_management(reachgdb_sorted, "x_yendr", ptgdb, "x_yelev", "elev")
arcpy.AlterField_management(reachgdb_sorted, "elev", "downelev", "", "", "", "NON_NULLABLE", "false")

