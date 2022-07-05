# III. CPU-Intensive Current Ops Extraction
./extractCurrentOp

## Features
This is a utility script which returns a JSON response which contains details of the current High CPU-Intensive mongo clients, and what command the clients have hit. 

This is achieved through the use of the top -H command and the db.currentOp() command feature provided by mongo.

> top -H -bn1 -w512 | grep "conn" 
>
> mongo localhost:27017 --eval 'EJSON.stringify(db.currentOp())' --quiet


## Usage

The Script has a simple usage as follows:
> python extractCurrentOp.py [-c [0-100] -s -e -d -h]

Options
 - **c** or **--cpu-threshold** :     Provide the CPU Usage Threshold for threads (0-100) (OPTIONAL) - Default = 15
 - **s** or **--short** :    Toggle to get a shorter version of Current Operation for each thread (OPTIONAL)
 - **e** or **--extra** :    Toggle to get some extra information from mongostat (OPTIONAL)
 - **d** or **--debug** :    Use this option to print timestamps and debug information for this script (OPTIONAL) - Default = no debug info"
 - **h** or **--help**  :    Show the help menu

The output is returned in JSON format and is also stored in **currentOpByThread.json**
