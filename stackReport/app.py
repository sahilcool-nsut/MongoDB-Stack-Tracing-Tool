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
        TOP_GIVEN = False

        # Timestamp is used to create unique data/graph/html files for each user coming to server.
        # It is passed to main python script, where it sets the file names using the dynamic timestamp
        TIMESTAMP=str(datetime.datetime.now())
        path = os.getcwd()

        if 'stackFile' not in request.files:
            error="No Stack File Given"
            return render_template('home.html',messages={'error':error})
        # Empty file is provided by browser in case no file is selected
        elif request.files['stackFile'].filename == '':
            error='No selected stack file'
            return render_template('home.html',messages={'error':error})
        else:
            f = request.files['stackFile']
            f.save(os.path.join(path, "data/stackFile_"+TIMESTAMP+".txt"))

        if 'topFile' not in request.files:
            TOP_GIVEN = False
        elif request.files['topFile'].filename == '':
            TOP_GIVEN = False
        else:
            TOP_GIVEN = True
            f = request.files['topFile']
            f.save(os.path.join(path, "data/topFile_"+TIMESTAMP+".txt"))
        

        
        createStackReport.main(TIMESTAMP,TOP_GIVEN)

        # Delete template file and date files uploaded, once returned to user. 
        # Graph images are not deleted as they were dissapearing on user's webpage too.
        # Have to decide how to delete graph images as they are accumulating
        @app.after_request
        def remove_file(response):
            try:
                @response.call_on_close
                def process_after_request():
                    time.sleep(3)
                    try:
                        os.remove(os.path.join(path,"templates","StackTraceReport_"+TIMESTAMP+".html"))
                    except:
                        pass
                    try:
                        os.remove(os.path.join(path,"data/stackFile_"+TIMESTAMP+".txt"))
                    except:
                        pass
                    try:
                        os.remove(os.path.join(path, "data/topFile_"+TIMESTAMP+".txt"))
                    except:
                        pass
                    try:
                        os.remove(os.path.join(path,"static/graphs/flameGraph_"+TIMESTAMP+".pdf"))
                    except:
                        pass
                    try:
                        os.remove(os.path.join(path,"static/graphs/statePie_"+TIMESTAMP+".png"))
                    except:
                        pass
                    try:
                        os.remove(os.path.join(path,"static/graphs/identicalStackTraceGraph_"+TIMESTAMP+".png"))
                    except:
                        pass
            except Exception as error:
                pass
            return response
            
        return render_template("StackTraceReport_"+TIMESTAMP+".html")
        
    return "Invalid Request"
if __name__ == '__main__':
   app.run()
