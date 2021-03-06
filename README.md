# I. MongoDB-Live-Stack-Tracing-Tool
./liveStackTracing

This Folder contains a tool used to acquire live Stack Traces of a running **MongoDB Server.**
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



# II. Eu-Stack Report Web Utility
./stackReport

This is a tool to provide individual stack reports, particularly aimed for analyzing stack traces of Running MongoDB servers.

It sets up a flask server which prompts to upload the necessary files, which are
 - **Single iteration of eu-stack**  (Required)
 > Sample Command
 >
 > sudo eu-stack -p PID > stack.txt
 >
 > Can also use the output of the live stack tracing script in this repository (run it in -s mode)
 >
 - **Single iteration of top command**  (Optional)
 > Sample Command
 >
 > top -H -bn1 -w512 | grep "conn" > topH.txt
 > 
 > -b for batch mode, -n1 for limiting to 1 iteration. As it is aimed for MongoDB client queries, "conn" named threads are considered (these are MongoDB Clients)

It uses the combination of a **single iteration of eu-stack** and **top** command to provide insights and analysis using different graphs, by rendering a HTML page. This is done using a **python** script.

!["Individual Stack Report Screenshot"](https://github.com/sahilcool-nsut/MongoDB-Stack-Tracing-Tool/blob/main/Screenshots/StackReportScreenshot.png "Individual Stack Report")

### Features
Provides an HTML page with simple UI showing the following information in form of **graphs/tables**. Also provides snippets of information regarding these graphs.

 - Thread State Distribution (only if top file provided)
 - Call Stack (Flame Graph)
 - Identical Stack Trace Distribution
 - Top CPU Consuming Threads (only if top file provided)
 - Most Used Functions
 - Individual Thread Details

### Usage
To locally run the program, follow the steps given below
 - For initial dependency setup, a requirements.txt is provided
 > pip install -r requirements.txt
 - Run the Flask App by running the command
 > python app.py
 >
 > or
 >
 > flask run
 - Now, the server should be up on localhost:5000
 - !["Upload Files Landing Page"](https://github.com/sahilcool-nsut/MongoDB-Stack-Tracing-Tool/blob/main/Screenshots/UploadPage.png "Upload Files Landing Page")
 - Go to localhost:5000 and upload the required files. (basic error handling is present to avoid empty files)
 - Press Submit and you will get the results

The Repository also contains a shell script **collectData.sh** which can be used to generate both the text files when run on the server. The resulting files are stored in folder **dataByCommand**

Current Directory Structure:
 - stackReport
    - static 
      - scripts&emsp;&emsp;&emsp;&emsp;&emsp;-> local JS files
      - styles&emsp;&emsp;&emsp;&emsp;&emsp; -> local CSS files
    - templates &emsp;&emsp;&emsp;&emsp;&emsp;-> Home HTML file, and also where the generated HTML file is stored
    - app.py
    - createStackReport.py
    - README-StackReport.md
    - requirements.txt
> Any dynamic file generated during the script is deleted once response is sent to user.
    
    
Repository which is hosted live: https://github.com/sahilcool-nsut/EuStack-Analyzer
Live host website: https://eustack-analyzer.herokuapp.com/

> For hosting, the only special requirement was to add the graphviz buildpack in heroku for it to work properly
> Further, change in form action (in home.html) to the live URL was also required

    
# III. CPU-Intensive Current Ops Extraction
./extractCurrentOp

## Features
This is a utility script which returns a JSON response which contains details of the current High CPU-Intensive mongo clients, and what command the clients have hit. 

This is achieved through the use of the top -H command and the db.currentOp() command feature provided by mongo.

> top -H -bn1 -w512 | grep "conn" 
>
> mongo localhost:27017 --eval 'JSON.stringify(db.currentOp())' --quiet


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

>Potential Issues: 
The script requires the correct IP (localhost is fit in the script) and the correct port with it, else the command might not work.
