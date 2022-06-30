import getopt
import json
import multiprocessing
import subprocess
import sys
import time

# Arguments
NUMCALLS=-1
INTERVAL=-1
TOP_N_THREADS=-1
CPU_THRESHOLD=-1

OUTPUT_FILE_NAME="collectedData"

# Thread Class used to store thread objects
class Thread:
    def __init__(self,tid,tstate,tcpu,tname,tstack="",ttimestamp=""):
        self.threadId=tid
        self.threadName=tname
        self.threadCpu=tcpu
        self.threadState=tstate
        self.threadStack=tstack
        self.threadStackTimeStamp=ttimestamp

# This function is multithreaded to collect stack information for a single thread
# -1 is an option to get stack of an individual thread given by its thread ID passed to -p
def runStackCommand(threadId,threads):
    p = subprocess.Popen("sudo eu-stack -1 -p " + str(threadId), stdout=subprocess.PIPE, shell=True)
    stdout, stderr = p.communicate()
    currThread = threads[threadId]
    currThread.threadStack = stdout.decode('UTF-8')
    currThread.threadStackTimeStamp=str(int(round(time.time() * 1000)))[-6:]
    threads[threadId] = currThread

# This function is multithreaded to collect current operations using mongosh command
# EJSON = Extended JSON to convert UUID, TimeStamps into json readable objects.
# --quiet is to remove the connection information we get on a new connection
def runCurrentOpsCommand(currentOps,iteration):
    p = subprocess.Popen("mongosh localhost:27017 --eval 'EJSON.stringify(db.currentOp())' --quiet", stdout=subprocess.PIPE, shell=True)
    stdout, stderr = p.communicate()
    currentOps[iteration]=json.loads(stdout.decode('UTF-8'))

# Driver Function to gather thread information from top and eu-stack commands
def gatherThreadInformation(threads):

    # Call top command in batch mode(-b) and limit it for 1 iteration (n1). 
    # Grep for clients with name starting as "conn.." as these are CLIENT threads for mongodb
    # Also, use parameter TOP_N_THREADS to limit results
    # Sorting is done by threadId (-k1 = first field, -n = numeric). This is done so that relative order of sorting remains same, and we can achieve precision in intervals
    # Although the impact of sorting may be very less, but it can be useful in case of very slow running commands 
    p = subprocess.Popen("top -H -bn1 -w512 | grep -m " + str(TOP_N_THREADS) + " 'conn' | sort -n -k1", stdout=subprocess.PIPE, shell=True)
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

    totalProcesses=[]
    print("Starting multiprocessing of eu-stack calls at time: " +str(int(round(time.time() * 1000)))[-6:])    
    for threadId,thread in threads.items():
        process=multiprocessing.Process(target=runStackCommand,args=(threadId,threads,))
        process.start()
        totalProcesses.append(process)
    print("All processes were created, now waiting : " +str(int(round(time.time() * 1000)))[-6:])
    for p in totalProcesses:
        p.join()
    

