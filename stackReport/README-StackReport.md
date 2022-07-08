# Eu-Stack Report Web Utility
./stackReport

This is a tool to provide individual stack reports, particularly aimed for analyzing stack traces of Running MongoDB servers.

It sets up a flask server which prompts to upload the necessary files, which are
 - **Single iteration of eu-stack**  (Required) 
 > Sample Command
 >
 > sudo eu-stack -p PID > stack.txt
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