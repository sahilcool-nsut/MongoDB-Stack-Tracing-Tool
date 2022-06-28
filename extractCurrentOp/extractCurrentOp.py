import multiprocessing
import subprocess
import json
import time

CPU_THRESHOLD=20.0
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
    p = subprocess.Popen("mongosh localhost:27017 --eval 'EJSON.stringify(db.currentOp())' --quiet", stdout=subprocess.PIPE, shell=True)
    stdout, stderr = p.communicate()
    # Key value has to be used as due to some reason, the currentOps object wasn't being updated
    currentOps["value"]=dict(json.loads(stdout.decode('UTF-8')))

def runTopHCommand(threads):
    # Call top command in batch mode(-b) and limit it for 1 iteration (n1). 
    # Grep for clients with name starting as "conn.." as these are CLIENT threads for mongodb
    p = subprocess.Popen("top -H -bn1 | grep 'conn'", stdout=subprocess.PIPE, shell=True)
    stdout, stderr = p.communicate()
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
# Driver Function to gather thread information from top and eu-stack commands
def gatherThreadInformation(threads,currentOps):

    totalProcesses=[]
    process=multiprocessing.Process(target=runTopHCommand,args=(threads,))
    process.start()
    totalProcesses.append(process)

    process=multiprocessing.Process(target=runCurrentOpsCommand,args=(currentOps,))
    process.start()
    totalProcesses.append(process)

    print("All processes were created, now waiting : " +str(int(round(time.time() * 1000))))
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
                        currThread.currentOp = item
                        threads[threadId] = currThread
                        break
        except: 
            print("Something went wrong while parsing current operations")
    
def createJSON(threads):
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
    try:
        jsonFile = open(OUTPUT_FILE_NAME, "w")
        json.dump(entireJSONObject, jsonFile)
        jsonFile.close()
    except:
        print("Couldn't open file for creating JSON")
    
if __name__=="__main__":
    manager = multiprocessing.Manager()
    threads = manager.dict()
    currentOps = manager.dict()
    gatherThreadInformation(threads,currentOps)

    createJSON(threads)