# Function to perform analysis on the stacks and save it in the JSON file
def performAnalysis(currentOps):
    try:
        mergedFile = open("OutputFiles/"+OUTPUT_FILE_NAME+".json", "r")
        jsonObject = json.load(mergedFile)
        mergedFile.close()
    except:
        print("Something went wrong while accessing the file in analysis performing phase.")

    # Iterate over each thread and each iteration of the thread
    for threadId in jsonObject["threads"]:
        for i in range(0,len(jsonObject["threads"][threadId]["iterations"])):
            
            try:
                analysisObject={}
                currIteration=jsonObject["threads"][threadId]["iterations"][i]["iteration"]
                currStack=jsonObject["threads"][threadId]["iterations"][i]["threadStack"]
                currName=jsonObject["threads"][threadId]["iterations"][i]["threadName"]
                
                # Corner case for bad stacks collected
                # Stack would be something like TID 12314: (and nothing ahead)
                if len(currStack.split('\n')) <=1:
                    continue
                
                done=False
                if done == False and "recvmsg" in currStack:
                    analysisObject["queryState"]="Idle"
                    done=True
                if done == False and "__poll" in currStack:
                    analysisObject["queryState"]="Polling"
                    done=True
                
                # Type of Scan present
                if done == False and "CollectionScan" in currStack:
                    analysisObject["includesCollectionScan"]="True"

                if done == False and "CountScan" in currStack:
                    analysisObject["includesCountScan"]="True"

                # Type of Stage present
                if done == False and "CountStage" in currStack:
                    analysisObject["includesCountingStage"]="True"

                if done == False and "SortStage" in currStack:
                    analysisObject["includesSortingStag"]="True"

                if done == False and "UpdateStage" in currStack:
                    analysisObject["includesUpdationStage"]="True"

                if done == False and "ProjectionStage" in currStack:
                    analysisObject["includesProjectionStage"]="True"

                # Query type if present
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

                # Higher positions in stack, interval should be precise to catch these.
                if done == False and "ExprMatchExpression" in currStack:
                    analysisObject["includesExpressionMatching"]="True"
                
                if done == False and "PathMatchExpression" in currStack:
                    analysisObject["currentlyMatchingDocuments"]="Matching Path for expression (still deciding path)"
                
                if done == False and "InMatchExpression" in currStack:
                    analysisObject["currentlyMatchingDocuments"]="Matching 'IN' expression"
                
                if done == False and "RegexMatchExpression" in currStack:
                    analysisObject["currentlyMatchingDocuments"]="Matching 'REGEX' expression"
                
                if done == False and "ComparisonMatchExpression" in currStack:
                    analysisObject["currentlyComparingValues"]="True"
                
                if done == False and "getNextDocument" in currStack:
                    analysisObject["fetchingNextDocument"]="True"
                
                if done == False and "compareElementStringValues" in currStack:
                    analysisObject["currentlyComparingStringValues"]="True"
                jsonObject["threads"][threadId]["iterations"][i]["analysis"]=analysisObject
            except: 
                print("Something went wrong while performing analysis")
            # Find the current operation of the current thread (by thread name)
            try:
                currentOpObject = currentOps[currIteration]
                if len(currentOpObject)!=0:
                    myCurrentOpObject={}
                    for item in currentOpObject["inprog"]:
                        if item["desc"] == currName:
                            myCurrentOpObject["command"] = item
                            break
                    jsonObject["threads"][threadId]["iterations"][i]["currentOp"]=myCurrentOpObject
            except: 
                print("Something went wrong while parsing current operations")

    try:       
        a_file = open("OutputFiles/"+OUTPUT_FILE_NAME+".json", "w")
        json.dump(jsonObject, a_file)
        a_file.close()
    except:
        print("Something went wrong while accessing file after performing analysis")

# Function to create JSON file from collected data
def createJsonFile(allIterationsThreads):
    # Creating the JSON Object to be stored
    entireJsonObject={}
    entireJsonObject["threads"]={}
    for i in range(0,NUMCALLS):
        try:
            currIterationDict=allIterationsThreads[i]

            # Iterate over all thread information available and create individual thread objects
            for threadId,thread in currIterationDict.items():
                currThreadObject={}
                # Basically in first iteration, the thread won't be present and would have to be created explicitly.
                if threadId not in entireJsonObject["threads"]:
                    currThreadObject={}
                    currThreadObject["threadId"]=threadId
                    currThreadObject["iterations"]=[]
                else:
                    currThreadObject=entireJsonObject["threads"][threadId]
                
                # Create current iteration for this thread
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
        except:
            print("Something went wrong while creating JSON File")

    try:
        jsonFile = open("OutputFiles/"+OUTPUT_FILE_NAME+".json", "w")
        json.dump(entireJsonObject, jsonFile)
        jsonFile.close()
    except:
        print("Couldn't open file for creating JSON")

# Function to show help menu
def showHelp():
    # Display Help
    print("")
    print("Syntax: python stackTraceTool.py [-n 3 -I 0.5] [-c|N|h]")
    print("options:")
    print("n or --num-iterations         Provide number of iterations for stack (REQUIRED).")
    print("I or --interval               Provide the INTERVAL between iterations (in seconds) (REQUIRED).")
    print("c or --cpu-threshold          Provide the CPU Usage Threshold for threads (0-100) (OPTIONAL) - Default = 20")
    print("N or --num-threads            Provide the Number of Threads to be taken (>0) (OPTIONAL) - Default = 20")
    print("h or --help                   Show the help menu")
    print("")
    exit

