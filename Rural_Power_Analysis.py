## This script calculates the stream power. width and critical stream power and stream power gradient using discharge and slope values for reaches in the stream network. 
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


#Allow overwrite of results
arcpy.env.overwriteOutput = True

#Set workspace folder
workspace_folder = GetParameterAsText(0)

##Inputs
seg_gdb = GetParameterAsText(1)
ptgdb = GetParameterAsText(2)

#-----------------------------------------------------------------------------------------------------------
#Process: Delete geodatabase with same name and create new file geodatabase 
gdb_name=str(workspace_folder)+ "\\Rural_scenario.gdb"
arcpy.Delete_management(gdb_name)
arcpy.CreateFileGDB_management(str(workspace_folder), "Rural_scenario.gdb")

#Save shapefile to file geodatabase
strmpowergdb = gdb_name + "\\R_Power"
arcpy.CopyFeatures_management(seg_gdb, strmpowergdb)

#----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# Calculate discharge
#Import coefficient c and x in Q= cA^x.
coeff_c = GetParameterAsText(3)
coeff_x = GetParameterAsText(4)

# Add Field to calculate discharge using Q=cA^x where c and x are coefficcients and A is the drainage area
arcpy.AddField_management(ptgdb,"totalimp_percnt", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
arcpy.CalculateField_management(ptgdb, "totalimp_percnt", "0" , "VB", "")

arcpy.AddField_management(ptgdb,"c", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
arcpy.CalculateField_management(ptgdb, "c", "0.248" , "VB", "")

arcpy.AddField_management(ptgdb,"x", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
arcpy.CalculateField_management(ptgdb, "x", "0.91" , "VB", "")

arcpy.AddField_management(ptgdb,"Q_m3pers", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
expressionq= "!c!*(!drainarea_km2!**!x!)"
arcpy.CalculateField_management(ptgdb, "Q_m3pers", str(expressionq), "PYTHON_9.3", "")

# Add field to discharge points to obtain the x,y coordinates of the points.
arcpy.AddField_management(ptgdb,"xp", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
arcpy.AddField_management(ptgdb,"yp","DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
arcpy.AddField_management(ptgdb,"x_yp", "TEXT")
arcpy.CalculateField_management(ptgdb, "xp", "!SHAPE.CENTROID.X!", "PYTHON_9.3", "")
arcpy.CalculateField_management(ptgdb, "yp", "!SHAPE.CENTROID.Y!", "PYTHON_9.3", "")
arcpy.CalculateField_management(ptgdb, "x_yp", "str(float(!xp!))+\",\"+ str(float(!yp!))",  "PYTHON_9.3", "")

# Add Fields to discharge_reaches to obtain the first x,y coordinates.
arcpy.AddField_management(strmpowergdb,"xstartr", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
arcpy.AddField_management(strmpowergdb,"ystartr","DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
arcpy.AddField_management(strmpowergdb,"x_ystartr", "TEXT")
arcpy.CalculateField_management(strmpowergdb, "xstartr", "!SHAPE.firstPoint.X!", "PYTHON_9.3", "")
arcpy.CalculateField_management(strmpowergdb, "ystartr", "!SHAPE.firstPoint.Y!", "PYTHON_9.3", "")
arcpy.CalculateField_management(strmpowergdb, "x_ystartr", "str(float(!xstartr!))+\",\"+ str(float(!ystartr!))",  "PYTHON_9.3", "")

# Join discharge values based on x,y coordinates of discharge points and start x,y of discharge reaches
arcpy.JoinField_management(strmpowergdb, "x_ystartr", ptgdb, "x_yp", ["drainarea_km2", "totalimp_percnt", "Q_m3pers"])
AddMessage("The calculated rural discharge is saved in R_Power.")

#-----------------------------------------------------------------------------------------------
##Total Stream Power
# Add Field with specific weight of water(9810 N) and strmpower
arcpy.AddField_management(strmpowergdb,"Wg_Nperm3", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
arcpy.CalculateField_management(strmpowergdb, "Wg_Nperm3", "9810" , "VB", "")

arcpy.AddField_management(strmpowergdb,"Power_Wperm", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
expressionpow="!S_mperm_SAVG!*!Q_m3pers!*!Wg_Nperm3!"
arcpy.CalculateField_management(strmpowergdb, "Power_Wperm", str(expressionpow), "PYTHON_9.3", "")
expressionabs = "!Power_Wperm!*-1"
arcpy.CalculateField_management(strmpowergdb, "Power_Wperm", str(expressionabs), "PYTHON_9.3", "")

AddMessage("The calculated total stream power is saved in R_Power.")


#-------------------------------------------------------------------------------------------------------
##Specific Stream Power

# Add Field with width and specific stream power
coeff_a=GetParameterAsText(5)
coeff_b=GetParameterAsText(6)

arcpy.AddField_management(strmpowergdb,"a", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
arcpy.CalculateField_management(strmpowergdb, "a", str(coeff_a) , "VB", "") 
arcpy.AddField_management(strmpowergdb,"b", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
arcpy.CalculateField_management(strmpowergdb, "b", str(coeff_b) , "VB", "")
arcpy.AddField_management(strmpowergdb,"Width_m", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
expressionwidth="!a!*(!drainarea_km2!**!b!)"
arcpy.CalculateField_management(strmpowergdb, "width_m", str(expressionwidth), "PYTHON_9.3", "")

arcpy.AddField_management(strmpowergdb,"SPower_Wperm", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
expressionspow="!Power_Wperm!/!width_m!"
arcpy.CalculateField_management(strmpowergdb, "SPower_Wperm", str(expressionspow), "PYTHON_9.3", "")

AddMessage("The calculated rural specific stream power is saved in R_Power.")

#-----------------------------------------------------------------------------------------------------------------------------------------
## D84 Prediction
##Calculate d84 based on Ferguson (2005) particle mobility model. Model fitting uses Annable (1996) data.

#Add field for d84 prediction
arcpy.AddField_management(strmpowergdb,"D84_mm", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
		
#Equation 16 from Ferguson (2005) Assumption: Di = Db
#constants for d84 prediction
gamma = 9790 # N/m3
kappa = 0.41 # constant from Ferguson 2005 - works for D in mm, power in W/m2
R = 1.65 # submerged specific gravity
rho = 1000 # density of water
theta_cb = 0.045 # shear stress threshold
m =2.80 # roughness multiplier for D84 from Lopez and Barrangan e.g. Hey 1979
gee = 9.81 #acceleration by gravity

#C = log10(30*theta_cb*R/(e*m*!S_mperm!))"
#expressionDb = "((kappa*!SPower_Wperm!/(2.30*rho*log10(30*theta_cb*R/(exp*m*!S_mperm!))))**(2/3))/(theta_cb*R*gee)"

expressionlogC= "math.log10(30*0.045*1.65/(math.exp(1)*2.80*(abs(!S_mperm!))))"
expressionDb = "((((0.41*abs(!SPower_Wperm!))/(2.30*1000*" + str(expressionlogC) + "))**(2.0/3))/(0.045*1.65*9.81))*1000"
arcpy.CalculateField_management(strmpowergdb, "D84_mm", str(expressionDb), "PYTHON_9.3", "")

#----------------------------------------------------------------------------------------------------------
## Stream Power Gradient
gradient =GetParameterAsText(7)

if gradient == "true":

	# add field to get coordinates
	arcpy.AddField_management(strmpowergdb,"xendr_gr", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
	arcpy.AddField_management(strmpowergdb,"yendr_gr","DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
	arcpy.AddField_management(strmpowergdb,"x_yendr_gr", "TEXT")
	arcpy.CalculateField_management(strmpowergdb, "xendr_gr", "!SHAPE.lastPoint.X!", "PYTHON_9.3", "")
	arcpy.CalculateField_management(strmpowergdb, "yendr_gr", "!SHAPE.lastPoint.Y!", "PYTHON_9.3", "")
	arcpy.CalculateField_management(strmpowergdb, "x_yendr_gr", "str(float(!xendr_gr!))+\",\"+ str(float(!yendr_gr!))",  "PYTHON_9.3", "")

	arcpy.AddField_management(strmpowergdb,"xstartr_gr", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
	arcpy.AddField_management(strmpowergdb,"ystartr_gr","DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
	arcpy.AddField_management(strmpowergdb,"x_ystartr_gr", "TEXT")
	arcpy.CalculateField_management(strmpowergdb, "xstartr_gr", "!SHAPE.firstPoint.X!", "PYTHON_9.3", "")
	arcpy.CalculateField_management(strmpowergdb, "ystartr_gr", "!SHAPE.firstPoint.Y!", "PYTHON_9.3", "")
	arcpy.CalculateField_management(strmpowergdb, "x_ystartr_gr", "str(float(!xstartr_gr!))+\",\"+ str(float(!ystartr_gr!))",  "PYTHON_9.3", "")

	# Add field to calculate total and specific stream power gradient by using added coordinates from slopergdb 
	arcpy.AddField_management(strmpowergdb,"PowerGr_Wperm", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
	arcpy.AddField_management(strmpowergdb,"SPowerGr_Wperm", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

	# obtain subsequent reaches start points coordinates and their total stream power
	startrxy_set =set()
	cursorgr=arcpy.SearchCursor(strmpowergdb)
	for row in cursorgr:
		startr_v = row.getValue("x_ystartr_gr")
		startr_pow = row.getValue("Power_Wperm")
		startr_spow = row.getValue("SPower_Wperm")
		startr_val = (startr_v,startr_pow,startr_spow)
		startrxy_set.add(startr_val)
	del row,cursorgr

	# match subsequent reaches start coordinates with ending coordinates of parent reaches and subtract their total stream power
	for sxy, spow, sspow in startrxy_set:
		ucursorgr = arcpy.UpdateCursor(strmpowergdb)
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
					print sxy, exy, spow, epow, gradtp, gradsp
				else:
					gradtp = spow-epow
					gradsp = sspow-espow
					row.setValue("PowerGr_Wperm", gradtp)
					row.setValue("SPowerGr_Wperm", gradsp)
					ucursorgr.updateRow(row)
					print sxy, exy, spow, epow, gradtp, gradsp
		del row, ucursorgr

