import datetime
import os
from os.path import isfile, join
import time
from flask import Flask, after_this_request, render_template, request
import createStackReport
from hashlib import sha512
import base64
app = Flask(__name__)
# To ensure that templates get reloaded (the dynamic html file being craeted wasnt getting updated on back buttons, so this was the fix)
app.config["TEMPLATES_AUTO_RELOAD"]=True
# Home route, messages is empty right now, later would contain error message
@app.route('/')
def home():
    return render_template('home.html',messages={})


# On pressing submit button, user is redirected here.
# Availability of both the submitted files is checked first
# If there are missing files, user is redirected to home page with an error
# If no error, the python script is called which generates a HTML template to which the user is then redirected
@app.route('/uploader', methods = ['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        print(request.files)
        if 'stackFile' not in request.files:
            error="No Stack File Given"
            return render_template('home.html',messages={'error':error})
        # Empty file is provided by browser in case no file is selected
        elif request.files['stackFile'].filename == '':
            error='No selected stack file'
            return render_template('home.html',messages={'error':error})
        if 'topFile' not in request.files:
            error="No Top File Given"
            return render_template('home.html',messages={'error':error})
        elif request.files['topFile'].filename == '':
            error="No selected top file given"
            return render_template('home.html',messages={'error':error})
        
        path = os.getcwd()

        # Timestamp is used to create unique data/graph/html files for each user coming to server.
        # It is passed to main python script, where it sets the file names using the dynamic timestamp
        TIMESTAMP=str(datetime.datetime.now())
        f = request.files['stackFile']
        f.save(os.path.join(path, "data/stackFile_"+TIMESTAMP+".txt"))
        f = request.files['topFile']
        f.save(os.path.join(path, "data/topFile_"+TIMESTAMP+".txt"))
        
        
        createStackReport.main(TIMESTAMP)

        # Delete template file and date files uploaded, once returned to user. 
        # Graph images are not deleted as they were dissapearing on user's webpage too.
        # Have to decide how to delete graph images as they are accumulating
        @app.after_request
        def remove_file(response):
            try:
                os.remove(os.path.join(path,"templates","StackTraceReport_"+TIMESTAMP+".html"))
                os.remove(os.path.join(path,"data/stackFile_"+TIMESTAMP+".txt"))
                os.remove(os.path.join(path, "data/topFile_"+TIMESTAMP+".txt"))
                # os.remove(os.path.join(path,"static/graphs/flameGraph_"+TIMESTAMP+".pdf"))
                # os.remove(os.path.join(path,"static/graphs/statePie_"+TIMESTAMP+".png"))
                # os.remove(os.path.join(path,"static/graphs/identicalStackTraceGraph_"+TIMESTAMP+".png"))
            except Exception as error:
                pass
            return response
            
        return render_template("StackTraceReport_"+TIMESTAMP+".html")

@app.route('/delete1day')
def delete():
    graphDirectory=os.path.join(os.getcwd(),"static/graphs")
    onlyfiles = [f for f in os.listdir(graphDirectory) if isfile(join(graphDirectory, f))]
    print(onlyfiles)
    for file in onlyfiles:
        # Example file name: flameGraph_2022-07 01 ......
        fileWithoutExtension=(file[::-1].split('.',1)[1])[::-1]
        fileDateTime=fileWithoutExtension.split('_')[1]
        deltatime=datetime.datetime.now()-datetime.datetime.strptime(fileDateTime,"%Y-%m-%d %H:%M:%S.%f")
        if deltatime.days>=1:
            os.remove(join(graphDirectory, file))
        
    return "Deleted Successfully"
if __name__ == '__main__':
   app.run()

