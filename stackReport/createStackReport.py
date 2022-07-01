from datetime import date, datetime
import math
import os
from queue import Queue
import sys
import time
import re
import pydot
import matplotlib.pyplot as plt

path = os.getcwd()

# ALL SET IN setGlobals() function as require dynamic timestamp
# Files used with their paths, incase any path is to be changed, can directly change variable there

OUTPUT_FILE_PATH=""
TOP_COMMAND_FILE=""
STACK_TRACE_FILE=""
FLAME_GRAPH_PATH=""
STATE_GRAPH_PATH=""
IDENTICAL_STACK_GRAPH_PATH=""
FLAME_GRAPH_HTML_PATH=""
STATE_GRAPH_HTML_PATH=""
IDENTICAL_STACK_GRAPH_HTML_PATH=""
CUSTOM_JS_PATH=""
JQUERY_PATH=""
BOOTSTRAP_JS_PATH=""
BOOTSTRAP_CSS_PATH=""
CUSTOM_CSS_PATH=""


# Class for an individual thread object with all its attribtues
class Thread:
    def __init__(self,tid,tname,tcpu,tstate,tstack="noStackFound"):
        self.threadId=tid
        self.threadName=tname
        self.threadCpu=tcpu
        self.threadState=tstate
        self.threadStack=tstack

# Class including methods for constructing a call stack trie
class FlameGraph:
    # childrenMap contains FlameGraphNodes of the children of current node
    # data contains the current function of the node
    # count contains how many times the current function has been traversed through the trie
    # nodeNumber is unique node number
    # graphNode contains the visualization node object
    class FlameGraphNode:
        def __init__(self,data,nodeNumber,graphNode):
            self.childrenMap={}
            self.data=data
            self.count=1
            self.nodeNumber=nodeNumber
            self.graphNode=graphNode

    def __init__(self):
        self.graph=pydot.Dot(graph_type='digraph')
        # Colors in decreasing order of intensity
        self.colorsList=["#FFA500","#FFA50099","#FFA50075","#FFA50050","#FFA50040"]
        # Stores count of each function in the call stack
        self.countsDictionary={}
        # Unique node number to identify each node
        self.nodeNum=0
        # Maximum and minimum counts used to normalize counts for assigning color intensity
        self.maximumFunctionCountInTrie=0
        self.minimumFunctionCountInTrie=0
        self.createRoot()
    
    def createRoot(self):
        # Create Root Node
        rootGraphNode=pydot.Node(str(("Root",-1)))
        self.graph.add_node(rootGraphNode)
        self.root=self.FlameGraphNode("Root",-1,rootGraphNode)

    def saveGraph(self):
        self.graph.write_pdf(FLAME_GRAPH_PATH) # or png too

    # Utility function used to calculate maximum and minimum counts present in the trie
    def calculateMaximumMinimumCounts(self):
        if len(self.countsDictionary)>0:
            self.maximumFunctionCountInTrie = max(k for k, v in self.countsDictionary.items() if v > 0)
            self.minimumFunctionCountInTrie = min(k for k, v in self.countsDictionary.items() if v > 0)
        else:
            self.maximumFunctionCountInTrie=0
            self.minimumFunctionCountInTrie=0

    def insertInTrie(self,stack):
        functionsList=[]

        # Extract functions linewise from the current stack
        for function in stack.splitlines():
            
            # Sample Function -> "#1  0xFF123123 functionName::myFunc()" 
            # So, split by one or more spaces, and consider everything after the 2nd split
            tempFunctions=re.split(' +',function,maxsplit=2)
            # For corner case stacks which were not caught correctly
            if len(tempFunctions) <=2:
                continue

            currFunction=tempFunctions[2]

            # Have to replace Colons because they are present in function names in abundant quantities, and are a Parsing issue for DOT language
            # DOT language is used to create the visual graph.
            currFunction=currFunction.replace(':',';')
            functionsList.append(currFunction)


        # Start inserting each function in the trie
        # Have to reverse FunctionList as the first element is the functionlist is the top of stack, so have to construct trie from bottom to top
        # Creates a node and adds it in graph but DOESNT add edge right now, will add edge later (so that label can be correctly set with correct Count)
        currNode=self.root
        for function in reversed(functionsList):
            # If function not current in present childrenMap, then add it as new node in trie
            if function not in currNode.childrenMap:
                
                # Would require to add double quotes around function name, but now already replaced colons with semicolons, so no need
                newChildNode=pydot.Node(str((function,self.nodeNum )))
                currNode.childrenMap[function] = self.FlameGraphNode(function,self.nodeNum,newChildNode)
                self.graph.add_node(newChildNode)
                self.nodeNum=self.nodeNum+1

                # Updating Counts Dictionary
                if 1 not in self.countsDictionary:
                    self.countsDictionary[1]=0
                self.countsDictionary[1]+=1
            else:
                self.countsDictionary[currNode.childrenMap[function].count]-=1
                # only trie operation present here, rest are manipulating countsDictionary
                currNode.childrenMap[function].count +=1

                if currNode.childrenMap[function].count not in self.countsDictionary:
                    self.countsDictionary[currNode.childrenMap[function].count]=0
                self.countsDictionary[currNode.childrenMap[function].count]+=1
            currNode=currNode.childrenMap[function]
        
    # Used to traverse the graph in level order way and create "nodes" used to visualize the graph. 
    def traversal(self):
        q = Queue()
        q.put(self.root)

        while not q.empty():
            temporaryFront = q.get()
            parentNode=temporaryFront.graphNode
            # Have to add line breaks in function name to avoid very long nodes
            lineBreakedFunction='\n'.join(temporaryFront.data[i:i+100] for i in range(0, len(temporaryFront.data), 100))
            # Set Parent node label
            parentNode.set('label',lineBreakedFunction + "\n\nCount: " + str(temporaryFront.count))

            for childKey,childValue in temporaryFront.childrenMap.items():
                # Now, set labels and color of each of the child of the parent node.
                newChildNode=childValue.graphNode
                lineBreakedFunctionChild='\n'.join(childValue.data[i:i+100] for i in range(0, len(childValue.data), 100))
                newChildNode.set('label',lineBreakedFunctionChild + "\n\nCount: " + str(childValue.count))
            
                newChildNode.set('style','filled')
                currCount = childValue.count
                try:
                    normalizedCountIndexColor = min(len(self.colorsList)-1,math.floor((((self.maximumFunctionCountInTrie-currCount)/(self.maximumFunctionCountInTrie-self.minimumFunctionCountInTrie)) * 1.0) * len(self.colorsList)))
                except:
                    normalizedCountIndexColor=0
                newChildNode.set('fillcolor',self.colorsList[normalizedCountIndexColor])
                # newChildNode.set('fontcolor','white')

                edge=pydot.Edge(temporaryFront.graphNode,childValue.graphNode)
                self.graph.add_edge(edge)

                q.put(childValue)

