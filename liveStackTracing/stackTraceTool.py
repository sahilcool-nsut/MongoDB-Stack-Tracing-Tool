from calendar import c
from collections import defaultdict
import getopt
import json
import multiprocessing
import re
import subprocess
import sys
import time

# Arguments
NUMCALLS=-1
INTERVAL=-1
TOP_N_THREADS=-1
CPU_THRESHOLD=-1
TAKE_CURRENT_OPS=-1
PRINT_DEBUG=-1
ITERATIONS_FOUND_THRESHOLD=-1
SAVE_COMBINED_FILES=-1
OUTPUT_FILE_NAME="collectedData.json"

# Thread Class used to store thread objects
class Thread:
    def __init__(self,tid,tstate,tcpu,tname,tstack="",ttimestamp=""):
        self.threadId=tid
        self.threadName=tname
        self.threadCpu=tcpu
        self.threadState=tstate
        self.threadStack=tstack
        self.threadStackTimeStamp=ttimestamp


def printOutput(error=None,threads=None):
    global OUTPUT_FILE_NAME
    if error!=None:
        jsonObject={}
        jsonObject["success"] = "Failed"
        jsonObject["error"] = error
        try:
            jsonFile = open(OUTPUT_FILE_NAME, "w")
            # dump to store in file
            json.dump(jsonObject, jsonFile,indent=4)
            jsonFile.close()
        except:
            printOutput(error="Some Error while saving output to file")
        # dumps to just print
        print(json.dumps(jsonObject,indent=4))
        exit(1)
    else:
        jsonObject=threads
        jsonObject["success"] = "Success"
        try:
            jsonFile = open(OUTPUT_FILE_NAME, "w")
            # dump to store in file
            json.dump(jsonObject, jsonFile,indent=4)
            jsonFile.close()
        except:
            printOutput(error="Some Error while saving output to file")
        # dumps to just print
        print(json.dumps(jsonObject,indent=4))
        exit(1)

