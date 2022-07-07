# MongoDB-Live-Stack-Tracing-Tool
This Repository contains a tool used to acquire live Stack Traces of a running **MongoDB Server.**
This utility can be useful in **debugging** issues in **real-time** when the server is experiencing high CPU usage due to client queries. 

## Features

The python script is built to run on linux based systems with a running mongodb server, utilising the **eu-stack** utility of **elfutils** package. and some system commands like **top** 
It further refines the results and can provide:
  1) Individual Stack Trace Reports in **JSON** format
  2) Information regarding individual **thread states, CPU usage, client names etc.**

## Usage

To run the script, provide 2 required parameters as shown below

**Syntax**: 
> python stackTraceTool.py [-n 3 -I 0.5] [-c | -N | -t | -C | -s | -d | -h ]

Options:

 - **n** or **--num-iterations**  : Provide number of iterations for stack (REQUIRED).
 - **I** or **--interval**    :  Provide the INTERVAL between iterations (in seconds) (REQUIRED).
 - **c** or **--cpu-threshold** :     Provide the CPU Usage Threshold for threads (0-100) (OPTIONAL) - Default = 15
 - **N** or **--num-threads** :    Provide the Number of Threads to be taken (>0) (OPTIONAL) - Default = 40
 - **t** or **--threshold-iterations** :     Provide the number of iterations for which the thread has to be in High CPU Usage state to be considered for analysis (OPTIONAL) - Default = total number of iterations
 - **C** or **--current-ops** :    Use this option to capture current ops too (OPTIONAL) - Default = no current operations data provided"
 - **s** or **--save** :    Use this option to make the script save the results in a combined form for each iteration. Can be used in a stack analyzer utility (OPTIONAL) - Default = no seperate files are created
 - **D** or **--debug** :    Use this option to print timestamps and debug information for this script (OPTIONAL) - Default = no debug info"
 - **h** or **--help**  :   Show the help menu

The output is returned in JSON format and is also stored in **collectedData.json**

>Potential Issues: 
While running the script without sudo permission, it might ask for sudo password while running the script. After entering it, the results of that iteration may not be meaningful, so it may be required to restart the script.