# Function to extract thread information from files
def extractInformation():
    threads={}
    # Gather individual thread details first
    try:
        with open(TOP_COMMAND_FILE) as f:
            while True:
                individualThreadDetails = f.readline().strip()
                if not individualThreadDetails: 
                    break
                fields=individualThreadDetails.split()
                # Sample TOP output
                # 61286 mongodb   20   0 3095132   1.5g  38440 S   0.0  20.3   0:00.00 conn37
                currThread = Thread(tid=fields[0],tname=fields[11],tcpu=float(fields[8]),tstate=fields[7])
                threads[fields[0]] = currThread


        # After individual details, have to read individual stacks
        # Start reading stack trace and split by "TID" for individual stack traces
        with open(STACK_TRACE_FILE, "r") as f:
            entireStackTrace = f.read()
            entireStackTrace = entireStackTrace.split("TID")


        for currStack in entireStackTrace:
            # Remove whitespaces (include newlines and spaces) from leading and trailing areas
            currStack = currStack.strip()
            # First line of the extracted stack contains the tid time() * 1000)))as -> 12312: 
            splitStackForTID=currStack.split('\n',1)        # Limit split to 1, so that we retrieve the first line(The TID)
            # For bad stacks
            if len(splitStackForTID) < 2:
                continue
            # Extract threadID from left of ':'
            currThreadId=splitStackForTID[0].split(':')[0]
            if currThreadId not in threads.keys():
                continue
            currStack=splitStackForTID[1]
            threads[currThreadId].threadStack = currStack
        threads=dict(sorted(threads.items(), key=lambda item: item[1].threadCpu,reverse=True))
    except:
        print("Some Error occurred while extracting information. Please check if the files are present in the correct directory (/data folder)")
        sys.exit(2)
    return threads