# This function is multithreaded to collect stack information for a single thread
# -1 is an option to get stack of an individual thread given by its thread ID passed to -p
def runStackCommand(threadId,threads):
    p = subprocess.Popen("sudo eu-stack -1 -p " + str(threadId), stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    stdout, stderr = p.communicate()
    if stderr.decode('UTF-8')!='':
        currThread = threads[threadId]
        # Included TID as the web analyzer splits stacks on TID. So, maintaining the same format
        currThread.threadStack = "TID "+str(threadId)+" Error while collecting Stack (Most probably thread dissapeared)\n"
        currThread.threadStackTimeStamp=str(int(round(time.time() * 1000)))[-6:]
        threads[threadId] = currThread
    else:
        currThread = threads[threadId]
        currThread.threadStack = stdout.decode('UTF-8')
        if currThread.threadStack=="":
            # Included TID as the web analyzer splits stacks on TID. So, maintaining the same format
            currThread.threadStack="TID "+str(threadId)+" Error while collecting Stack (Most probably thread dissapeared)\n"
        currThread.threadStackTimeStamp=str(int(round(time.time() * 1000)))[-6:]
        threads[threadId] = currThread

# This function is multithreaded to collect current operations using mongo command
# JSON.stringify() to convert BSON to JSON
# --quiet is to remove the connection information we get on a new connection
def runCurrentOpsCommand(currentOps,iteration):
    p = subprocess.Popen("mongo localhost:27017 --eval 'JSON.stringify(db.currentOp())' --quiet", stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    stdout, stderr = p.communicate()
    if(stderr.decode('UTF-8')!=''):
        currentOps[iteration]={}
    currentOps[iteration]=json.loads(stdout.decode('UTF-8'))

# Driver Function to gather thread information from top and eu-stack commands
def gatherThreadInformation(threads):
    # Call top command in batch mode(-b) and limit it for 1 iteration (n1). 
    # Grep for clients with name starting as "conn.." as these are CLIENT threads for mongodb
    # Also, use parameter TOP_N_THREADS to limit results
    # Sorting is done by threadId (-k1 = first field, -n = numeric). This is done so that relative order of sorting remains same, and we can achieve precision in intervals
    # Although the impact of sorting may be very less, but it can be useful in case of very slow running commands 
    
    p = subprocess.Popen("top -H -bn1 -w512 | grep -m " + str(TOP_N_THREADS) + " 'conn' | sort -n -k1", stdout=subprocess.PIPE,stderr=subprocess.PIPE, shell=True)
    stdout, stderr = p.communicate()
    if(stderr.decode('UTF-8')!=''):
        printOutput(error=stderr.decode('UTF-8'))
    
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
    if PRINT_DEBUG==1:
        print("Starting multiprocessing of eu-stack calls at time: " +str(int(round(time.time() * 1000)))[-6:]) 
    # Collect stacks   
    for threadId,thread in threads.items():
        process=multiprocessing.Process(target=runStackCommand,args=(threadId,threads,))
        process.start()
        totalProcesses.append(process)
    if PRINT_DEBUG==1:
        print("All processes were created, now waiting : " +str(int(round(time.time() * 1000)))[-6:])
    for p in totalProcesses:
        p.join()
    

# Function to perform analysis on the stacks and save it in the JSON file
def performAnalysis(currentOps,finalJsonObject):

    # Iterate over each thread and each iteration of the thread
    for threadId in finalJsonObject["threads"]:
        # lists used to collect items for overall analysis
        cpuCounts=[]
        currIterationsStacks=[]
        analysisList=[]
        for i in range(0,len(finalJsonObject["threads"][threadId]["iterations"])):
            # Iteration Wise Analysis
            try:
                analysisObject={}
                currIteration=finalJsonObject["threads"][threadId]["iterations"][i]["iteration"]
                currStack=finalJsonObject["threads"][threadId]["iterations"][i]["threadStack"]
                currState=finalJsonObject["threads"][threadId]["iterations"][i]["threadState"]
                currName=finalJsonObject["threads"][threadId]["iterations"][i]["threadName"]
                currCpu = float(finalJsonObject["threads"][threadId]["iterations"][i]["threadCpu"])
                                
                # Store for overall analysis
                cpuCounts.append(currCpu)
                currIterationsStacks.append(currStack)
                # Corner case for bad stacks collected
                # Stack would be something like TID 12314: (and nothing ahead)
                if len(currStack.split('\n')) <=1:
                    continue
                try:
                    # Gets the stage/scan
                    doWorkRegexResults = re.findall('::(.+?)::doWork',currStack)
                    if len(doWorkRegexResults) > 0:
                        analysisObject["StagesAndScans"]={"Description": "The following stages were found somewhere in the stack, and can give some idea about what type of scans are being made, what functions of these scans are called etc."}
                        for function in doWorkRegexResults:
                            # Create individual object for each stage/scan as they can contain more functions
                            # Their individual functions are found using their namespace
                            analysisObject["StagesAndScans"][function]={}
                            analysisObject["StagesAndScans"][function]["FoundInStack"]="True"
                            individualFunctionRegexResults = re.findall(function+'::(.+?)\(',currStack)
                            if len(individualFunctionRegexResults) > 0:
                                # No need to include doWork as we used it just for extraction of function
                                if "doWork" in individualFunctionRegexResults:
                                    individualFunctionRegexResults.remove("doWork")
                                if len(individualFunctionRegexResults) > 0:
                                    functionsList=[]
                                    for indiFunction in individualFunctionRegexResults:
                                        functionsList.append({indiFunction:"called"})
                                    analysisObject["StagesAndScans"][function]["FunctionsCalled"]=functionsList
                except: 
                    pass
                
                try:
                    # Find "matching" part if the query has any such part
                    matchRegexResults = re.findall('::(.+?)::matches',currStack)
                    if len(matchRegexResults) > 0:
                        analysisObject["ExpressionMatching"]={"Description": "These elements can give idea about what type of expressions are being used to match the documents"}
                        # Check for REGEX namespace and give special attention
                        regexNamespaceRegexResults=re.findall('::RE::',currStack)
                        if len(regexNamespaceRegexResults) > 0:
                            analysisObject["ExpressionMatching"]["Contains RE Namespace"]={}
                            analysisObject["ExpressionMatching"]["Contains RE Namespace"]["Contains REGEX Matching"]="True"
                            individualFunctionRERegexResults = re.findall("RE"+'::(.+?)\(',currStack)
                            if len(individualFunctionRegexResults) > 0:
                                functionsList=[]
                                for indiFunction in individualFunctionRERegexResults:
                                    functionsList.append({indiFunction:"called"})
                                analysisObject["ExpressionMatching"]["Contains RE Namespace"]["FunctionsCalled"]=functionsList

                        # Basic "matches" namespaces, can give some idea about where thread is right now
                        for function in matchRegexResults:
                            analysisObject["ExpressionMatching"][function]={}
                            if function=="PathMatchExpression":
                                analysisObject["ExpressionMatching"][function]["Evaluating Execution Path"]="True"
                            analysisObject["ExpressionMatching"][function]["FoundInStack"]="True"
                            individualFunctionMatchingRegexResults = re.findall(function+'::(.+?)\(',currStack)
                            if len(individualFunctionMatchingRegexResults) > 0:
                                # Can remove matches, just like we removed doWork above.
                                if "matches" in individualFunctionMatchingRegexResults:
                                    individualFunctionMatchingRegexResults.remove("matches")
                                if len(individualFunctionMatchingRegexResults) > 0:
                                    functionsList=[]
                                    for indiFunction in individualFunctionMatchingRegexResults:
                                        functionsList.append({indiFunction:"called"})
                                    analysisObject["ExpressionMatching"][function]["FunctionsCalled"]=functionsList
                    
                    # Similar to ExpressionMatching, we can use BSONElement namespace to find some very high level stack functions
                    
                    bsonElementRegexResults=re.findall('BSONElement::(.+?)\(',currStack)
                    if len(bsonElementRegexResults) > 0:
                        if "ExpressionMatching" not in analysisObject:
                            analysisObject["ExpressionMatching"]={"Description": "These elements can give idea about what type of expressions are being used to match the documents"}
                        
                        for function in bsonElementRegexResults:
                            analysisObject["ExpressionMatching"]["BSONElement::"+function]={}
                            analysisObject["ExpressionMatching"]["BSONElement::"+function]["FoundInStack"]="True"
                            
                except:
                    pass
                
                # Find query command given using run()
                try:
                    commandRegexResults=re.findall('\(anonymous namespace\)::(.+?)::run\(mongo',currStack)
                    if len(commandRegexResults) > 0:
                        analysisObject["CommandFoundInStack"]={"Description":"This section includes the commands which may have been run on the current thread"}
                        for function in commandRegexResults:
                            # Most probably function would be found in line with typedRun() rather than run(). So, check that.
                            # In case some issue in retriveing it from typedRun(), we keep the run() result
                            if ">" in function:
                                typedRunCommandRegexResults=re.findall('\(anonymous namespace\)::(.+?)::typedRun\(mongo',currStack)
                                if len(typedRunCommandRegexResults) > 0:
                                    for function2 in typedRunCommandRegexResults:
                                        if ">" in function2:
                                            analysisObject["CommandFoundInStack"][function]="True"
                                        else:
                                            analysisObject["CommandFoundInStack"][function2]="True"
                                else:
                                    analysisObject["CommandFoundInStack"][function]="True"
                            else:
                                analysisObject["CommandFoundInStack"][function]="True"
                except:
                    pass
                
                # Concurrency Related
                try:
                    lockRegexResults=re.findall('Mutex::(.+?)\(\)',currStack)
                    if len(lockRegexResults) > 0:
                        if "ConcurrencyRelated" not in analysisObject:
                            analysisObject["ConcurrencyRelated"]={"Description":"This section includes the commands which may be related to concurrency operations etc."}
                        for function in lockRegexResults:
                            analysisObject["ConcurrencyRelated"][function]="Lock related operation found in stack"
                    lockWaitRegexResults=re.findall('__lll_lock_wait',currStack)
                    if len(lockWaitRegexResults) > 0:
                        if "ConcurrencyRelated" not in analysisObject:
                            analysisObject["ConcurrencyRelated"]={"Description":"This section includes the commands which may be related to concurrency operations etc."}
                        for function in lockWaitRegexResults:
                            analysisObject["ConcurrencyRelated"][function]="Lock waiting operation found in stack"
                    yieldRegexResults=re.findall('__sched_yield',currStack)
                    if len(yieldRegexResults) > 0:
                        if "ConcurrencyRelated" not in analysisObject:
                            analysisObject["ConcurrencyRelated"]={"Description":"This section includes the commands which may be related to concurrency operations etc."}
                        for function in yieldRegexResults:
                            analysisObject["ConcurrencyRelated"][function]="Yield related operation found in stack"
                    
                except:
                    pass

                # WiredTiger
                try:
                    wiredTigerRegexResults=re.findall('::WiredTiger(.+?)\(',currStack)
                    if len(wiredTigerRegexResults) > 0:
                        if "WiredTiger" not in analysisObject:
                            analysisObject["WiredTiger"]={"Description": "This section contains commands related to WiredTiger (the storage engine) that were called"}
                        for function in wiredTigerRegexResults:
                            analysisObject["WiredTiger"]["WiredTiger"+function]="Found in stack"
                except:
                    pass
                # Ensure that currState is Sleeping if allocating any of these, as these don't make sense if state is Running, and can be misleading  
                if "recvmsg" in currStack:
                    if currState=="S":
                        analysisObject["clientState"]="Client may be waiting for Query to be given"
                if "__poll" in currStack:
                    if currState=="S":
                        analysisObject["clientState"]="Polling"

                finalJsonObject["threads"][threadId]["iterations"][i]["analysis"]=analysisObject
                analysisList.append(analysisObject)
            except: 
                print("Something went wrong while performing analysis")
            # Find the current operation of the current thread (by thread name)
            if(TAKE_CURRENT_OPS==1):
                try:
                    currentOpObject = currentOps[currIteration]
                    if len(currentOpObject)!=0:
                        myCurrentOpObject={}
                        for item in currentOpObject["inprog"]:
                            if item["desc"] == currName:
                                myCurrentOpObject["command"] = item
                                break
                        finalJsonObject["threads"][threadId]["iterations"][i]["currentOp"]=myCurrentOpObject
                except: 
                    print("Something went wrong while parsing current operations")
        

        # Overall Thread Analysis
        overallAnalysis={}

        # Merge all individual iterations
        # For this, we have assumed that major category is the first key (like ScanStage, ExpressionMatching)
        # Inside them, the individual functions are appended in a list
        # Only first level key is taken into consideration, inner nesting information is not taken here, as it is just a short cumulative summary

        try:
            dd = defaultdict(list)
            for d in tuple(analysisList):
                for key, value in d.items():
                    if type(value) is dict:
                        for stageName in value:
                            # No need to add description here
                            if stageName=="Description":
                                continue
                            dd[key].append(stageName)
                        if len(dd[key])==0:
                            dd[key]=[]
                        else:
                            tempList = dd[key]
                            dd[key] = list(set(tempList))

            overallAnalysis["mergedStackAnalysis"]=dd
            # For client waiting for query status
            clientStateCount=0
            for analysis in analysisList:
                if "clientState" in analysis:
                    if analysis["clientState"]=="Client may be waiting for Query to be given":
                        clientStateCount+=1
            if clientStateCount == len(analysisList):
                overallAnalysis["mergedStackAnalysis"]["clientState"]="Client seems to have no query running throughout all iterations"
            # Can check for multiple commands to warn that combined stack analysis is of more than 1 query
            if "CommandFoundInStack" in overallAnalysis["mergedStackAnalysis"]:
                numCommands = len(overallAnalysis["mergedStackAnalysis"]["CommandFoundInStack"])
                if numCommands>=2:
                    overallAnalysis["numberOfQueries"]="Thread was captured making more than 1 different query over iterations"
        except: 
            pass

        # CPU ANALYSIS
        if len(cpuCounts)>0:
            avgCpu=0
            for i in range(0,len(cpuCounts)):
                avgCpu+=cpuCounts[i]
            avgCpu=float(avgCpu/len(cpuCounts))
            overallAnalysis["avgCpu"]="{:.2f}".format(avgCpu)
        else:
            overallAnalysis["avgCpu"]=0
        
        if len(currIterationsStacks) >1:
            overallAnalysis["cpuStats"]={}
            increasingCpuTrend= all(i <= j for i, j in zip(cpuCounts, cpuCounts[1:]))
            decreasingCpuTrend= all(i >= j for i, j in zip(cpuCounts, cpuCounts[1:]))
            equalCpuTrend = all(i == j for i, j in zip(cpuCounts, cpuCounts[1:]))
            if equalCpuTrend == True:
                if avgCpu > CPU_THRESHOLD:
                    overallAnalysis["cpuStats"]["cpuTrend"]="Thread has equal CPU for each iteration. Its Average CPU is greater than threshold. It may be problematic"
                else:
                    overallAnalysis["cpuStats"]["cpuTrend"]="Thread has equal CPU for each iteration, but its average CPU remains lower than threshold."
            elif increasingCpuTrend == True:
                if avgCpu > CPU_THRESHOLD:
                    if abs(cpuCounts[0] - cpuCounts[len(cpuCounts)-1]) > CPU_THRESHOLD:
                        overallAnalysis["cpuStats"]["cpuTrend"]="Thread has increasing cpu utilization over iterations. Its Average CPU is greater than threshold."
                    else:
                        overallAnalysis["cpuStats"]["cpuTrend"]="Thread has increasing cpu utilization over iterations. Its Average CPU is greater than threshold."
                else:
                    overallAnalysis["cpuStats"]["cpuTrend"]="Thread has increasing cpu utilization over iterations, but its average CPU remains lower than threshold."
            elif decreasingCpuTrend == True:
                if abs(cpuCounts[0] - cpuCounts[len(cpuCounts)-1]) < CPU_THRESHOLD:
                    overallAnalysis["cpuStats"]["cpuTrend"]="Thread has decreasing cpu utilization over iterations."
                else:
                    overallAnalysis["cpuStats"]["cpuTrend"]="Thread has decreasing cpu utilization over iterations. The drop in CPU usage was large, and hence it may not be problematic"
            else:
                overallAnalysis["cpuStats"]["cpuTrend"]="No monotically increasing or decreasing trend seen for thread over iterations "

            if any(abs(i-j) > CPU_THRESHOLD for i, j in zip(cpuCounts, cpuCounts[1:])):
                overallAnalysis["cpuStats"]["cpuDiff"]="Differences in CPU utilization were high over iterations"
            else:
                overallAnalysis["cpuStats"]["cpuDiff"]="Differences in CPU utilization were not much over iterations"
        # Stack Changing Analysis
        if len(currIterationsStacks) >1:
            res = all(ele == currIterationsStacks[0] for ele in currIterationsStacks)
            if(res):
                overallAnalysis["stacksOverIterations"] = "Stacks were same over all iterations"
            else:
                overallAnalysis["stacksOverIterations"] = "Stacks changed over different iterations"
        finalJsonObject["threads"][threadId]["overallAnalysis"]=overallAnalysis

    
    finalJsonObject["threads"]=dict(sorted(finalJsonObject["threads"].items(), key=lambda item: item[1]["overallAnalysis"]["avgCpu"],reverse=True))
    return finalJsonObject

# Function to create JSON Object from collected data
def createJsonObject(allIterationsThreads):
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
    
    # Threshold threads according to the number of iterations they were seen in.
    afterThresholdingJsonObject={}
    afterThresholdingJsonObject["threads"]={}
    for threadId,currentThreadObject in entireJsonObject["threads"].items():
        if(len(currentThreadObject["iterations"])>=ITERATIONS_FOUND_THRESHOLD):
            afterThresholdingJsonObject["threads"][threadId]=currentThreadObject
    return afterThresholdingJsonObject


def createCombinedFiles(completeJsonObject):
    euStacks={}
    topFiles={}
    try:
        for threadId,thread in completeJsonObject["threads"].items():
            for j in range(0,len(finalJsonObject["threads"][threadId]["iterations"])):
                currIterationObject=finalJsonObject["threads"][threadId]["iterations"][j]
                currIterationNum = currIterationObject["iteration"]
                if currIterationNum not in euStacks:
                    euStacks[currIterationNum]=""
                euStacks[currIterationNum]+=currIterationObject["threadStack"]
                #   22865 mongodb   20   0 2098744 455476  52788 R  27.8   5.7   0:02.19 conn719
                if currIterationNum not in topFiles:
                    topFiles[currIterationNum]=""
                topString=str(threadId) + " - " + "- " + "- " + "- " + "- " + "- " + currIterationObject["threadState"] + " " + str(currIterationObject["threadCpu"]) + " - " + "- " + currIterationObject["threadName"] + "\n"
                topFiles[currIterationNum]+=topString
    except:
        print("Problem in creating combined files")
    for i in range(0,NUMCALLS):
        fileName = "eustack_"+str(i)+".txt"
        if i in euStacks:
            textFile = open(fileName, "w")
            textFile.write(euStacks[i])
            textFile.close()
        fileName = "topH_"+str(i)+".txt"
        if i in topFiles:
            textFile = open(fileName, "w")
            textFile.write(topFiles[i])
            textFile.close()

# Function to show help menu
def showHelp():
    # Display Help
    print("")
    print("Syntax: python stackTraceTool.py [-n 3 -I 0.5] [-c|N|t|C|s|d|h]")
    print("options:")
    print("n or --num-iterations")
    print("Provide number of iterations for stack (REQUIRED).")
    print("")
    print("I or --interval")
    print("Provide the INTERVAL between iterations (in seconds) (REQUIRED).")
    print("")
    print("c or --cpu-threshold")
    print("Provide the CPU Usage Threshold for threads (0-100) (OPTIONAL) - Default = 15")
    print("")
    print("N or --num-threads")
    print("Provide the Number of Threads to be taken (>0) (OPTIONAL) - Default = 40")
    print("")
    print("t or --threshold-iterations")
    print("Provide the number of iterations for which the thread has to be in High CPU Usage state to be considered for analysis (OPTIONAL) - Default = total number of iterations")
    print("")
    print("C or --current-ops")
    print("Use this option to capture current ops too (OPTIONAL) - Default = no current operations data provided")
    print("")
    print("s or --save")
    print("Use this option to save the combined files of each iteration - Default = no combined file is made")
    print("")
    print("d or --debug")
    print("Use this option to print timestamps and debug information for this script (OPTIONAL) - Default = no debug info")
    print("")
    print("h or --help")
    print("Show the help menu")
    print("")
    exit

# Function to parse the command line options
def parseOptions(argv):
    global NUMCALLS
    global INTERVAL
    global CPU_THRESHOLD
    global TOP_N_THREADS
    global TAKE_CURRENT_OPS
    global SAVE_COMBINED_FILES
    global PRINT_DEBUG
    global ITERATIONS_FOUND_THRESHOLD
    try:
    #   C,d,h require no input, so no colon for them
        opts, args = getopt.getopt(argv,"n:I:c:N:t:Csdh",["num-iterations=","interval=","cpu-threshold=","num-threads=","threshold-iterations=","current-ops","save","debug","help"])
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
        elif opt in ("-t", "--threshold-iterations"):
            try:
                ITERATIONS_FOUND_THRESHOLD = int(arg)
                if ITERATIONS_FOUND_THRESHOLD <=0 or ITERATIONS_FOUND_THRESHOLD > NUMCALLS:
                    sys.exit(2)
            except:
                print("Iterations threshold should have value between 1 and Number of Iterations. Value provided was: " + str(arg) + "\nExiting")
                sys.exit(2)
        elif opt in ("-C", "--current-ops"):
            TAKE_CURRENT_OPS = 1
        elif opt in ("-s", "--save"):
            SAVE_COMBINED_FILES=1
        elif opt in ("-d", "--debug"):
            PRINT_DEBUG = 1
    if NUMCALLS==-1:
        print("Number of iterations is a required option. Refer to --help for further information")
        sys.exit(2)
    if INTERVAL==-1:
        print("Interval is a required option. Refer to --help for further information")
        sys.exit(2)
    if CPU_THRESHOLD==-1:
        CPU_THRESHOLD=15.0
    if TOP_N_THREADS == -1:
        TOP_N_THREADS = 40
    if TAKE_CURRENT_OPS==-1:
        TAKE_CURRENT_OPS=0
    if SAVE_COMBINED_FILES==-1:
        SAVE_COMBINED_FILES=0
    if PRINT_DEBUG == -1:
        PRINT_DEBUG=0
    if ITERATIONS_FOUND_THRESHOLD==-1:
        ITERATIONS_FOUND_THRESHOLD = NUMCALLS
    if PRINT_DEBUG==1:
        print("Parameters used: ")
        print("")
        print("CPU Threshold: " + str(CPU_THRESHOLD))
        print("Top N Threads: " + str(TOP_N_THREADS))
        print("Interval (s): " + str(INTERVAL))
        print("Number of Iterations: " + str(NUMCALLS)) 
        print("Iterations Threshold used: " + str(ITERATIONS_FOUND_THRESHOLD))
        print("Take Current Ops: " + str(TAKE_CURRENT_OPS))
        print("Save Combined Files: " + str(SAVE_COMBINED_FILES))
        print("Print Debug: " + str(PRINT_DEBUG))
        print("")
   
if __name__ == "__main__":

    if PRINT_DEBUG==1:
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

        if PRINT_DEBUG==1:
            print("Starting iteration " + str(i) + " at time: " + str(int(round(time.time() * 1000)))[-6:])

        # Dictionary used to store data for current iteration.
        threads=manager.dict()

        # # Start the currentOp process first seperately as it takes way longer than other operations.
        if(TAKE_CURRENT_OPS==1):
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

        if PRINT_DEBUG==1:
            print("Completed iteration : " +str(int(round(time.time() * 1000)))[-6:]+"\n\n")
        
    
    # We wait for current ops before creating JSON file
    if TAKE_CURRENT_OPS==1:
        if PRINT_DEBUG==1:
            print("Now waiting for currentOps to complete: " + str(int(round(time.time() * 1000)))[-6:])
        for process in currentOpProcesses:
            process.join()

    if PRINT_DEBUG==1:
        print("Starting to create JSON file at time: " + str(int(round(time.time() * 1000)))[-6:])
    # Create JSON Object
    finalJsonObject=createJsonObject(allIterationsThreads)
    
    if PRINT_DEBUG==1:
    # Performed Analysis seperately, and not while collection, so that time between thread stacks is precise
        print("Starting analysis at time:  " + str(int(round(time.time() * 1000)))[-6:])

    completeJsonObject=performAnalysis(currentOps,finalJsonObject)

    if SAVE_COMBINED_FILES==1:
        createCombinedFiles(completeJsonObject)

    printOutput(threads=completeJsonObject)