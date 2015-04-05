-------------------------
Using hole_mapper code. 
-------------------------
There are two programs: plateplanner.py and platemapper.py

plateplanner.py is for designing plates and generates the .plate files. It is described here.

platemapper.py is used to generate fiber assignments for plates and is discussed elsewhere.

Execution is (in dir of plateplanner.py): "plateplanner.py", but running the program prior to the following steps is pointless.


-------------------------
Creating plates
-------------------------
go through all the received files and fix formatting errors or yell at submitter
Some common issues:
abbreviated required column names
RA2000 DE2000 instead of RA, Dec, & epoch columns 
extension not .field
# in front of header row
no field=name
<> around a number value

Create a directory with all of the .field files, and make an archive of your starting point.


Figure out what UT each field should be drilled for and add the line
obsdate = yyyy mm dd h m s
to each .field file

run plateplanner.py in the directory you want the output to appear: ./plateplanner.py


What goes onto the plate is determined as follows:
get everything drillable for each field, conflict procedure:
chek all for presence on the plate, done in inches
exclude anything that conflicts with a guide, acquisition, or the SH hole
perform a weighted minimum vertex cover cut on any remaining holes that can’t be plugged simultaneously WE MAY WANT TO CHANGE THIS IF THERE ISN”T A WAY AROUND IT VIA a second field
no number of low priority targets will overtake a higher priority target and cause it to be dropped
sky weights were respected here until the apr15 batch of plates, they shouldn’t have been
minsky is not considered, users are required to provide enough isolated skys for their own requirements
mustkeep is also not considered here.
sort out what is compatible on the plate with fieldmanager._determine_conflicts 
handle guides first, try to keep at least  MIN_GUIDES for each field
keep isolated first
drop colliding targets if necessary but not if it would violate mustkeep for a field
Repeat the same process with acquisitions, trying for MIN_ACQUISITIONS 
Finally process all the targets and skys
compute what conflicts with what, allowing  DRILLABLE_PCT_R_OVERLAP_OK
skys are subject to mustkeep, their priorities are respected for this purpose alone
for all the selected fields set the drill priority of mustkeep targets to max
break the targets of each field into groups within that field based on priorities
e.g. all targets with pri=4.3 in field 1 are a group
cycle through the fields taking a target from the group with highest priority still having targets and giving it the next most important priority for the plate, so that each successive draw is slightly less important. all draws will be lower priority that mustkeeps
set non-mustkeep sky priorities to the negative sum of the number of things it conflicts with
go through every colliding hole
discard it if it is a standard
discard it if it has a lower priority than the max of what it conflicts with
if dropping it would violate minsky, drop everything else instead