# Driver Function to create the flame graph using the FlameGraph class. Also embeds the pdf in the HTML
def createFlameGraph(threads):
    global htmlData
    flameGraph = FlameGraph()

    # Create nodes and insert in the trie
    for key,thread in threads.items():
        currStack = thread.threadStack
        flameGraph.insertInTrie(currStack)

    flameGraph.calculateMaximumMinimumCounts()
    
    # Insert Edges
    flameGraph.traversal()
    flameGraph.saveGraph()
    # Insert the flame graph in the HTML. iframe is used to embed the pdf with zoom options
    htmlData+='''
        <section id="flameGraph">
            <h2>II. Call Stack (Flame Graph)</h2>
            <p> Shows the call stack in the form of a tree </p>
            <p> Darker the node, more frequently it appeared in the call stack. Individual node counts are also appended in the label </p>
            <div class="chart-panel">
                <iframe src="'''+FLAME_GRAPH_HTML_PATH+'''" title="Flame Graph" height="800px" width="100%" /></iframe>
            </div>
            <hr class="solid">
        </section>
    '''
    return flameGraph

# Function to create the State Distribution Pie Graph. Also creates a table with state frequencies
def createStateDistributionGraph(threads):
    global htmlData
    # Based on linux thread states
    stateNamesMap={"S":"Sleeping\n(Interruptable)","R":"Running","t":"Stopped","D":"Sleeping\n(Uninterruptable)","Z":"Zombie"}
   
    # Counts of individual states present in current thread data
    stateCountMap={}
    for key,thread in threads.items():
        currState=thread.threadState
        if currState not in stateCountMap:
            stateCountMap[currState]=1
        else:
            stateCountMap[currState]+=1

    # sort by reversed frequency
    stateCountMap=dict(sorted(stateCountMap.items(), key=lambda item: item[1],reverse=True))
    # Create Pie Graph
    countList=[]
    labels=[]
    explode=[]
    for state in stateCountMap:
        countList.append(stateCountMap[state])
        labels.append(stateNamesMap[state])
        explode.append(0.2)

    plt.pie(countList, labels = labels, explode = explode,autopct='%1.1f%%',startangle=90)
    plt.savefig(STATE_GRAPH_PATH)
    
    # Create the HTML data 
    # Two column layout, left column includes state name and state count, while right column has the pie graph png
    # Left column is further divided into rows of state information
    htmlData+='''
    <section id="threadStateDistribution">
    <h2>I. Thread State Distribution</h2>
    <p> Pie graph to illustrate the different states of threads present </p>
    <div class="container">
        <div class="row align-items-center">
            <div class="col-sm">
                <!-- Used to make state information in rows -->
                <div class="row">
        '''
    # Loop over the different states
    for state in stateCountMap:
        htmlData+='''
                    <div class="col">
                        <div class ="chart-panel" style="padding:12px 24px">
                            <div style="text-align:center;font-size:48px;font-weight:bold;">
                    '''
        htmlData+=str(stateCountMap[state])
        htmlData+='''       </div>
                        <hr class='solid'>
                            <div style="text-align:center;">'''
        htmlData+=stateNamesMap[state]
        htmlData+='''
                            </div>
                        </div>
                    </div>
        '''
    htmlData+='''
                </div>
            </div>
            <div class="col-sm">
                <img class="chart-panel" src = "'''+STATE_GRAPH_HTML_PATH+'''" alt = "Thread State Distribution Graph" />
            </div>
        </div>
    </div>
    </section>
    <hr class="solid">
    '''
    plt.close()

