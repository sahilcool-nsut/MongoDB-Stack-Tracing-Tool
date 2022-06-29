# MongoDB-Live-Stack-Tracing-Tool
This Repository contains a tool used to acquire live Stack Traces of a running **MongoDB Server.**
This utility can be useful in **debugging** issues in **real-time** when the server is experiencing high CPU usage due to client queries. 

## Features

The python script is built to run on linux based systems, utilising the **eu-stack** utility of **elfutils** package. and some system commands like **top** 
It further refines the results and can provide:
  1) Individual Stack Trace Reports in **JSON** format
  2) Information regarding individual **thread states, CPU usage, client names etc.**

## Usage

To run the script, provide 2 required parameters as shown below

**Syntax**: 
> python stackTraceTool.py [-n 3 -I 0.5] [-c | -N | -h ]

Options:

 - **n** or **--num-iterations**  : Provide number of iterations for stack (REQUIRED).
 - **I** or **--interval**    :  Provide the INTERVAL between iterations (in seconds) (REQUIRED).
 - **c** or **--cpu-threshold** :     Provide the CPU Usage Threshold for threads (0-100) (OPTIONAL) - Default = 20
 - **N** or **--num-threads** :    Provide the Number of Threads to be taken (>0) (OPTIONAL) - Default = 20
 - **h** or **--help**  :   Show the help menu

The output is stored in **OutputFiles/collectedData.json**

>Potential Issues: 
While running the script without sudo permission, it might ask for sudo password while running the script. After entering it, the results of that iteration may not be meaningful, so it may be required to restart the script.

