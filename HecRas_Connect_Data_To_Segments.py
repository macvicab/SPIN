## Python script: This script will convert hecras results (both storm events and at bridge event), connect the results to points and
## join the points to the stream network if they are within 45m.
## Bridge scour and overtopping will be calculated for river stations located at bridges.
## Inputs: hecras river stations as shapefile, hecras model as .csv, stream reaches with calculated rural stream power
## Written by Kimisha Ghunowa, River Hydraulics Research Group, University of Waterloo. 
## Last edited: Sept 5, 2019
#---------------------------------------------------------------------------------#

#Import the Arc Package
import arcpy
import os
from arcpy import *
from arcpy import env
from arcpy.sa import *
import pandas as pd
import numpy as np

#Enable the Spatial Analyst Extension license
arcpy.CheckOutExtension("Spatial")

#Allow overwrite of files
arcpy.env.overwriteOutput = True

#Set the current workspace for geoprocessing
workspace_folder = GetParameterAsText(0)
env.workspace= workspace_folder

# Import the points shapefile of the river stations
hec_pts = GetParameterAsText(1)

# Import the hecras results (.csv)
hec_csv = GetParameterAsText(2)

# Import the stream segment
strm_reach = GetParameterAsText(3)

# Import the hecras bridge results (.csv)
bridge_analysis = GetParameterAsText(4)
bridge_hec_csv = GetParameterAsText(5)

#------------------------------------------------------------------
## Transform hecrasfile for flood events (.csv) into compatible format

# read file as dataframe (df) by skipping 9 rows and specify column headers 
df = pd.read_csv(hec_csv, header=[0,1])

# remove unnamed cells in column names
for i, col in enumerate(df.columns.levels):
    columns = np.where(col.str.contains('Unnamed'), '', col)
    df.columns.set_levels(columns, level=i, inplace=True)

# combine both rows as headers
col_raw = df.columns
col_raw.tolist()
new_col = pd.Index([e[0] + e[1] for e in col_raw.tolist()])
df.columns = new_col

# transform field name by replace space and symbols with underscore
df.columns = df.columns.str.replace(' ', '_')
df.columns = df.columns.str.replace('(', '_')
df.columns = df.columns.str.replace(')', '')
df.columns = df.columns.str.replace('/', 'per')
df.columns = df.columns.str.replace('.', '_')

# Replace all space in df
df_c = df.replace(' ', '_', regex=True)

#drop rows with none
df_c = df_c.dropna(axis=0, how = 'all')

# drop columns before profile id
df_c1 = df_c.drop(df_c.columns[[0]], axis =1)

df_c1 = df_c1.dropna(axis=0, subset=['Profile'])

# pivot table by making the profile (i.e. storm event) data into columns
df_piv = pd.pivot_table(df_c1, index='River_Sta', columns = 'Profile')

# group stacked columns
df_piv.columns = df_piv.columns.map('_'.join)

#save transformed hec ras file 
hec_csv_f = str(workspace_folder)+ "\\hecras_csv_formatted.csv"
df_piv.to_csv(hec_csv_f)

#------------------------------------------------------------------------------
## Connect river station points to transformed hecras data

#Process: Delete geodatabase with same name and create new file geodatabase 
gdb_name=str(workspace_folder)+ "\\hec2points.gdb"
arcpy.Delete_management(gdb_name)
arcpy.CreateFileGDB_management(str(workspace_folder), "hec2points.gdb")

# convert points shapefile to gdb class
arcpy.FeatureClassToGeodatabase_conversion(hec_pts, gdb_name)
pts_base = str(os.path.basename(hec_pts))
pts_name = os.path.splitext(pts_base)[0]
pts_gdb = str(gdb_name)+ "\\" + str(pts_name)

#convert .csv to gdb table
hec_csv_gdb= arcpy.TableToTable_conversion(hec_csv_f, gdb_name, "hec_data_formatted")

# Join transformed hecras data to hec points shapefile
pts_joined_table = arcpy.JoinField_management(pts_gdb, "RIVER_STA", hec_csv_gdb, "River_Sta")

#Save layer to file geodatabase
hec_pts_gdb= gdb_name + "\\hec_2points_connected"
arcpy.CopyFeatures_management(pts_joined_table, hec_pts_gdb)

#---------------------------------------------------------------------
## Connect river station points with hecras data to stream reach

# snap points to edge of reach 
hec_pts_gdb_c = str(gdb_name) + "\\hec_2points_connected_c"
arcpy.CopyFeatures_management(hec_pts_gdb, hec_pts_gdb_c)
snapenv = [strm_reach, "EDGE", "45 Meters"]
arcpy.Snap_edit(hec_pts_gdb_c, [snapenv])

