from asyncio import gather
import json
import multiprocessing
import subprocess
import time

NUMCALLS=3
INTERVAL=0.5
TOP_N_THREADS=40

class Thread:
    def __init__(self,tid,tstate,tcpu,tname,tstack="",ttimestamp=""):
        self.threadId=tid
        self.threadName=tname
        self.threadCpu=tcpu
        self.threadState=tstate
        self.threadStack=tstack
        self.threadStackTimeStamp=ttimestamp

def runStackCommand(threadId,threads):
    p = subprocess.Popen("sudo eu-stack -1 -p " + str(threadId), stdout=subprocess.PIPE, shell=True)
    stdout, stderr = p.communicate()
    currThread = threads[threadId]
    currThread.threadStack = stdout.decode('UTF-8')
    currThread.threadStackTimeStamp=str(int(round(time.time() * 1000)))
    threads[threadId] = currThread

def runCurrentOpsCommand(currentOps,iteration):
    p = subprocess.Popen("mongosh localhost:27017 --eval 'EJSON.stringify(db.currentOp())' --quiet", stdout=subprocess.PIPE, shell=True)
    stdout, stderr = p.communicate()
    # print(stdout.decode('UTF-8'))
    currentOps[iteration]=json.loads(stdout.decode('UTF-8'))
    # print(currentOps)

def gatherThreadInformation(threads):
    p = subprocess.Popen("top -H -bn1 | grep -m " + str(TOP_N_THREADS) + " 'conn' | sort -n -k1", stdout=subprocess.PIPE, shell=True)
    stdout, stderr = p.communicate()
    
    print("Command for top completed at : " +str(int(round(time.time() * 1000))))
    for client in stdout.splitlines():
        clientData = client.decode('UTF-8').split()
        currThread = Thread(clientData[0],clientData[7],clientData[8],clientData[11])
        # if float(currThread.threadCpu) < CPU_THRESHOLD:
        #     continue
        threads[currThread.threadId]=currThread
    print("Data filling for top completed at : " +str(int(round(time.time() * 1000))))
    totalProcesses=[]
    print("Command for threads and currentOps started at : " +str(int(round(time.time() * 1000))))    
    for threadId,thread in threads.items():
        
        process=multiprocessing.Process(target=runStackCommand,args=(threadId,threads,))
        process.start()
        totalProcesses.append(process)
    print("All processes were created, now waiting : " +str(int(round(time.time() * 1000))))
    for p in totalProcesses:
        p.join()
    
    
def performAnalysis(currentOps):
    mergedFile = open("OutputFiles/mergedPython.json", "r")
    jsonObject = json.load(mergedFile)
    mergedFile.close()

    for threadId in jsonObject["threads"]:
        for i in range(0,len(jsonObject["threads"][threadId]["iterations"])):
            
            analysisObject={}
            currIteration=jsonObject["threads"][threadId]["iterations"][i]["iteration"]
            currStack=jsonObject["threads"][threadId]["iterations"][i]["threadStack"]
            currName=jsonObject["threads"][threadId]["iterations"][i]["threadName"]
            # Corner case for bad stacks colelcted
            
            if len(currStack.split('\n')) <=1:
                continue
            done=False
            if done == False and "recvmsg" in currStack:
                analysisObject["queryState"]="Idle"
                done=True
            if done == False and "__poll" in currStack:
                analysisObject["queryState"]="Polling"
                done=True
            if done == False and "CollectionScan" in currStack:
                analysisObject["includesCollectionScan"]="True"

            if done == False and "CountScan" in currStack:
                analysisObject["includesCountScan"]="True"

            if done == False and "CountStage" in currStack:
                analysisObject["includesCountingStage"]="True"

            if done == False and "SortStage" in currStack:
                analysisObject["includesSortingStag"]="True"

            if done == False and "UpdateStage" in currStack:
                analysisObject["includesUpdationStage"]="True"

            if done == False and "ProjectionStage" in currStack:
                analysisObject["includesProjectionStage"]="True"

            if done == False and "FindCmd" in currStack:
                analysisObject["queryType"]="Find"

            if done == False and "CmdCount" in currStack:
                analysisObject["queryType"]="Count"

            if done == False and "CmdFindAndModify" in currStack:
                analysisObject["queryType"]="FindAndModify"
            
            if done == False and "PipelineCommand" in currStack:
                analysisObject["queryType"]="Pipeline"

            if done == False and "runAggregate" in currStack:
                analysisObject["queryType"]="Aggregation"

            if done == False and "CmdInsert" in currStack:
                analysisObject["queryType"]="Insert"

            if done == False and "ExprMatchExpression" in currStack:
                analysisObject["includesExpressionMatching"]="True"
            
            if done == False and "PathMatchExpression" in currStack:
                analysisObject["currentlyMatchingDocuments"]="Matching Path for expression (still deciding path)"
            
            if done == False and "InMatchExpression" in currStack:
                analysisObject["currentlyMatchingDocuments"]="Matching 'in' expression"
            
            if done == False and "RegexMatchExpression" in currStack:
                analysisObject["currentlyMatchingDocuments"]="Matching 'Regex' expression"
            
            if done == False and "ComparisonMatchExpression" in currStack:
                analysisObject["currentlyComparingValues"]="True"
            
            if done == False and "getNextDocument" in currStack:
                analysisObject["fetchingNextDocument"]="True"
            
            if done == False and "compareElementStringValues" in currStack:
                analysisObject["currentlyComparingStringValues"]="True"
            jsonObject["threads"][threadId]["iterations"][i]["analysis"]=analysisObject
            
            currentOpObject = currentOps[currIteration]
            if len(currentOpObject)!=0:
                myCurrentOpObject={}
                for item in currentOpObject["inprog"]:
                    if item["desc"] == currName:
                        myCurrentOpObject["command"] = item
                        break
                jsonObject["threads"][threadId]["iterations"][i]["currentOp"]=myCurrentOpObject

    a_file = open("OutputFiles/mergedPython.json", "w")
    json.dump(jsonObject, a_file)
    a_file.close()

