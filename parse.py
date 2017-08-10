#!/usr/bin/env python

import sqlite3
import csv
import tarfile
import tempfile
import shutil
import os
import argparse

def main():
	"""
	This script is a convenience utility allowing users to get a human readable overview
	summary of the database structure of a Vive system.  The script can be run without
	arguments on a Vive Hub or can be given a path to a database file or support file to
	run on.  The script will output an HTML "outline" style summary of the system structure
	to stdout.

	You'll probably want to pipe the output of the script to a file for
	later analysis.  Usage in that way may look like this when run on a Vive Hub:

		./parse15.py > project.html

	Running the script in a similar way on a host machine when given a support file
	would look like this:

		./parse15.py -s mysupportfile.tar.gz > project.html

	If running this script on Windows, you will need to invoke the python interpretter
	directly:

		python parse15.py -s mysupportfile.tar.gz > project.html

	"""

	# Define a private function for use with argparse to check file existence
	def _fileexists(path) :
		if not os.path.isfile(path) :
			raise argparse.ArgumentTypeError("File %s is not a valid file or does not exist." % path)
		return path

	# Parse the command line arguments
	parser = argparse.ArgumentParser(description='Dump the programming of a Vive system from a database or support file.')
	parser.add_argument('-d', '--database-path', type=_fileexists, help='Path to the database file')
	parser.add_argument('-s', '--support-file', type=_fileexists, help='Path to a support file to use to obtain system devices')
	args = parser.parse_args()

	# Get the database from either the support file or directly
	if args.support_file is not None:
		# We should process a support file instead of a database (and obtain the database from that file)
		tar = tarfile.open(args.support_file, "r:gz")
		info = [s for s in tar if s.name == "./supportfile/lutron-db.sqlite"]
		if len(info) == 1:
			# Now we need to extract the db and copy it to a temporary file
			f = tar.extractfile(info[0])
			temp = tempfile.NamedTemporaryFile(delete=False)
			shutil.copyfileobj(f, temp)
			temp.close()

			# Now we can open the file as a sqlite database (finally) and write the config
			dumpproject(temp.name)

			# Finally, cleanup our stuff
			os.remove(temp.name)
		else:
			parser.error("Invalid support file (couldn't find database) - %s"%args.support_file)
	else:
		# If there is no database path specified, attempt to use the default
		if args.database_path is None:
			args.database_path = "/var/db/lutron-db.sqlite"

			# Make sure that the default file exists
			if not os.path.isfile(args.database_path) :
				parser.error('Cannot find default database file at "%s", please specify a valid path'%args.database_path)

		# Process this as a database file
		dumpproject(args.database_path)

