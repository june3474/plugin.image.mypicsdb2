# plugin.image.mypicsdb2
MyPicsDB2 for Kodi with Python 3

## 1) How to include picture paths
Don't change the plugin configuration unless you know what you do!

a) You must add picture sources to XBMC

b) Within MyPicsDB (not in the configuration) select menu "Paths of pictures folders" to add these paths to the database.

### Excluding paths

a) Add the exclude path(s) via menu "Paths of pictures folders".

b) Rescan the paths which contain these added exclude paths to remove the pictures from MyPicsDB

### Excluding files

a) This can be done in the plugin settings under "Files"

b) You only need to enter a unique part of the complete path name. All files which contain this entered part of the path name will be excluded.

c) Rescan all paths.

d) To concatenate different file/path name parts use the | sign.

### Cleanup

a) After renaming a directory you must do a full rescan!

## 2) MySql

ATTENTION: Currently not supported!

a) You must create a database:
CREATE DATABASE MyPicsDB CHARACTER SET utf8 COLLATE utf8_bin;

b) Create a user (if not already done for music and movies):
CREATE USER 'xbmc'@'%' IDENTIFIED BY 'xbmc';

c) give him rights
GRANT ALL ON *.* TO 'xbmc'@'%';

d) Go to plugin settings and enable MySql. Set the correct user and password (they are case sensitive)!


## 3) Tag translation and combination of tags
Menu "translate your tags" lets you suppress tags (leave translation empty) or combine tags like 'Country/primary location name', 'Photoshop:Country' and 'Iptc4xmpExt:CountryName' to one 'Country' tag. 


## 4) General problems with MyPicsDB
If you have unexplainable problems like pictures don't get included into database and you're a long time user of MyPicsDB then it will be a good decision to delete the database and start with a new one.

To do this select "Pictures->Add-ons", press "C" and select "Add-on settings". 
Activate "Initialze the database at next startup" on tab "General" and press "OK".

Then start MyPicsDB. 
All tables (except table rootpaths which includes your entered picture paths) are dropped and recreated. 

This means that the already entered paths are still available and that you can start a rescan with "Paths of picture folders"->"Scan all paths". 


