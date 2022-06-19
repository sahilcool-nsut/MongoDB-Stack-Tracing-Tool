# MongoDB-Stack-Tracing-Tool
This Repository contains a tool used to acquire live Stack Traces of a running MongoDB Server.
This utility can be useful in debugging issues in real-time when the server is experiencing high CPU usage due to client queries. 

The shell script is built to run on linux based systems, utilising the eu-stack utility of elfutils package. 
It further refines the results and can provide:
  1) Individual Stack Trace Reports in JSON format
  2) Information regarding individual thread states, CPU usage, client names etc.


Syntax: ./newerMain.sh [-n 3 -I 0.5] [-c|N|h|t]
options:
n       Provide number of iterations for stack (REQUIRED).
I       Provide the INTERVAL between iterations (in seconds) (REQUIRED).
c       Provide the CPU Usage Threshold for threads (0-100) (OPTIONAL) - Default = 0
N       Provide the Number of Threads to be taken (>0) (OPTIONAL) - Default = 20
t       Provide the Threshold for minimum number of stacks of a thread to be considered (0<num<=iterations) (OPTIONAL) - Default = 0 (consider all threads)
h       Show the help menu