# Function to create the thread information table
def createThreadTable(threads):
    global htmlData
    htmlData+='''
    <section id="individualThreadDetails">
    <h2>VI. Individual Thread Details</h2>
    <p> Shows details of each thread </p>
    <table class="chart-panel">
    <tr>
        <th>Thread ID</th>
        <th>Thread Name</th>
        <th>Thread State</th>
        <th>Thread CPU</th>
    </tr>'''
    # print(htmlData)
    for threadID,thread in dict(sorted(threads.items(), key=lambda item: item[1].threadCpu,reverse=True)).items():
        htmlData+="<tr>"
        htmlData+="<td style='text-align:center'>" + threadID + "</td>"
        htmlData+="<td style='text-align:center'>" + thread.threadName + "</td>"
        htmlData+="<td style='text-align:center'>" + thread.threadState + "</td>"
        htmlData+="<td style='text-align:center;font-weight:bold;'>" + str(thread.threadCpu)+ "</td>"
        htmlData+="<tr>"
    htmlData+='''
    </table>
    <hr class="solid">
    </section>
    '''

# Takes input list of unique stacks present, and returns a dictionary of analysis objects of each stack
def getStackTraceAnalysis(stackTracesList):
    stackTraceAnalysis={}
    # Iterate over unique stack traces
    for currStack in stackTracesList:
        currAnalysisObject={}
        if len(currStack.split('\n')) <=1:
                currAnalysisObject["invalid stack"]="true"
                stackTraceAnalysis[currStack] = currAnalysisObject
                continue

        done=False
        # Incase any of these hit, no need to check further
        if done == False and "recvmsg" in currStack:
            currAnalysisObject["queryState"]="Idle"
            done=True
        if done == False and "__poll" in currStack:
            currAnalysisObject["queryState"]="Polling"
            done=True
        
        # Type of Scan present
        if done == False and "CollectionScan" in currStack:
            currAnalysisObject["includesCollectionScan"]="True"

        if done == False and "CountScan" in currStack:
            currAnalysisObject["includesCountScan"]="True"

        # Type of Stage present
        if done == False and "CountStage" in currStack:
            currAnalysisObject["includesCountingStage"]="True"

        if done == False and "SortStage" in currStack:
            currAnalysisObject["includesSortingStag"]="True"

        if done == False and "UpdateStage" in currStack:
            currAnalysisObject["includesUpdationStage"]="True"

        if done == False and "ProjectionStage" in currStack:
            currAnalysisObject["includesProjectionStage"]="True"

        # Query type if present
        if done == False and "FindCmd" in currStack:
            currAnalysisObject["queryType"]="Find"

        if done == False and "CmdCount" in currStack:
            currAnalysisObject["queryType"]="Count"

        if done == False and "CmdFindAndModify" in currStack:
            currAnalysisObject["queryType"]="FindAndModify"
        
        if done == False and "PipelineCommand" in currStack:
            currAnalysisObject["queryType"]="Pipeline"

        if done == False and "runAggregate" in currStack:
            currAnalysisObject["queryType"]="Aggregation"

        if done == False and "CmdInsert" in currStack:
            currAnalysisObject["queryType"]="Insert"

        # Higher positions in stack, interval should be precise to catch these.
        if done == False and "ExprMatchExpression" in currStack:
            currAnalysisObject["includesExpressionMatching"]="True"
        
        if done == False and "PathMatchExpression" in currStack:
            currAnalysisObject["currentlyMatchingDocuments"]="Matching Path for expression (still deciding path)"
        
        if done == False and "InMatchExpression" in currStack:
            currAnalysisObject["currentlyMatchingDocuments"]="Matching 'in' expression"
        
        if done == False and "RegexMatchExpression" in currStack:
            currAnalysisObject["currentlyMatchingDocuments"]="Matching 'Regex' expression"
        
        if done == False and "ComparisonMatchExpression" in currStack:
            currAnalysisObject["currentlyComparingValues"]="True"
        
        if done == False and "getNextDocument" in currStack:
            currAnalysisObject["fetchingNextDocument"]="True"
        
        if done == False and "compareElementStringValues" in currStack:
            currAnalysisObject["currentlyComparingStringValues"]="True"
        stackTraceAnalysis[currStack] = currAnalysisObject
    return stackTraceAnalysis


