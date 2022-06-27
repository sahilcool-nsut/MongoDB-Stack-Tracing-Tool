# MongoDB-Stack-Tracing-Tool
## I.  Collective stack tracing
This Repository contains a tool used to acquire live Stack Traces of a running **MongoDB Server.**
This utility can be useful in **debugging** issues in **real-time** when the server is experiencing high CPU usage due to client queries. 


### Features

The shell script is built to run on linux based systems, utilising the **eu-stack** utility of **elfutils** package. and some system commands like **top** 
It further refines the results and can provide:
  1) Individual Stack Trace Reports in **JSON** format
  2) Information regarding individual **thread states, CPU usage, client names etc.**

### Usage

To run the script, provide 2 required parameters as shown below

**Syntax**: 
> ./stackTraceTool.sh [-n 3 -I 0.5] [-c | N | h | t ]

Options:

 - **n**  : Provide number of iterations for stack (REQUIRED).
 - **I**     :  Provide the INTERVAL between iterations (in seconds) (REQUIRED).
 - **c**  :     Provide the CPU Usage Threshold for threads (0-100) (OPTIONAL) - Default = 10
 - **N**  :    Provide the Number of Threads to be taken (>0) (OPTIONAL) - Default = 20
 - **t**   :  Provide the Threshold for minimum number of stacks of a thread to be considered 0<num<=iterations) (OPTIONAL) - Default = 0 (consider all threads)
 - **h**   :   Show the help menu

>Potential Issues: 
While running the script without sudo permission, it might ask for sudo password while running the script. After entering it, the results of that iteration won't be meaningful, so it may be required to restart the script.

> The program also creates temporary files which are deleted in the process

## II. Individual Stack Report
A tool to provide individual stack reports is also provided in the folder **/stackReport**
It uses the combination of a **single iteration of eu-stack** and **top** command to provide insights and analysis using different graphs, by rendering a HTML page. This is done using a **python** script.

### Features
Provides a HTML page with simple UI showing the following information in form of **graphs/tables**

 - Thread State Distribution
 - Call Stack (Flame Graph)
 - Identical Stack Trace Distribution
 - Top CPU Consuming Threads
 - Most Used Functions
 - Individual Thread Details

### Usage
If running for a live stack trace, the program can be run using the shell file **takeStack.sh** on a system with a running mongod server. 
If a live stack trace is not a requirement, we can manually provide the files of the stack trace and top command in the workspace as: 
> /data/entireStackTrace.txt
> /data/threadDetailsTopH.txt

After this, simply run the python script **createReport.py** to get the results