# Join the points which are snapped to the stream reach data
hec_strm = os.path.join(gdb_name, "hecras_data_connected")
arcpy.SpatialJoin_analysis(strm_reach, hec_pts_gdb_c, hec_strm, "", "", "", "INTERSECT")


###########################################################################
## Bridge Analysis - Connect hecras bridge data to stream reach to calculate bridge scour and overtopping

if bridge_analysis == "true":

    # Transform hec csv into compatible format
    # read file as dataframe by skipping 9 rows and specify column headers
    df_b = pd.read_csv(bridge_hec_csv, header=[0,1])

    # remove unnamed cells in column names
    for i, col in enumerate(df_b.columns.levels):
        columns = np.where(col.str.contains('Unnamed'), '', col)
        df_b.columns.set_levels(columns, level=i, inplace=True)

    #combine both headers
    col_raw = df_b.columns
    col_raw.tolist()
    new_col = pd.Index([e[0] + e[1] for e in col_raw.tolist()])
    df_b.columns = new_col

    # replace space and symbols in column names with underscore
    df_b.columns = df_b.columns.str.replace(' ', '_')
    df_b.columns = df_b.columns.str.replace('(', '_')
    df_b.columns = df_b.columns.str.replace(')', '')
    df_b.columns = df_b.columns.str.replace('/', 'per')
    df_b.columns = df_b.columns.str.replace('.', '_')

    # replace space in dataframe with underscore
    df_bc = df_b.replace(' ', '_', regex=True)

    # drop rows with none
    df_bc = df_bc.dropna(axis=0, how = 'all')

    # pivot table to transform profile from row wise to column wise
    df_piv_b = pd.pivot_table(df_bc, index='River_Sta', columns = 'Profile')

    #group stacked columns
    df_piv_b.columns = df_piv_b.columns.map('_'.join)

    # add new columns to calculate bridge scour
    df_piv_b["Scour_Ratio_2_y_Ex"] = ""
    df_piv_b["Scour_Ratio_5_y_Ex"] = ""
    df_piv_b["Scour_Ratio_10_y_Ex"] = ""
    df_piv_b["Scour_Ratio_25_y_Ex"] = ""
    df_piv_b["Scour_Ratio_50_y_Ex"] = ""
    df_piv_b["Scour_Ratio_100_y_Ex"] = ""
    df_piv_b["Overtop_Ratio_2_y_Ex"] = ""
    df_piv_b["Overtop_Ratio_5_y_Ex"] = ""
    df_piv_b["Overtop_Ratio_10_y_Ex"] = ""
    df_piv_b["Overtop_Ratio_25_y_Ex"] = ""
    df_piv_b["Overtop_Ratio_50_y_Ex"] = ""
    df_piv_b["Overtop_Ratio_100_y_Ex"] = ""

    #save transformed data with new fields
    hec_csv_bf = str(workspace_folder)+ "\\hecras_bridge_formatted.csv"
    df_piv_b.to_csv(hec_csv_bf)

    #-----------------------------------------------------------------------------
    ## Connect transformed bridge data to gdb table. To calculate bridge scour and bridge overtopping, the data for the upstream river station and at the bridge are required.

    # convert csv to gdb table
    bhec_csv_gdb= arcpy.TableToTable_conversion(hec_csv_bf, gdb_name, "hec_bridge_data_formatted")

    # loop through table, find river station at bridge,  extract upstream river station data and perform scour and overtopping calculations at bridge
    # get river stations list
    rid_list = []
    cursor = arcpy.SearchCursor(bhec_csv_gdb)
    for row in cursor:
        rid = row.getValue("River_Sta")
        rid_list.append(rid)
    del row, cursor

    # sort river station list in ascending order
    rid_list.sort()

    # loop through river station id, get data for first river station to calculate data for following river station.

    while len(rid_list) != 0:
        rid_br = rid_list[1] # station at bridge
        rid_up = rid_list[0] # station above bridge
        rid_list.remove(rid_br)
        rid_list.remove(rid_up)

        cursor = arcpy.SearchCursor(bhec_csv_gdb)
        for row in cursor:
            rid_tbl = row.getValue("River_Sta")
            if rid_tbl == rid_up:
                q_up_2 = row.getValue("Q_Channel_m3pers_2_y_Ex")
                q_up_5 = row.getValue("Q_Channel_m3pers_5_y_Ex")
                q_up_10 = row.getValue("Q_Channel_m3pers_10_y_Ex")
                q_up_25 = row.getValue("Q_Channel_m3pers_25_y_Ex")
                q_up_50 = row.getValue("Q_Channel_m3pers_50_y_Ex")
                q_up_100 = row.getValue("Q_Channel_m3pers_100_y_Ex")
                w_up_2 = row.getValue("Top_W_Chnl_m_2_y_Ex")
                w_up_5 = row.getValue("Top_W_Chnl_m_5_y_Ex")
                w_up_10 = row.getValue("Top_W_Chnl_m_10_y_Ex")
                w_up_25 = row.getValue("Top_W_Chnl_m_25_y_Ex")
                w_up_50 = row.getValue("Top_W_Chnl_m_50_y_Ex")
                w_up_100 = row.getValue("Top_W_Chnl_m_100_y_Ex")
                break
        del row, cursor

        cursor = arcpy.UpdateCursor(bhec_csv_gdb)
        for row in cursor:
            rid_tbl = row.getValue("River_Sta")
            if rid_tbl == rid_br:
                q_b_2 = row.getValue("Q_Bridge_m3pers_2_y_Ex")
                q_b_5 = row.getValue("Q_Bridge_m3pers_5_y_Ex")
                q_b_10 = row.getValue("Q_Bridge_m3pers_10_y_Ex")
                q_b_25 = row.getValue("Q_Bridge_m3pers_25_y_Ex")
                q_b_50 = row.getValue("Q_Bridge_m3pers_50_y_Ex")
                q_b_100 = row.getValue("Q_Bridge_m3pers_100_y_Ex")
                w_b_2 = row.getValue("Deck_Width_m_2_y_Ex")
                w_b_5 = row.getValue("Deck_Width_m_5_y_Ex")
                w_b_10 = row.getValue("Deck_Width_m_10_y_Ex")
                w_b_25 = row.getValue("Deck_Width_m_25_y_Ex")
                w_b_50 = row.getValue("Deck_Width_m_50_y_Ex")
                w_b_100 = row.getValue("Deck_Width_m_100_y_Ex")

                q_t_2 = row.getValue("Q_Total_m3pers_2_y_Ex")
                q_t_5 = row.getValue("Q_Total_m3pers_5_y_Ex")
                q_t_10 = row.getValue("Q_Total_m3pers_10_y_Ex")
                q_t_25 = row.getValue("Q_Total_m3pers_25_y_Ex")
                q_t_50 = row.getValue("Q_Total_m3pers_50_y_Ex")
                q_t_100 = row.getValue("Q_Total_m3pers_100_y_Ex")

                if q_up_2 == None or q_up_5 == None or q_up_10 == None or q_up_25 == None or q_up_50 == None or q_up_100 == None or q_b_2 == None or q_b_5 == None or q_b_10 == None or q_b_25 == None or q_b_50 == None or q_b_100 == None or w_up_2 == None or w_up_5 == None or w_up_10 == None or w_up_25 == None or w_up_50 == None or w_up_100 == None or w_b_2 == None or w_b_5 == None or w_b_10 == None or w_b_25 == None or w_b_50 == None or w_b_100 == None:
                    row.setValue("Scour_Ratio_2_y_Ex", None)
                    row.setValue("Scour_Ratio_5_y_Ex", None)
                    row.setValue("Scour_Ratio_10_y_Ex", None)
                    row.setValue("Scour_Ratio_25_y_Ex", None)
                    row.setValue("Scour_Ratio_50_y_Ex", None)
                    row.setValue("Scour_Ratio_100_y_Ex", None)
                    row.setValue("Overtop_Ratio_2_y_Ex", None)
                    row.setValue("Overtop_Ratio_5_y_Ex", None)
                    row.setValue("Overtop_Ratio_10_y_Ex", None)
                    row.setValue("Overtop_Ratio_25_y_Ex", None)
                    row.setValue("Overtop_Ratio_50_y_Ex", None)
                    row.setValue("Overtop_Ratio_100_y_Ex", None)
                    cursor.updateRow(row)
                else:
                    scour_2 = ((q_b_2/q_up_2)**0.857)*((w_up_2/w_b_2)**0.59)
                    scour_5 = ((q_b_5/q_up_5)**0.857)*((w_up_5/w_b_5)**0.59)
                    scour_10 = ((q_b_10/q_up_10)**0.857)*((w_up_10/w_b_10)**0.59)
                    scour_25 = ((q_b_25/q_up_25)**0.857)*((w_up_25/w_b_25)**0.59)
                    scour_50 = ((q_b_50/q_up_50)**0.857)*((w_up_50/w_b_50)**0.59)
                    scour_100 = ((q_b_100/q_up_100)**0.857)*((w_up_100/w_b_100)**0.59)
                    overtop_2 = q_t_2/q_b_2
                    overtop_5 = q_t_5/q_b_5
                    overtop_10 = q_t_10/q_b_10
                    overtop_25 = q_t_25/q_b_25
                    overtop_50 = q_t_50/q_b_50
                    overtop_100 = q_t_100/q_b_100
                    row.setValue("Scour_Ratio_2_y_Ex", scour_2)
                    row.setValue("Scour_Ratio_5_y_Ex", scour_5)
                    row.setValue("Scour_Ratio_10_y_Ex", scour_10)
                    row.setValue("Scour_Ratio_25_y_Ex", scour_25)
                    row.setValue("Scour_Ratio_50_y_Ex", scour_50)
                    row.setValue("Scour_Ratio_100_y_Ex", scour_100)
                    row.setValue("Overtop_Ratio_2_y_Ex", overtop_2)
                    row.setValue("Overtop_Ratio_5_y_Ex", overtop_5)
                    row.setValue("Overtop_Ratio_10_y_Ex", overtop_10)
                    row.setValue("Overtop_Ratio_25_y_Ex", overtop_25)
                    row.setValue("Overtop_Ratio_50_y_Ex", overtop_50)
                    row.setValue("Overtop_Ratio_100_y_Ex", overtop_100)
                    cursor.updateRow(row)
        del row, cursor

    # create a copy of table
    bhec_csv_gdb_c = gdb_name + "\\bridge_scour_overtop_ratios_only"
    arcpy.Copy_management(bhec_csv_gdb, bhec_csv_gdb_c)

    # delete empty rows from final table where all the calculations are null
    cursor =  arcpy.UpdateCursor(bhec_csv_gdb_c)
    for row in cursor:
        s_2 = row.getValue("Scour_Ratio_2_y_Ex")
        s_5 = row.getValue("Scour_Ratio_5_y_Ex")
        s_10 = row.getValue("Scour_Ratio_10_y_Ex")
        s_25 = row.getValue("Scour_Ratio_25_y_Ex")
        s_50 = row.getValue("Scour_Ratio_50_y_Ex")
        s_100 = row.getValue("Scour_Ratio_100_y_Ex")
        if s_2 == None and s_5 == None and s_10 == None and s_25 == None and s_50 == None and s_100 == None:
            cursor.deleteRow(row)
    del row, cursor

    #---------------------------------------------------------------------------
    ## Connect bridge calculations to a copy of river stations points file 

    # Make a copy of points file
    b_pts_gdb= gdb_name + "\\bridge_2points_connected"
    arcpy.CopyFeatures_management(pts_gdb, b_pts_gdb)

    # Join bridge calculations to hec points shapefile
    b_pts_joined = arcpy.JoinField_management(b_pts_gdb, "RIVER_STA", bhec_csv_gdb_c, "River_Sta")

    #-----------------------------------------------------------------------------------------------------------------------
    #Connect points to stream reach

    # snap points to edge of reach 
    b_pts_joined_c = str(gdb_name) + "\\bridge_2points_c"
    arcpy.CopyFeatures_management(b_pts_joined, b_pts_joined_c)
    snapenv = [strm_reach, "EDGE", "45 Meters"]
    arcpy.Snap_edit(b_pts_joined_c, [snapenv])

    # Join the points to the stream reach
    bridge_strm = os.path.join(gdb_name, "bridge_2strm_connected")
    arcpy.SpatialJoin_analysis(strm_reach, b_pts_joined_c, bridge_strm, "", "", "", "INTERSECT")

    # join fields of bridge calculations to strm reach 
    arcpy.JoinField_management(hec_strm, "OBJECTID" , bridge_strm, "OBJECTID", ["Scour_Ratio_2_y_Ex","Scour_Ratio_5_y_Ex","Scour_Ratio_10_y_Ex","Scour_Ratio_25_y_Ex","Scour_Ratio_50_y_Ex", "Scour_Ratio_100_y_Ex", "Overtop_Ratio_2_y_Ex", "Overtop_Ratio_5_y_Ex", "Overtop_Ratio_10_y_Ex", "Overtop_Ratio_25_y_Ex", "Overtop_Ratio_50_y_Ex", "Overtop_Ratio_100_y_Ex"])

#---------------------------------------------------------------------------------------------------------------------------------------