# Function to count the frequency of stack traces present, and show a bar graph and table for the same
def createIdenticalStackTracesGraph(threads):
    global htmlData
    stackTraceCount={}
    # Loop over threads and store stack counts in the map. Also, store thread ids which are having that stack trace (to be displayed later)
    for threadId,thread in threads.items():
        currStack = thread.threadStack
        currThreadId = threadId
        if currStack not in stackTraceCount.keys():
            stackTraceCount[currStack] = [currThreadId]
        else:
            stackTraceCount[currStack].append(currThreadId)
    # Sort by length of list of threadIds for each stack trace. (basically the stack trace with most count, comes first)
    stackTraceCount=dict(sorted(stackTraceCount.items(), key=lambda item: len(item[1]),reverse=True))
    

    stackAnalysisDict=getStackTraceAnalysis(list(stackTraceCount.keys()))
    i=1
    barGraphX=[]
    barGraphY=[]
    # X axis has sort names for stack traces, exact stack traces are shown in the table below the graph
    for stackTraceList in stackTraceCount.values():
        barGraphY.append(len(stackTraceList))
        barGraphX.append("S" + str(i))
        i+=1

    # creating the bar plot with dynamic X size, if width of bar = w, total width given is 2*w + 5.
    # Used bbox_inches='tight' to avoid any unnecessary padding on sides of image
    plt.figure(figsize=(1.0*len(barGraphX) + 5,7)) 
    plt.bar(barGraphX, barGraphY, color="#FFAD2F",  edgecolor='#111',
            width = 0.5)
    
    plt.ylabel("No. of threads")
    plt.title("Identical Stack Traces amongst Threads")
    plt.savefig(IDENTICAL_STACK_GRAPH_PATH,bbox_inches='tight')

    # Create Graph and Table
    htmlData+='''
    <section id="stackTraceCount">
        <h2>III. Identical Stack Traces Distribution</h2>
        <p> Shows statistics related to frequency of stack traces amongst different threads. Refer to below table for actual stack values </p>
        <img class="chart-panel" src = "'''+IDENTICAL_STACK_GRAPH_HTML_PATH+'''" alt = "Identical Stack Traces Distribution" />
        <table class="chart-panel">
        <tr>
            <th>Stack Name</th>
            <th>Stack Trace</th>
            <th>Thread Count</th>
            <th>Stack Analysis</th>
        </tr>
    '''
    # Can add thread list too, just add thread list header above and also uncomment threadList in for loop
    i=1
    for stackTrace,threadList in stackTraceCount.items():
        # white-space: pre-line is used to make \n have their effects
        # Here, read more class is using jquery function to hide entire stack traces to avoid extremely large strings in table
        htmlData+="<tr>"
        htmlData+="<td style='text-align:center'>" + "S" + str(i) + "</td>"
        htmlData+="<td style='white-space: pre-line' class='readMoreTextHide'>" + stackTrace + "</td>"
        htmlData+="<td style='text-align:center;font-weight:bold'>" + str(len(threadList)) + "</td>"

        # Analysis
        currAnalysisObject=stackAnalysisDict[stackTrace]
        htmlData+="<td>"
        htmlData+="<ul>"
        for analysisKey,analysisValue in currAnalysisObject.items():
            htmlData+="<li><b>" + analysisKey + "</b>: " + analysisValue +"</li>"
        htmlData+="<ul>"
        htmlData+="</td>"
        
        # Thread List
        # htmlData+="<td class = 'readMoreTextHide'>" + ' '.join(threadList) + "</td>"
        htmlData+="</tr>"
        i+=1
    htmlData+='''
    </table>
    <hr class="solid">
    </section>
    '''
    plt.close()