def dumpproject(dbpath):
	
	# First connect to the database
	conn = sqlite3.connect(dbpath)
	c = conn.cursor()
	
	print("""
			<!-- JS -->
			<script src="https://ajax.googleapis.com/ajax/libs/jquery/3.1.1/jquery.min.js"></script>
			<script type="text/javascript">
				  $(document).ready(function($) {
					$('#showall').click(function(){
					  //Expand all areas
					  $('.devices').show('fast');
					});
					
					$('#hideall').click(function(){
					  //Collapse all areas
					  $('.devices').hide('fast');
					});
					
					$('.area').click(function(e){
					  //Expand or collapse all assigned_dev
					  if (e.target !== this)
							return;
					  $(this).children().toggle('fast');

					});
					
					$('.control_device').click(function(e){
					  //Expand or collapse all assigned_dev
					  if (e.target !== this)
							return;
					  $(this).next().toggle('fast');

					});
					
					
				  });
			</script>

			
			<!-- CSS -->
			<style type='text/css'>
		
				
	
				.area {color: blue; font-size: large}
				.area {cursor: pointer;}
				
				.control_device {color: black; cursor: pointer;}
				
				.assigned_devices {color: purple; font-style: italic; cursor: text;}
				
				.load_controller {color: green; cursor: text;}
		
				#hub_info {font-weight: bold; font-size: large;}
			</style>

			
		  """)
	print("<input type='button' value='Print' onClick='window.print()'>")
	print("<div id='hub_info'>") #HTML Open the hub info Div
	
	
	# Now get the hub serial number
	c.execute('SELECT Name, SerialNumber FROM Device WHERE DeviceID="1"')
	hubs = c.fetchall()
	for hub in hubs :
		hub_name = hub[0]
		hub_serial = hub[1]
		print("Hub Serial: %08X"%(hub_serial))
		print("<br />")
		
	# Now get the Wifi Name
	c.execute('SELECT Ssid FROM WifiSettings')
	wifis = c.fetchall()
	for wifi in wifis :
		wifi_name = wifi[0]
		print("Wifi Name: %s"%(wifi_name))
		print("<br /><textarea rows='4' cols='30' placeholder='Enter notes here, e.g. The WiFi Password is Lutron123!'></textarea><br />")
	
	
	print("<a href ='#' id ='showall' title='Expand All Areas'>&#8650;</a> | <a href ='#' id ='hideall' title='Collapse All Areas'>&#8649;</a>")
	print("</div><br /><div id='areas'>") #HTML Close the hub info Div, Open the areas div
	
	

	
	# Now get all of the areas in the system
	c.execute('SELECT AreaID, Name FROM Area WHERE Name != "root"')
	area_rows = c.fetchall()

	# For each of the areas in the system, get all of the devices
	for area_row in area_rows :
		# Store the column values in a named variable for easy reference
		area_id = area_row[0]
		area_name = area_row[1]

		# Get all of the devices in the area
		c.execute(
			'''
			SELECT DeviceID, Name, Device.DeviceClassInfoID, SerialNumber, DeviceClassInfo.ModelNumber, DeviceClassInfo.ShortDescription, FirmwareRevision
			FROM Device 
			JOIN DeviceClassInfo ON (Device.DeviceClassInfoID=DeviceClassInfo.DeviceClassInfoID) 
			WHERE ContainerObjectID = ? 
			AND ContainerObjectTypeID = 2
			''', (area_id,)
			)
		device_rows = c.fetchall()
		
		
		print("<div id= '%s' class= 'area'>")%(area_name) #HTML open Area Div
		print("Area: %s (There are %d total devices in this Area)"%(area_name, len(device_rows)))
		print("<div id='%s_devices' class= 'devices'><ul>")%(area_name) #HTML Open devices Div, open unordered list
		
		# Create a list of Pico device class info IDs
		pico_device_class_info_ids = [
			12, # Pico Remote Control 3-Button with Raise/Lower
			21, # Pico Remote Control 1-Button
			22, # Pico Remote Control 2-Button
			23, # Pico Remote Control 2-Button with Raise/Lower
			24, # Pico Remote Control 3-Button
			25, # Pico Remote Control 3-Button with Raise/Lower
			32, # 4-Group RF Remote Control
			33, # Pico Remote Control 4-Button
			34, # Pico Remote Control 4-Button with Raise/Lower
			35  # Pico Remote Control 4-Button 2-Group
		]

		# Create a list of Occupancy Sensor device class info IDs
		occ_sensor_device_class_info_ids = [
			11 # Radio Powr Savr Wireless Ceiling-Mounted Occ/Vac Sensor
		]

		# Create a list of Daylight Sensor device class info IDs
		daylight_sensor_device_class_info_ids = [
			46 # Radio Powr Savr Wireless Daylight Sensor
		]

		# For each device in the area, print and get programming (for Picos, Occ and Daylight Sensors)
		for device_row in device_rows :
			# Store the column values in a named variable for easy reference
			device_id = device_row[0]
			device_name = device_row[1]
			device_class_info_id = device_row[2]
			device_serial_number = device_row[3]
			device_designer_tag = device_row[4]
			device_short_descr = device_row[5]
			device_fw_rev = device_row[6]

			if device_class_info_id in pico_device_class_info_ids :
				# This is a Pico, get the devices that it is programmed to
				c.execute(
					'''
					SELECT DISTINCT Device.Name, Device.SerialNumber, DeviceClassInfo.ModelNumber, DeviceClassInfo.ShortDescription
					FROM Button
					JOIN ProgrammingModel USING (ProgrammingModelID)
					JOIN Preset USING (ProgrammingModelID)
					JOIN PresetAssignment USING (PresetID)
					JOIN Zone ON (PresetAssignment.AssignableObjectID = Zone.ZoneID AND PresetAssignment.AssignableObjectTypeID = 15)
					JOIN SwitchLegController ON (Zone.AssociatedSwitchLegControllerID = SwitchLegController.SwitchLegControllerID)
					JOIN Device ON (Device.DeviceID = SwitchLegController.DeviceID)
					JOIN DeviceClassInfo ON (Device.DeviceClassInfoID=DeviceClassInfo.DeviceClassInfoID)
					WHERE Button.DeviceID = ?
					''', (device_id,)
					)
				programmed_devices_rows = c.fetchall()
				print("<div id='0x%08X' class= 'control_device'>"%(device_serial_number)) #HTML open Div with ID of Device
				print("    %s: %s (SN: %08X) (This Pico controls %d devices)"%
					(device_designer_tag, device_name, device_serial_number, len(programmed_devices_rows)))
				print("</div><div id ='0x%08X_assigned_devices' class='assigned_devices'><ul>"%(device_serial_number)) #HTML Close Div, Open Assigned Devices Div, Open Unordered List
				
				for programmed_device_row in programmed_devices_rows :
					# Store the column values in a named variable for easy reference
					programmed_device_name = programmed_device_row[0]
					programmed_device_serial_number = programmed_device_row[1]
					programmed_device_designer_tag = programmed_device_row[2]
					programmed_device_short_descr = programmed_device_row[3]

					# Print the assigned device name and serial
					print("<li>") #HTML List Item
					print("        %s: %s (SN: %08X)"%(programmed_device_designer_tag, programmed_device_name, programmed_device_serial_number))
					print("</li>") #HTML List Item
				print("</ul></div>") #HTML Close Unordered List, Close Div
			elif device_class_info_id in occ_sensor_device_class_info_ids :
				# This is an occupancy sensor, get the devices that it is programmed to
				c.execute(
					'''
					SELECT DISTINCT Device.Name, Device.SerialNumber, DeviceClassInfo.ModelNumber, DeviceClassInfo.ShortDescription
					FROM OccupancySensorConnection
					JOIN OccupancySensor USING(OccupancySensorID)
					JOIN OccupancySensorAssociation USING(OccupancySensorID)
					JOIN SwitchLegController ON (OccupancySensorAssociation.SwitchLegControllerID = SwitchLegController.SwitchLegControllerID)
					JOIN Device ON (Device.DeviceID = SwitchLegController.DeviceID)
					JOIN DeviceClassInfo ON (Device.DeviceClassInfoID=DeviceClassInfo.DeviceClassInfoID)
					WHERE OccupancySensorConnection.DeviceID = ?
					''', (device_id,)
					)
				programmed_devices_rows = c.fetchall()
				print("<div id='0x%08X' class= 'control_device'>"%(device_serial_number)) #HTML open Div with ID of Device
				print("    %s: %s (SN: %08X) (This Occupancy Sensor controls %d devices)"%
					(device_designer_tag, device_name, device_serial_number, len(programmed_devices_rows)))
				print("</div><div id ='0x%08X_assigned_devices' class='assigned_devices'><ul>"%(device_serial_number)) #HTML Close Div, Open Assigned Devices Div, Open Unordered List
				
				for programmed_device_row in programmed_devices_rows :
					# Store the column values in a named variable for easy reference
					programmed_device_name = programmed_device_row[0]
					programmed_device_serial_number = programmed_device_row[1]
					programmed_device_designer_tag = programmed_device_row[2]
					programmed_device_short_descr = programmed_device_row[3]

					# Print the assigned device name and serial
					print("<li>") #HTML List Item
					print("        %s: %s (SN: %08X)"%(programmed_device_designer_tag, programmed_device_name, programmed_device_serial_number))
					print("</li>") #HTML List Item
				print("</ul></div>") #HTML Close Unordered List, Close Div
				
			elif device_class_info_id in daylight_sensor_device_class_info_ids :
				# This is a daylight sensor, get the devices that it is programmed to
				c.execute(
					'''
					SELECT DISTINCT Device.Name, Device.SerialNumber, DeviceClassInfo.ModelNumber, DeviceClassInfo.ShortDescription
					FROM DaylightSensorConnection
					JOIN DaylightGainGroup USING(DaylightSensorID)
					JOIN DaylightGainGroupAssociation USING(DaylightGainGroupID)
					JOIN SwitchLegController ON (DaylightGainGroupAssociation.SwitchLegControllerID = SwitchLegController.SwitchLegControllerID)
					JOIN Device ON (Device.DeviceID = SwitchLegController.DeviceID)
					JOIN DeviceClassInfo ON (Device.DeviceClassInfoID=DeviceClassInfo.DeviceClassInfoID)
					WHERE DaylightSensorConnection.DeviceID = ?
					''', (device_id,)
					)
				programmed_devices_rows = c.fetchall()
				print("<div id='0x%08X' class= 'control_device'>"%(device_serial_number)) #HTML open Div with ID of Device
				print("    %s: %s (SN: %08X) (This Daylight Sensor controls %d devices)"%
					(device_designer_tag, device_name, device_serial_number, len(programmed_devices_rows)))
				print("</div><div id ='0x%08X_assigned_devices' class='assigned_devices'><ul>"%(device_serial_number)) #HTML Close Div, Open Assigned Devices Div, Open Unordered List
	
				for programmed_device_row in programmed_devices_rows :
					# Store the column values in a named variable for easy reference
					programmed_device_name = programmed_device_row[0]
					programmed_device_serial_number = programmed_device_row[1]
					programmed_device_designer_tag = programmed_device_row[2]
					programmed_device_short_descr = programmed_device_row[3]

					# Print the assigned device name and serial
					print("<li>") #HTML List Item
					print("        %s: %s (SN: %08X)"%(programmed_device_designer_tag, programmed_device_name, programmed_device_serial_number))
					print("</li>") #HTML List Item
				print("</ul></div>") #HTML Close Unordered List, Close Div
			else :
				print("<div id='0x%08X' class='load_controller'>"%(device_serial_number)) #HTML open Div with ID of Device
				print("    %s: %s (SN: %08X) (v%s)"%(device_designer_tag, device_name, device_serial_number, device_fw_rev.lstrip("0")))
				print("</div>") #HTML Close Div
			
		print("</ul></div></div>") #HTML close unordered list, close devices Div, close Areas Div
	# Cleanup the connection after we are done
	conn.close()

if __name__ == "__main__":
	main()