def createJsonFile(allIterationsThreads):
    entireJsonObject={}
    entireJsonObject["threads"]={}
    for i in range(0,NUMCALLS):
        currThreadDict=allIterationsThreads[i]
        # print("ITERATION: " + str(i) + "\n\n")
        for threadId,thread in currThreadDict.items():
            currThreadObject={}
            if threadId not in entireJsonObject["threads"]:
                currThreadObject={}
                currThreadObject["threadId"]=threadId
                currThreadObject["iterations"]=[]
            else:
                currThreadObject=entireJsonObject["threads"][threadId]
            
            iterationObject={}
            iterationObject["iteration"] = i
            iterationObject["threadId"]=threadId
            iterationObject["threadName"]=thread.threadName
            iterationObject["threadCpu"]=thread.threadCpu
            iterationObject["threadState"]=thread.threadState
            iterationObject["threadStackTimeStamp"]=thread.threadStackTimeStamp
            iterationObject["threadStack"]=thread.threadStack

            currThreadObject["iterations"].append(iterationObject)
            entireJsonObject["threads"][threadId]=currThreadObject

    jsonFile = open("OutputFiles/mergedPython.json", "w")
    json.dump(entireJsonObject, jsonFile)
    jsonFile.close()


if __name__ == "__main__":

    print("Starting script at " + str(int(round(time.time() * 1000))))

    manager = multiprocessing.Manager()

    allIterationsThreads=[]
    currentOps=manager.dict()
    currentOpProcesses=[]
    # Gather Information
    for i in range(0,NUMCALLS):
        time1=int(round(time.time() * 1000))

        print("Starting iteration " + str(i) + " at time: " + str(int(round(time.time() * 1000))))
        threads=manager.dict()
        currentOpProcess=multiprocessing.Process(target=runCurrentOpsCommand,args=(currentOps,i,))
        currentOpProcess.start()
        gatherThreadInformation(threads)
        allIterationsThreads.append(threads)
        
        currentOpProcesses.append(currentOpProcess)
        time2=int(round(time.time() * 1000))
        timediff = time2-time1
        error = INTERVAL - timediff/1000
        if error <=0:
            pass
        else:
            time.sleep(error)
        print("Completed iteration : " +str(int(round(time.time() * 1000)))+"\n\n")
        
    
    
    print("Now waiting for currentOps to complete: " + str(int(round(time.time() * 1000))))
    for process in currentOpProcesses:
        process.join()
    # print(currentOps)
    print("Starting to create JSON file at time: " + str(int(round(time.time() * 1000))))
    # Create JSON File
    createJsonFile(allIterationsThreads=allIterationsThreads)
    
    # Performed Analysis seperately so that time between thread stacks is precise
    print("Starting analysis at time:  " + str(int(round(time.time() * 1000))))
    performAnalysis(currentOps)