# Function to calculate and create table for frequency of function calls in entire stack trace
def createTotalFunctionCountsTable(threads):
    global htmlData
    totalFunctionCounts={}
    totalCount=0
    for threadId,thread in threads.items():
        currStack = thread.threadStack
        for function in currStack.splitlines():
            # Extract functions from the entire stack
            # Split each individual function line by one or more spaces and make only 2 splits(to remove # and hexadecimal address)
            # sample function line is : #1 0xFF123123 void main()
            tempFunctions=re.split(' +',function,maxsplit=2)
            # for handling bad stack case
            if len(tempFunctions) <=2:
                continue
            currFunction=tempFunctions[2]
            if currFunction in totalFunctionCounts:
                totalFunctionCounts[currFunction] = totalFunctionCounts[currFunction] + 1
            else:
                totalFunctionCounts[currFunction] = 1
            totalCount+=1
    # to handle division by 0
    if totalCount==0:
        totalCount=1
    htmlData+='''
    <section id="mostUsedFunctions">
    <h2>V. Most Used Functions</h2>
    <p> Shows which functions have been most used across the entire stack trace </p>
    <table class="chart-panel">
    <tr>
        <th>Thread Count</th>
        <th>Function Name</th>
        <th>Percentage</th>
    </tr>'''
    totalFunctionCounts=dict(sorted(totalFunctionCounts.items(),key=lambda item: item[1],reverse=True))
    for currFunc,currCount in totalFunctionCounts.items():
        htmlData+="<tr>"
        htmlData+="<td style='text-align:center;'>" + str(currCount) + "</td>"
        htmlData+="<td class='readMoreTextHide' style='white-space: pre-line;'>" + '\n'.join(currFunc[i:i+100] for i in range(0, len(currFunc), 100)) + "</td>"
        htmlData+="<td style='text-align:center;font-weight:bold;'>" + "{:.1f}".format((currCount/totalCount)*100) + "</td>"
        htmlData+="<tr>"
    htmlData+='''
    </table>
    <hr class="solid">
    </section>
    '''
    return totalFunctionCounts

# Function to create and display the most CPU consuming threads (top 5)
def createConsumingThreadTable(threads):
    global htmlData
    htmlData+='''
    <section id="cpuConsumingThreads">
    <h2>IV. Top CPU Consuming Threads (Top 5)</h2>
    <table class="chart-panel">
    <tr>
        <th>Thread ID</th>
        <th>Thread Name</th>
        <th>Thread State</th>
        <th>Thread CPU</th>
        <th>Thread Stack</th>
    </tr>'''
    i=0
    for threadID,thread in threads.items():
        if i==5:
            break
        # currStack = thread.threadStack.replace("\n","<br>")
        currStack = thread.threadStack
        htmlData+="<tr>"
        htmlData+="<td style='text-align:center'>" + threadID + "</td>"
        htmlData+="<td style='text-align:center'>" + thread.threadName + "</td>"
        htmlData+="<td style='text-align:center'>" + thread.threadState + "</td>"
        htmlData+="<td style='text-align:center;font-weight:bold;'>" + str(thread.threadCpu)+ "</td>"
        htmlData+='<td class="readMoreTextHide" style="white-space: pre-line">' + currStack + "</td>"
        htmlData+="<tr>"
        i+=1
    htmlData+='''
    </table>
    <hr class="solid">
    </section>
    '''

def setGlobals(TIMESTAMP):

    global OUTPUT_FILE_PATH
    global TOP_COMMAND_FILE
    global STACK_TRACE_FILE
    global FLAME_GRAPH_PATH
    global STATE_GRAPH_PATH
    global IDENTICAL_STACK_GRAPH_PATH
    global FLAME_GRAPH_HTML_PATH
    global STATE_GRAPH_HTML_PATH
    global IDENTICAL_STACK_GRAPH_HTML_PATH
    global CUSTOM_JS_PATH
    global JQUERY_PATH
    global BOOTSTRAP_JS_PATH
    global BOOTSTRAP_CSS_PATH
    global CUSTOM_CSS_PATH

    # IMPORTANT
    # FILE NAMES SHOULD NOT CONTAIN ANY '_' OTHER THAN THE ONE SEPERATING THE TIMESTAMP (used in delete logic in app.py)

    OUTPUT_FILE_PATH=os.path.join(path,"templates/StackTraceReport_"+TIMESTAMP+".html")

    # Data files uploaded by user
    TOP_COMMAND_FILE=os.path.join(path, "data/topFile_"+TIMESTAMP+".txt")
    STACK_TRACE_FILE=os.path.join(path, "data/stackFile_"+TIMESTAMP+".txt")

    # Graphs dynamically created by script
    FLAME_GRAPH_PATH=os.path.join(path, "static/graphs/flameGraph_"+TIMESTAMP+".pdf")
    STATE_GRAPH_PATH=os.path.join(path, "static/graphs/statePie_"+TIMESTAMP+".png")
    IDENTICAL_STACK_GRAPH_PATH=os.path.join(path, "static/graphs/identicalStackTraceGraph_"+TIMESTAMP+".png")

    # Graphs directory to be used in HTML code generated
    FLAME_GRAPH_HTML_PATH="{{ url_for('static', filename='graphs/flameGraph_"+TIMESTAMP+".pdf') }}"
    STATE_GRAPH_HTML_PATH="{{ url_for('static', filename='graphs/statePie_"+TIMESTAMP+".png') }}"
    IDENTICAL_STACK_GRAPH_HTML_PATH="{{ url_for('static', filename='graphs/identicalStackTraceGraph_"+TIMESTAMP+".png') }}"
    # Style/Script files 
    CUSTOM_JS_PATH="{{ url_for('static', filename='scripts/customScript.js') }}"
    JQUERY_PATH="{{ url_for('static', filename='scripts/jquery-3.6.0.min.js') }}"
    BOOTSTRAP_JS_PATH="{{url_for('static', filename='scripts/bootstrap.min.js')}}"
    BOOTSTRAP_CSS_PATH="{{ url_for('static', filename='styles/bootstrap.min.css') }}"
    CUSTOM_CSS_PATH="{{ url_for('static', filename='styles/customStyle.css') }}"


