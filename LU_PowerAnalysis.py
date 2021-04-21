## This script finds the  discharge along the stream network by relating it to imperviousness.
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

#Set workspace folder
workspace_folder = GetParameterAsText(0)
env.workspace= str(workspace_folder)

#Allow overwrite of results
arcpy.env.overwriteOutput = True

#Import discharge points
disch_pt = GetParameterAsText(1)

#Import drainage area polygons shapefile
dischpolygdiss = GetParameterAsText(2)

#Define following variables
lu_path = GetParameterAsText(3)
disch_reach= GetParameterAsText(4)
gradient = GetParameterAsText(5)
coeff_c=GetParameterAsText(6) #Note:hardcoded
coeff_x=GetParameterAsText(7) #Note:hardcoded
coeff_b=GetParameterAsText(8) #Note:hardcoded
coeff_a=GetParameterAsText(9) #Note:hardcoded
coeff_b=GetParameterAsText(10) #Note:hardcoded


#Create file geodatabase to store final results
#Process: Delete geodatabase with same name and create new file geodatabase 
gdb_name=str(workspace_folder)+ "\\urban_lu_scenario.gdb"
arcpy.Delete_management(gdb_name)
arcpy.CreateFileGDB_management(str(workspace_folder), "urban_lu_scenario.gdb")


##---------------------------------------------------------------------------------------------------------
# Copy discharge drainage area polygons to geodatabase 
arcpy.FeatureClassToGeodatabase_conversion(dischpolygdiss,gdb_name)
dischpt_dagdb= gdb_name + "\\final_da"

