# MongoDB-Stack-Tracing-Tool
This Repository contains a tool used to acquire live Stack Traces of a running MongoDB Server.
This utility can be useful in debugging issues in real-time when the server is experiencing high CPU usage due to client queries. 

The shell script is built to run on linux based systems, utilising the eu-stack utility of elfutils package. 
It further refines the results and can provide:
  1) Individual Stack Trace Reports in JSON format
  2) Information regarding individual thread states, CPU usage, client names etc.

Currently, it also uses a python script to generate the following graphs
1) Flame Graph (trie) for the callstack
2) Pie graph for states of threads

To install its dependencies, a requirements.txt file is provided

To run the script, provide 2 required parameters as shown below\n

Syntax: ./stackTraceTool.sh [-n 3 -I 0.5] [-c|N|h|t]
options:
1) n       Provide number of iterations for stack (REQUIRED).
2) I       Provide the INTERVAL between iterations (in seconds) (REQUIRED).
3) c       Provide the CPU Usage Threshold for threads (0-100) (OPTIONAL) - Default = 0
4) N       Provide the Number of Threads to be taken (>0) (OPTIONAL) - Default = 20
5) t       Provide the Threshold for minimum number of stacks of a thread to be considered (0<num<=iterations) (OPTIONAL) - Default = 0 (consider all threads)
6) h       Show the help menu

Potential Issues: 
While running the script without sudo permission, it might ask for sudo password while running the script. After entering it, the results of that iteration won't be meaningful, so it may be required to restart the script. \n
The program also creates temporary files