def main(TIMESTAMP):
    # Have to set globals using function as file names would be dynamic as they are using a timestamp
    setGlobals(TIMESTAMP)
    global htmlData
    # Open the HTML file and create boilerplate HTML code
    OUTPUT_FILE = open(OUTPUT_FILE_PATH,"w")

    # HTML Boilerplate, CSS and Javascript code necessary
    # Currently, Javascript code is for "read more" functionality for stack traces.
    # All files are fetched from /scripts and /styles folder
    htmlData='''
    <!doctype html>
    <html lang="en">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <!-- Include Bootstrap and Custom CSS -->
        <link rel="stylesheet" href="'''+BOOTSTRAP_CSS_PATH+'''">
        <link rel="stylesheet" href="'''+CUSTOM_CSS_PATH+'''">
        <title>Stack Trace Report</title>
    </head> 
    <body>
        <div class="sidenav">
            <div class="sidenav-title"> Eu-Stack Analyzer </div>
            <br>
            <a href="#threadStateDistribution"> - Thread State Distribution</a>
            <a href="#flameGraph"> - Call Stack (Flame Graph)</a>
            <a href="#stackTraceCount"> - Identical Stack Traces Distribution</a>
            <a href="#cpuConsumingThreads"> - Top CPU Consuming Threads </a>
            <a href="#mostUsedFunctions"> - Most Used Functions </a>
            <a href="#individualThreadDetails"> - Individual Thread Details</a>
        </div>
        <div class="main">

        <h1>Stack Trace Report for the MongoDB server</h1>
        <p> Uses eu-stack to collect stack trace and top command for gathering thread details </p>
        <br>
        <hr class="solid">           
        <br>
    '''

    # Actual driver code for creating the report    

    print("Starting Python script at time: " + str(int(round(time.time() * 1000)))[-6:])

    threads={}
    # Dictionary to access thread objects by threadId
    threads=extractInformation()
    print("Starting creation of state distribution graph at time: " + str(int(round(time.time() * 1000)))[-6:])
    createStateDistributionGraph(threads)

    print("Starting creation of flame graph at time: " + str(int(round(time.time() * 1000)))[-6:])
    createFlameGraph(threads)

    print("Starting creation of stack trace count graph at time: " + str(int(round(time.time() * 1000)))[-6:])
    createIdenticalStackTracesGraph(threads)

    print("Starting creation of Most CPU Consuming Threads: " + str(int(round(time.time() * 1000)))[-6:])
    createConsumingThreadTable(threads)

    print("Starting creation of Function Count Table at time: " + str(int(round(time.time() * 1000)))[-6:])
    totalFunctionCounts=createTotalFunctionCountsTable(threads)

    createThreadTable(threads)
    

    # Finish the html data and save the file
    htmlData+='''
    </div>
    <script src="'''+BOOTSTRAP_JS_PATH+'''"></script>
    <script src="'''+JQUERY_PATH+'''"></script>
    <script src="'''+CUSTOM_JS_PATH+'''"></script>
    </body>
    </html>'''
    OUTPUT_FILE.write(htmlData)
    OUTPUT_FILE.close()

    print("completed")
    return TIMESTAMP
if __name__ == "__main__":

    main()
    

