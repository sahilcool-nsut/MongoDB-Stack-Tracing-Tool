import os
from flask import Flask, flash, redirect, render_template, request
import createStackReport
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'data/'
ALLOWED_EXTENSIONS = {'txt'}



@app.route('/')
def home():
   return render_template('home.html',messages={})


def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


    
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
        f = request.files['stackFile']
        f.save(os.path.join(path, "data/stackFile.txt"))
        f = request.files['topFile']
        f.save(os.path.join(path, "data/topFile.txt"))

        createStackReport.main()

        return render_template("StackTraceReport.html")

if __name__ == '__main__':
   app.run()