# Function to parse the command line options
def parseOptions(argv):
    global NUMCALLS
    global INTERVAL
    global CPU_THRESHOLD
    global TOP_N_THREADS
    try:
    #   h requires no input, so no colon for it
        opts, args = getopt.getopt(argv,"n:I:c:N:h",["num-iterations=","interval=","cpu-threshold=","num-threads=","help"])
    except getopt.GetoptError:
        showHelp()
        sys.exit(2)
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            showHelp()
            sys.exit()
        elif opt in ("-n", "--num-iterations"):
            try:
                NUMCALLS=int(arg)
                if NUMCALLS <= 0:
                    sys.exit(2)
            except:
                print("Number of Iterations should be an integer greater than 0. Value provided was: " + str(arg) + "\nExiting")
                sys.exit(2)
        elif opt in ("-I", "--interval"):
            try:
                INTERVAL = float(arg)
                if INTERVAL <= 0:
                    sys.exit(2)
            except:
                print("Interval should be an integer/float greater than 0. Value provided was: " + str(arg) + "\nExiting")
                sys.exit(2)
        elif opt in ("-c", "--cpu-threshold"):
            try:
                CPU_THRESHOLD = float(arg)
                if CPU_THRESHOLD > 100 or CPU_THRESHOLD < 0:
                    sys.exit(2)
            except:
                print("CPU Threshold should be an integer/float between 0 and 100. Value provided was: " + str(arg) + "\nExiting")
                sys.exit(2)
        elif opt in ("-N", "--num-threads"):
            try:
                TOP_N_THREADS = int(arg)
                if TOP_N_THREADS <=0:
                    sys.exit(2)
            except:
                print("Number of threads should be an integer greater than 0. Value provided was: " + str(arg) + "\nExiting")
                sys.exit(2)
    if NUMCALLS==-1:
        print("Number of iterations is a required option. Refer to --help for further information")
        sys.exit(2)
    if INTERVAL==-1:
        print("Interval is a required option. Refer to --help for further information")
        sys.exit(2)
    if CPU_THRESHOLD==-1:
        CPU_THRESHOLD=20.0
    if TOP_N_THREADS == -1:
        TOP_N_THREADS = 20
    print("Parameters used: ")
    print("")
    print("CPU Threshold: " + str(CPU_THRESHOLD))
    print("Top N Threads: " + str(TOP_N_THREADS))
    print("Interval (s): " + str(INTERVAL))
    print("Number of Iterations: " + str(NUMCALLS)) 
    print("")


    

if __name__ == "__main__":

    print("Starting script at " + str(int(round(time.time() * 1000)))[-6:])
    print("")
    parseOptions(sys.argv[1:])

    manager = multiprocessing.Manager()

    # Stores information for all iterations in a list as [iteration0,iteration1,...]
    allIterationsThreads=[]

    # Shared dictionary for storing CurrentOps data
    currentOps=manager.dict()
    # List used to store multithreaded processes of currentOps command
    currentOpProcesses=[]

    # Gather Information
    for i in range(0,NUMCALLS):
        time1=int(round(time.time() * 1000))

        print("Starting iteration " + str(i) + " at time: " + str(int(round(time.time() * 1000)))[-6:])

        # Dictionary used to store data for current iteration.
        threads=manager.dict()

        # Start the currentOp process first seperately as it takes way longer than other operations.
        currentOpProcess=multiprocessing.Process(target=runCurrentOpsCommand,args=(currentOps,i,))
        currentOpProcess.start()
        currentOpProcesses.append(currentOpProcess)
        
        # Major information collection for this iteration starting
        gatherThreadInformation(threads)

        # threads dictionary is now filled with data
        allIterationsThreads.append(threads)
        
        # Subtract the time which has already been taken to execute commands from interval. 
        # For example, if commands already took 2seconds, don't have to wait the extra 0.5s from interval. 
        time2=int(round(time.time() * 1000))
        timediff = time2-time1
        error = INTERVAL - timediff/1000
        if error <=0:
            pass
        else:
            time.sleep(error)
        print("Completed iteration : " +str(int(round(time.time() * 1000)))[-6:]+"\n\n")
        
    
    # We wait for current ops before creating JSON file
    print("Now waiting for currentOps to complete: " + str(int(round(time.time() * 1000)))[-6:])
    for process in currentOpProcesses:
        process.join()

    print("Starting to create JSON file at time: " + str(int(round(time.time() * 1000)))[-6:])
    # Create JSON File
    createJsonFile(allIterationsThreads)
    
    # Performed Analysis seperately, and not while collection, so that time between thread stacks is precise
    print("Starting analysis at time:  " + str(int(round(time.time() * 1000)))[-6:])

    # Reads data from the file created and adds analysis and currentOps in it
    performAnalysis(currentOps)