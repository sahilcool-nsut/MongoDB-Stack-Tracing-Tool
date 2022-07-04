import getopt
import multiprocessing
import subprocess
import json
import sys
import time

CPU_THRESHOLD=-1
PRINT_DEBUG=0
SHORT=0
EXTRA_MONGO_INFO=0
OUTPUT_FILE_NAME="currentOpByThread.json"

# Thread Class used to store thread objects
class Thread:
    def __init__(self,tid,tstate,tcpu,tname):
        self.threadId=tid
        self.threadName=tname
        self.threadCpu=tcpu
        self.threadState=tstate
        self.currentOp={}


# EJSON = Extended JSON to convert UUID, TimeStamps into json readable objects.
# --quiet is to remove the connection information we get on a new connection
def runCurrentOpsCommand(currentOps):
    p = subprocess.Popen("mongo localhost:27017 --eval 'JSON.stringify(db.currentOp())' --quiet", stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    # p = subprocess.Popen("mongosh localhost:27017 --eval 'EJSON.stringify(db.currentOp())' --quiet", stdout=subprocess.PIPE, shell=True)
    stdout, stderr = p.communicate()
    try:
        if stderr.decode('UTF-8') !='':
            print("CurrentOps command couldn't be run. Error: " + stderr.decode('UTF-8'))
            currentOps["value"]={}
        else:
            currentOps["value"]=json.loads(stdout.decode('UTF-8'))
    except:
        currentOps["value"]={}
    # Key value has to be used as due to some reason, the currentOps object wasn't being updated
    

def runTopHCommand(threads):
    # Call top command in batch mode(-b) and limit it for 1 iteration (n1). 
    # Grep for clients with name starting as "conn.." as these are CLIENT threads for mongodb
    p = subprocess.Popen("top -H -bn1 -w512 | grep 'conn'", stdout=subprocess.PIPE, stderr=subprocess.PIPE,shell=True)
    stdout, stderr = p.communicate()
    if stderr.decode('UTF-8') !='':
        print("Top command couldn't be run. Error: " + stderr.decode('UTF-8'))
    else:
        for client in stdout.splitlines():
            # have to decode as stdout would be in byte form
            clientData = client.decode('UTF-8').split()
            # Sample TOP output: 
            #   5977 mongodb   20   0 3556268   1.8g  56340 S   0.0  23.3   1:25.52 conn11
            currThread = Thread(clientData[0],clientData[7],float(clientData[8]),clientData[11])
            # Discard those threads which dont qualify CPU Threshold
            if currThread.threadCpu < CPU_THRESHOLD:
                continue
            threads[currThread.threadId]=currThread
    
def runMongoStatCommand(mongostat):
    p = subprocess.Popen("mongostat -n1 --noheaders --json", stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    stdout, stderr = p.communicate()
    try:
        if stderr.decode('UTF-8') !='':
            print("Mongostat command couldn't be run. Error: " + stderr.decode('UTF-8'))
        else:
            mongostat["value"]=json.loads(stdout.decode('UTF-8'))
    except:
        mongostat["value"]={}
# Driver Function to gather thread information from top and eu-stack commands
def gatherThreadInformation(threads,currentOps,mongostat):

    totalProcesses=[]
    process=multiprocessing.Process(target=runTopHCommand,args=(threads,))
    process.start()
    totalProcesses.append(process)

    process=multiprocessing.Process(target=runCurrentOpsCommand,args=(currentOps,))
    process.start()
    totalProcesses.append(process)

    if EXTRA_MONGO_INFO==1:
        process=multiprocessing.Process(target=runMongoStatCommand,args=(mongostat,))
        process.start()
        totalProcesses.append(process)

    if PRINT_DEBUG==1:
        print("All processes were created, now waiting : " +str(int(round(time.time() * 1000)))[-6:])
    for p in totalProcesses:
        p.join()
    currentOps=currentOps["value"]

    for threadId,thread in threads.items():
        currThread = thread
        currName = thread.threadName
        try:
            if len(currentOps)!=0:
                for item in currentOps["inprog"]:
                    if item["desc"] == currName:
                        if SHORT==1:
                            shortItem={}
                            shortItem["client"]=item["client"]
                            shortItem["secs_running"]=item["secs_running"]
                            shortItem["microsecs_running"]=item["microsecs_running"]
                            shortItem["ns"]=item["ns"]
                            shortItem["command"]=item["command"]
                            shortItem["waitingForLock"]=item["waitingForLock"]
                            currThread.currentOp = shortItem
                        else:
                            currThread.currentOp = item
                        threads[threadId] = currThread
                        break
        except: 
            print("Something went wrong while parsing current operations")
    if PRINT_DEBUG==1:
        print("Completed script at : " +str(int(round(time.time() * 1000)))[-6:])
    
def createJSON(threads,mongostat):
    entireJSONObject={}
    threads = dict(sorted(threads.items(), key=lambda item: item[1].threadCpu,reverse=True))
    for threadId,thread in threads.items():
        threadObj={}
        threadObj["threadId"] = thread.threadId
        threadObj["threadName"] = thread.threadName
        threadObj["threadCpu"] = thread.threadCpu
        threadObj["threadState"] = thread.threadState
        threadObj["currentOp"] = thread.currentOp
        entireJSONObject[threadId]=threadObj
    if EXTRA_MONGO_INFO==1:
        mongostat=mongostat["value"]
        try:
            entireJSONObject["mongostat"]={}
            qrw=mongostat["localhost"]["qrw"]
            qr = qrw.split('|')[0]
            qw = qrw.split('|')[1]
            arw=mongostat["localhost"]["arw"]
            ar = arw.split('|')[0]
            aw = arw.split('|')[1]
            dirty=mongostat["localhost"]["dirty"]
            flushes=mongostat["localhost"]["flushes"]
            entireJSONObject["mongostat"]["tips"]="Dirty % should be less than 5% in majority cases. Incase it is higher than 20%, server may start stalling and flushes would be seen to increase"
            entireJSONObject["mongostat"]["queueForReading"]=qr
            entireJSONObject["mongostat"]["queueForWriting"]=qw
            entireJSONObject["mongostat"]["activeReading"]=ar
            entireJSONObject["mongostat"]["activeWriting"]=aw
            entireJSONObject["mongostat"]["dirty%"]=dirty
            entireJSONObject["mongostat"]["flushes"]=flushes
        except:
            pass
    return entireJSONObject
    
# Function to show help menu
def showHelp():
    # Display Help
    print("")
    print("Syntax: python extractCurrentOp.py")
    print("options:")
    print("c or --cpu-threshold       Provide the CPU Usage Threshold for threads (0-100) (OPTIONAL) - Default = 15")
    print("d or --debug               Set as 1 to print debug statements with timestamps of script operationos (Default = 0 (no debug info))")
    print("s or --short               Ask for a shorter currentOps per client")
    print("e or --extra               Toggle this option to get extra mongo information from mongostat and mongotop (Default = 0)")
    print("h or --help                Show the help menu")
    print("")
    exit

# Function to parse the command line options
def parseOptions(argv):
    global CPU_THRESHOLD
    global PRINT_DEBUG
    global SHORT
    global EXTRA_MONGO_INFO
    try:
    #   h requires no input, so no colon for it
        opts, args = getopt.getopt(argv,"c:dseh",["cpu-threshold=","debug","help","short","extra"])
    except getopt.GetoptError:
        showHelp()
        sys.exit(2)
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            showHelp()
            sys.exit()
        elif opt in ("-c", "--cpu-threshold"):
            try:
                CPU_THRESHOLD = float(arg)
                if CPU_THRESHOLD > 100 or CPU_THRESHOLD < 0:
                    sys.exit(2)
            except:
                print("CPU Threshold should be an integer/float between 0 and 100. Value provided was: " + str(arg) + "\nExiting")
                sys.exit(2)
        elif opt in ("-d", "--debug"):
            try:
                PRINT_DEBUG = 1
            except:
                print("Value of debug parameter should be 0 or 1. Value provided was: " + str(arg) + "\nExiting")
                sys.exit(2)
        elif opt in ("-s", "--short"):
            SHORT=1
        elif opt in ("-e", "--extra"):
            EXTRA_MONGO_INFO=1

    if CPU_THRESHOLD==-1:
        CPU_THRESHOLD=15.0

    if PRINT_DEBUG==1:
        print("Parameters used: ")
        print("CPU Threshold: " + str(CPU_THRESHOLD))
        print("Short: " + str(SHORT))
        print("Debug: " + str(PRINT_DEBUG))
        print("Extra Info: " + str(EXTRA_MONGO_INFO))
        print("")

if __name__=="__main__":
    parseOptions(sys.argv[1:])
    manager = multiprocessing.Manager()
    threads = manager.dict()
    currentOps = manager.dict()
    mongostat=manager.dict()
    gatherThreadInformation(threads,currentOps,mongostat)
    entireJSONObject=createJSON(threads,mongostat)
    # try:
    #     jsonFile = open(OUTPUT_FILE_NAME, "w")
    #     json.dump(entireJSONObject, jsonFile, indent=4)
    #     jsonFile.close()
    # except:
    #     print("Couldn't open file for creating JSON")
    print(json.dumps(entireJSONObject,indent=4))