# Add field to calculate drainage area
arcpy.AddField_management(dischpt_dagdb, "drainarea_km2", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

# Calculate drainage area
arcpy.CalculateField_management(dischpt_dagdb,"drainarea_km2","!shape.area@squarekilometers!","PYTHON_9.3","#")

# Copy discharge points to gdb
disch_ptgdb= str(gdb_name) + "\\strm_ptcopy"
arcpy.CopyFeatures_management(disch_pt, disch_ptgdb)
arcpy.DeleteField_management(disch_ptgdb, ["Join_Count","TARGET_FID","Id","ORIG_FID"])

##----------------------------------------------------------------------------------------------------------
# Copy landuse imperviousness polygons to geodatabase
#Already defined at the beginning: lu_path = GetParameterAsText(3)
#lu_path = "C:\GIS_Research\Masters_Thesis\Ganet_ModelBuilding\Scripts\Test\imp_ganet.shp"
arcpy.FeatureClassToGeodatabase_conversion(lu_path,gdb_name)
lu_pathname = os.path.splitext(os.path.basename(str(lu_path)))[0]
lu_gdb = gdb_name + "\\" + str(lu_pathname)

#xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
# old step where all da intersect with lu
# Intersect landuse with drainage area to find which landuse types each contain
# dischda_lugdb = gdb_name + "\\dischda_lu"
# arcpy.Intersect_analysis([dischpt_dagdb,lu_gdb], dischda_lugdb, "ALL", "", "INPUT")
#xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
# new step to seperate DAs from all das. intersect will occur seperately for each da then merged.

# create new gdb to store intersect layers
# Process: Delete geodatabase with same name and create new file geodatabase 
gdb_poly=str(workspace_folder)+ "\\poly_da.gdb"
arcpy.Delete_management(gdb_poly)
arcpy.CreateFileGDB_management(str(workspace_folder), "poly_da.gdb")

# split das by pointids
arcpy.SplitByAttributes_analysis(dischpt_dagdb, gdb_poly, ['POINTID'])

# get list of pointids
arcpy.env.workspace = gdb_poly
dapolylist = arcpy.ListFeatureClasses()

# create new gdb to store intersect layers
#Process: Delete geodatabase with same name and create new file geodatabase 
gdb_dalu = str(workspace_folder)+ "\\poly_dalu.gdb"
arcpy.Delete_management(gdb_dalu)
arcpy.CreateFileGDB_management(str(workspace_folder), "poly_dalu.gdb")

# Loop through da list and intersect with landuse.
for da in dapolylist:
	dapoly = gdb_poly + "\\" + str(da)
	#print(dapoly)
	dalu_gdb = gdb_dalu + "\\dalu_" + str(da)
	#print(dalu_gdb)
	arcpy.Intersect_analysis([dapoly,lu_gdb], dalu_gdb, "ALL", "", "INPUT")

# Merge all watershed shapefiles together 
arcpy.env.workspace = gdb_dalu
dalulist = arcpy.ListFeatureClasses()

# create an empty copy of the first file
dalu1 = dalulist[0]
dalu1_path = gdb_dalu + "\\" + str(dalu1)
alldalu_path = gdb_dalu + "\\" + str("all_dalu")
arcpy.CopyFeatures_management(dalu1_path, alldalu_path)
arcpy.DeleteRows_management(alldalu_path)

# loop through each dalu poly and update shapefile
fields = [f.name for f in arcpy.ListFields(alldalu_path)] + ['SHAPE@']
del fields[2] # remove 3rd col

for dalu in dalulist:
	dalu_x = gdb_dalu + "\\" + str(dalu)
	cursor = arcpy.da.SearchCursor(dalu_x, fields)
	cursor1 = arcpy.da.InsertCursor(alldalu_path, fields)
	for row in cursor:
		cursor1.insertRow(row)
del cursor
del cursor1

dischda_lugdb = gdb_dalu + "\\" + str("all_dalu")
#---------------------------------------------------------------------------------------------------------------------
# Add field to calculate drainage area
arcpy.AddField_management(dischda_lugdb, "luarea_km2", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

# Calculate drainage area based 
arcpy.CalculateField_management(dischda_lugdb,"luarea_km2","!shape.area@squarekilometers!","PYTHON_9.3","#")

# Add field to calculate imperviousness for each land use type 
arcpy.AddField_management(dischda_lugdb, "impervOfluarea_km2", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

#Calculate % area of imperviousness
# percent= "((!imper_pcnt!)/100)"
arcpy.CalculateField_management(dischda_lugdb,"impervOfluarea_km2","!imper_pcnt!*0.01*!luarea_km2!","PYTHON_9.3","#")

#Create summary stats table for calculating the sum of imperviousness for each drainage area
sumimperv = str(gdb_name) + "\\sumimper_da"

# Process: Summary Statistics
arcpy.Statistics_analysis(dischda_lugdb, sumimperv, "impervOfluarea_km2 SUM", "POINTID")

# Join sum of imperviousness area to drainage areas
# Process: Join Field
arcpy.JoinField_management(dischpt_dagdb, "OBJECTID", sumimperv, "POINTID", "SUM_impervOfluarea_km2")

# Add field to calculate total imperviousness (=sum imperviousness area/ drainage area) for each drainage area 
arcpy.AddField_management(dischpt_dagdb, "totalimp_percnt", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

# Calculate total imperviousness (=sum imperviousness area/ drainage area)
ratio= "((!SUM_impervOfluarea_km2!)/(!drainarea_km2!))"
arcpy.CalculateField_management(dischpt_dagdb,"totalimp_percnt",ratio +"*100","PYTHON_9.3","#")

# Process: Join Field of drainage area total imp and drainage_area_km2 with discharge points
arcpy.JoinField_management(disch_ptgdb, "POINTID",dischpt_dagdb, "POINTID", "totalimp_percnt")
arcpy.JoinField_management(disch_ptgdb, "POINTID",dischpt_dagdb, "POINTID", "drainarea_km2")

##-------------------------------------------------------------------------------------------
## Calculate urban discharge
#Add Field to calculate discharge using Q=cA^x(IA^b) where c, x and b are coefficcients, A is the drainage area and IA is total imperviousness percentage.

arcpy.AddField_management(disch_ptgdb,"urban_c", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
arcpy.CalculateField_management(disch_ptgdb, "urban_c", "0.248" , "VB", "")

arcpy.AddField_management(disch_ptgdb,"urban_x", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
arcpy.CalculateField_management(disch_ptgdb, "urban_x", "0.91" , "VB", "")

arcpy.AddField_management(disch_ptgdb,"urban_b", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
arcpy.CalculateField_management(disch_ptgdb, "urban_b", "0.3" , "VB", "")
 
arcpy.AddField_management(disch_ptgdb, "Q_m3pers", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
expressionuq= "!urban_c!*(!drainarea_km2!**!urban_x!)*(!totalimp_percnt!**!urban_b!)"
arcpy.CalculateField_management(disch_ptgdb,"Q_m3pers",str(expressionuq),"PYTHON_9.3","#")

# Add field to discharge points to obtain the x,y coordinates of the points
arcpy.AddField_management(disch_ptgdb,"xp", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
arcpy.AddField_management(disch_ptgdb,"yp","DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
arcpy.AddField_management(disch_ptgdb,"x_yp", "TEXT")

arcpy.CalculateField_management(disch_ptgdb, "xp", "!SHAPE.CENTROID.X!", "PYTHON_9.3", "")
arcpy.CalculateField_management(disch_ptgdb, "yp", "!SHAPE.CENTROID.Y!", "PYTHON_9.3", "")

arcpy.CalculateField_management(disch_ptgdb, "x_yp", "str(float(!xp!))+\",\"+ str(float(!yp!))",  "PYTHON_9.3", "")

##-------------------------------------------------------------------------------------------------
## Joining discharge to segments 

# Copy dischreaches to gdb
disch_reachesgdb = str(gdb_name) + "\\LU_Pow"
arcpy.CopyFeatures_management(disch_reach, disch_reachesgdb)

# Add Fields to discharge_reaches to obtain the first x,y coordinates.
arcpy.AddField_management(disch_reachesgdb,"xstartr", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
arcpy.AddField_management(disch_reachesgdb,"ystartr","DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
arcpy.AddField_management(disch_reachesgdb,"x_ystartr", "TEXT")

arcpy.CalculateField_management(disch_reachesgdb, "xstartr", "!SHAPE.firstPoint.X!", "PYTHON_9.3", "")
arcpy.CalculateField_management(disch_reachesgdb, "ystartr", "!SHAPE.firstPoint.Y!", "PYTHON_9.3", "")
arcpy.CalculateField_management(disch_reachesgdb, "x_ystartr", "str(float(!xstartr!))+\",\"+ str(float(!ystartr!))",  "PYTHON_9.3", "")
# Join discharge values based on x,y coordinates of discharge points and start x,y of discharge reaches
arcpy.JoinField_management(disch_reachesgdb, "x_ystartr", disch_ptgdb, "x_yp", ["drainarea_km2", "totalimp_percnt", "Q_m3pers"])

#-------------------------------------------------------------------------------------------------------------------------
## Calculate total power and specific stream power

# Add Field with specific weight of water(9810 N) and strmpower
arcpy.AddField_management(disch_reachesgdb,"Wg_Nperm3", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
arcpy.CalculateField_management(disch_reachesgdb,"Wg_Nperm3", "9810" , "VB", "")

arcpy.AddField_management(disch_reachesgdb,"Power_Wperm", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
expressionpow="!S_mperm_SAVG!*!Q_m3pers!*!Wg_Nperm3!"
arcpy.CalculateField_management(disch_reachesgdb, "Power_Wperm", str(expressionpow), "PYTHON_9.3", "")
expressionabs = "!Power_Wperm!*-1"
arcpy.CalculateField_management(disch_reachesgdb, "Power_Wperm", str(expressionabs), "PYTHON_9.3", "")

#-----------------------------------------------------------------------------------------------------------------------------
## Calculate specific stream power

# Add Field with width and specific stream power

arcpy.AddField_management(disch_reachesgdb,"a", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
arcpy.CalculateField_management(disch_reachesgdb, "a", "1.16", "VB", "") 
arcpy.AddField_management(disch_reachesgdb,"b", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
arcpy.CalculateField_management(disch_reachesgdb, "b", "0.508", "VB", "")
arcpy.AddField_management(disch_reachesgdb,"Width_m", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
expressionwidth="!a!*(!drainarea_km2!**!b!)"
arcpy.CalculateField_management(disch_reachesgdb, "width_m", str(expressionwidth), "PYTHON_9.3", "")

arcpy.AddField_management(disch_reachesgdb,"SPower_Wperm", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
expressionspow = "!Power_Wperm!/!width_m!"
arcpy.CalculateField_management(disch_reachesgdb, "SPower_Wperm", str(expressionspow), "PYTHON_9.3", "")


#---------------------------------------------------------------------------------------------------------------------------------------------------------------------
## Stream Power Gradient

if gradient == "true":
	# add field to get coordinates
	arcpy.AddField_management(disch_reachesgdb,"xendr_gr", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
	arcpy.AddField_management(disch_reachesgdb,"yendr_gr","DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
	arcpy.AddField_management(disch_reachesgdb,"x_yendr_gr", "TEXT")
	arcpy.CalculateField_management(disch_reachesgdb, "xendr_gr", "!SHAPE.lastPoint.X!", "PYTHON_9.3", "")
	arcpy.CalculateField_management(disch_reachesgdb, "yendr_gr", "!SHAPE.lastPoint.Y!", "PYTHON_9.3", "")
	arcpy.CalculateField_management(disch_reachesgdb, "x_yendr_gr", "str(float(!xendr_gr!))+\",\"+ str(float(!yendr_gr!))",  "PYTHON_9.3", "")

	arcpy.AddField_management(disch_reachesgdb,"xstartr_gr", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
	arcpy.AddField_management(disch_reachesgdb,"ystartr_gr","DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
	arcpy.AddField_management(disch_reachesgdb,"x_ystartr_gr", "TEXT")
	arcpy.CalculateField_management(disch_reachesgdb, "xstartr_gr", "!SHAPE.firstPoint.X!", "PYTHON_9.3", "")
	arcpy.CalculateField_management(disch_reachesgdb, "ystartr_gr", "!SHAPE.firstPoint.Y!", "PYTHON_9.3", "")
	arcpy.CalculateField_management(disch_reachesgdb, "x_ystartr_gr", "str(float(!xstartr_gr!))+\",\"+ str(float(!ystartr_gr!))",  "PYTHON_9.3", "")

	# Add field to calculate total and specific stream power gradient by using added coordinates from slopergdb 
	arcpy.AddField_management(disch_reachesgdb,"PowerGr_Wperm", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
	arcpy.AddField_management(disch_reachesgdb,"SPowerGr_Wperm", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

	# obtain subsequent reaches start points coordinates and their total stream power
	startrxy_set =set()
	cursorgr=arcpy.SearchCursor(disch_reachesgdb)
	for row in cursorgr:
		startr_v = row.getValue("x_ystartr_gr")
		startr_pow = row.getValue("Power_Wperm")
		startr_spow = row.getValue("SPower_Wperm")
		startr_val = (startr_v,startr_pow,startr_spow)
		startrxy_set.add(startr_val)
	del row,cursorgr

	# match subsequent reaches start coordinates with ending coordinates of parent reaches and subtract their total stream power
	for sxy, spow, sspow in startrxy_set:
		ucursorgr = arcpy.UpdateCursor(disch_reachesgdb)
		for row in ucursorgr:
			exy = row.getValue("x_yendr_gr")
			epow = row.getValue("Power_Wperm")
			espow =row.getValue("SPower_Wperm")
			if sxy == exy:
				if spow is None or sspow is None or epow is None or espow is None:
					gradtp = None
					gradsp = None
					row.setValue("PowerGr_Wperm", gradtp)
					row.setValue("SPowerGr_Wperm", gradsp)
					ucursorgr.updateRow(row)
					#print sxy, exy, spow, epow, gradtp, gradsp
				else:
					gradtp = spow-epow
					gradsp = sspow-espow
					row.setValue("PowerGr_Wperm", gradtp)
					row.setValue("SPowerGr_Wperm", gradsp)
					ucursorgr.updateRow(row)
					#print sxy, exy, spow, epow, gradtp, gradsp
		del row, ucursorgr

