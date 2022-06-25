import math
from queue import Queue
import time
import json
import re
import pydot
import numpy as np
import matplotlib.pyplot as plt

# Class for an individual thread object with all its attribtues
class Thread:
    def __init__(self,tid,tname,tcpu,tstate,tstack=""):
        self.threadId=tid
        self.threadName=tname
        self.threadCpu=tcpu
        self.threadState=tstate
        self.threadStack=tstack

class FlameGraph:
    class FlameGraphNode:
        def __init__(self,data,nodeNumber,graphNode):
            self.childrenMap={}
            self.data=data
            self.count=1
            self.nodeNumber=nodeNumber
            self.graphNode=graphNode
    def __init__(self):
        self.graph=pydot.Dot(graph_type='digraph')
        self.colorsList=["#FFA500","#FFA50099","#FFA50075","#FFA50050","#FFA50040"]
        self.countsDictionary={}
        self.nodeNum=0
        self.maximumFunctionCountInTrie=0
        self.minimumFunctionCountInTrie=0
        self.createRoot()
    
    def createRoot(self):
        # Create Root Node
        rootGraphNode=pydot.Node(str(("Root",-1)))
        self.graph.add_node(rootGraphNode)
        self.root=self.FlameGraphNode("Root",-1,rootGraphNode)

    def saveGraph(self):
        self.graph.write_pdf('graphs/flameGraph.pdf') # or png too
        # <iframe src="http://docs.google.com/gview?url=http://example.com/mypdf.pdf&embedded=true" style="width:718px; height:700px;" frameborder="0"></iframe>

    def calculateMaximumMinimumCounts(self):
        if len(self.countsDictionary)>0:
            self.maximumFunctionCountInTrie = max(k for k, v in self.countsDictionary.items() if v > 0)
            self.minimumFunctionCountInTrie = min(k for k, v in self.countsDictionary.items() if v > 0)
        else:
            self.maximumFunctionCountInTrie=0
            self.minimumFunctionCountInTrie=0

    def insertInRoot(self,stack):
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
        
    def traversal(self):
        q = Queue()
        q.put(self.root)
        while not q.empty():
            temporaryFront = q.get()
            parentNode=temporaryFront.graphNode
            # Took substring of entire function for now (even though it doesnt make sense, but need it for some level of visualization)
            parentNode.set('label',temporaryFront.data[:200] + "\nCount: " + str(temporaryFront.count))

            for childKey,childValue in temporaryFront.childrenMap.items():
                newChildNode=childValue.graphNode
                newChildNode.set('label',childValue.data[:200] + "\nCount: " + str(childValue.count))
            
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
    with open('data/threadDetailsTopH.txt') as f:
        while True:
            individualThreadDetails = f.readline().strip()
            if not individualThreadDetails: 
                break
            fields=individualThreadDetails.split()
            # Sample TOP output
            # 61286 mongodb   20   0 3095132   1.5g  38440 S   0.0  20.3   0:00.00 conn37
            currThread = Thread(tid=fields[0],tname=fields[11],tcpu=fields[8],tstate=fields[7])
            threads[fields[0]] = currThread

    # Now, start reading stack trace and split by "TID" for individual stack traces
    with open("data/entireStackTrace.txt", "r") as f:
        entireStackTrace = f.read()
        entireStackTrace = entireStackTrace.split("TID")

    # 
    for currStack in entireStackTrace:
        # Remove whitespaces (include newlines and spaces) from leading and trailing areas
        currStack = currStack.strip()
        # First line of the extracted stack contains the tid as -> 12312: 
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
    return threads

# Driver Function to create the flame graph using the FlameGraph class. Also embeds the pdf in the HTML
def createFlameGraph(threads):
    global htmlData
    flameGraph = FlameGraph()

    for key,thread in threads.items():
        currStack = thread.threadStack
        flameGraph.insertInRoot(currStack)

    flameGraph.calculateMaximumMinimumCounts()
    
    # Insert Edges
    flameGraph.traversal()
    flameGraph.saveGraph()
    htmlData+='''
        <h2>Flame Graph</h2>
        <p> Shows the call stack in the form of a tree </p>
        <iframe src="graphs/flameGraph.pdf" title="Flame Graph" height="100%" width="100%" /></iframe>
        <hr class="solid">
    '''
    # imgString=image_file_path_to_base64_string('graphs/flameGraph.png')
    # htmlData+='''
    #     <h2>Flame Graph</h2>
    #     <p> Shows the call stack in the form of a tree </p>
    #     <img src="data:image/png;base64,''' + imgString + '''" title="Flame Graph" height="100%" width="100%" /></img>
    #     <hr class="solid">
    # '''
    return flameGraph

# Function to create the State Distribution Pie Graph. Also creates a table with state frequencies
def createStateDistributionGraph(threads):
    global htmlData
    stateNamesMap={"S":"Sleeping\n(Interruptable)","R":"Running","t":"Stopped","D":"Sleeping\n(Uninterruptable)","Z":"Zombie"}
   
    stateCountMap={}
    for key,thread in threads.items():
        currState=thread.threadState
        if currState not in stateCountMap:
            stateCountMap[currState]=1
        else:
            stateCountMap[currState]+=1
    stateCountMap=dict(sorted(stateCountMap.items(), key=lambda item: item[1],reverse=True))
    countList=[]
    labels=[]
    explode=[]
    for state in stateCountMap:
        countList.append(stateCountMap[state])
        labels.append(stateNamesMap[state])
        explode.append(0.2)

    plt.pie(countList, labels = labels, explode = explode,autopct='%1.1f%%',startangle=90)
    plt.savefig('graphs/statePie')
    
    htmlData+='''
    <h2>Thread State Distribution Graph</h2>
    <p> Pie graph to illustrate the different states of threads present </p>
    <img class="chart-panel" src = "graphs/statePie.png" alt = "Thread State Distribution Graph" />
    <table>
    <tr>
        <th>Thread State</th>
        <th>Thread Count</th>
    </tr>'''
    for state in stateCountMap:
        htmlData+="<tr>"
        htmlData+="<td style='text-align:center'>" + stateNamesMap[state] + "</td>"
        htmlData+="<td style='text-align:center'>" + str(stateCountMap[state]) + "</td>"
        htmlData+="<tr>"
    htmlData+='''
    </table>
    <hr class="solid">
    '''
    plt.close()

# Function to create the thread information table
def createThreadTable(threads):
    global htmlData
    htmlData+='''
    <h2>Thread Details</h2>
    <p> Shows details of each thread </p>
    <table>
    <tr>
        <th>Thread ID</th>
        <th>Thread Name</th>
        <th>Thread State</th>
        <th>Thread CPU</th>
    </tr>'''
    for threadID,thread in threads.items():
        htmlData+="<tr>"
        htmlData+="<td style='text-align:center'>" + threadID + "</td>"
        htmlData+="<td style='text-align:center'>" + thread.threadName + "</td>"
        htmlData+="<td style='text-align:center'>" + thread.threadState + "</td>"
        htmlData+="<td style='text-align:center'>" + str(thread.threadCpu)+ "</td>"
        htmlData+="<tr>"
    htmlData+='''
    </table>
    <hr class="solid">
    '''

# Function to count the frequency of stack traces present, and show a bar graph and table for the same
def createIdenticalStackTracesGraph(threads):
    global htmlData
    stackTraceCount={}
    for threadId,thread in threads.items():
        currStack = thread.threadStack
        currThreadId = threadId
        if currStack not in stackTraceCount.keys():
            stackTraceCount[currStack] = [currThreadId]
        else:
            stackTraceCount[currStack].append(currThreadId)
    # Sort by length of list of threadIds for each stack trace. (basically the stack trace with most count, comes first)
    stackTraceCount=dict(sorted(stackTraceCount.items(), key=lambda item: len(item[1]),reverse=True))
    
    i=1
    barGraphX=[]
    barGraphY=[]
    for stackTraceList in stackTraceCount.values():
        barGraphY.append(len(stackTraceList))
        barGraphX.append("S" + str(i))
        i+=1

    # creating the bar plot with dynamic X size, if width of bar = w, total width given is 2*w + 5.
    # Used bbox_inches='tight' to avoid any unnecessary padding on sides of image
    plt.figure(figsize=(1.0*len(barGraphX) + 5,7)) 
    plt.bar(barGraphX, barGraphY, color="#FFAD2F",  edgecolor='blue',
            width = 0.5)
    
    plt.ylabel("No. of threads")
    plt.title("Identical Stack Traces amongst Threads")
    plt.savefig('graphs/identicalStackTraceGraph.png',bbox_inches='tight')

    # Create Graph and Table
    htmlData+='''
    <h2>Identical Stack Traces Distribution</h2>
    <p> Shows statistics related to frequency of stack traces amongst different threads. Refer to below table for actual stack values </p>
    <img class="chart-panel" src = "graphs/identicalStackTraceGraph.png" alt = "Identical Stack Traces Distribution" />
    <table>
    <tr>
        <th>Stack Name</th>
        <th>Stack Trace</th>
        <th>Thread Count</th>
        <th>Thread List</th>
    </tr>'''
    i=1
    for stackTrace,threadList in stackTraceCount.items():
        # Necessary to replace new lines with br to actually break line in HTML
        # stackTrace = stackTrace.replace("\n","<br><br>")
        htmlData+="<tr>"
        htmlData+="<td style='text-align:center'>" + "S" + str(i) + "</td>"
        htmlData+="<td style='white-space: pre-line' class='readMore'>" + stackTrace + "....</td>"
        htmlData+="<td style='text-align:center'>" + str(len(threadList)) + "</td>"
        htmlData+="<td style='text-align:center'>" + ', '.join(threadList) + "</td>"
        htmlData+="<tr>"
        i+=1
    htmlData+='''
    </table>
    <hr class="solid">
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
    <h2>Most Used Functions</h2>
    <p> Shows which functions have been most used across the entire stack trace </p>
    <table>
    <tr>
        <th>Thread Count</th>
        <th>Function Name</th>
        <th>Percentage</th>
    </tr>'''
    totalFunctionCounts=dict(sorted(totalFunctionCounts.items(),key=lambda item: item[1],reverse=True))
    for currFunc,currCount in totalFunctionCounts.items():
        htmlData+="<tr>"
        htmlData+="<td>" + str(currCount) + "</td>"
        htmlData+="<td>" + currFunc + "</td>"
        htmlData+="<td>" + "{:.1f}".format((currCount/totalCount)*100) + "</td>"
        htmlData+="<tr>"
    htmlData+='''
    </table>
    <hr class="solid">
    '''
    return totalFunctionCounts

# Function to create and display the most CPU consuming threads (top 5)
def createConsumingThreadTable(threads):
    global htmlData
    htmlData+='''
    <h2>Top CPU Consuming Threads (Top 5)</h2>
    <table>
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
        htmlData+="<td style='text-align:center'>" + str(thread.threadCpu)+ "</td>"
        htmlData+='<td style="white-space: pre-line" class="readMore">' + currStack + "</td>"
        htmlData+="<tr>"
        i+=1
    htmlData+='''
    </table>
    <hr class="solid">
    '''

def getJsData():
    return '''
    $(document).ready(function() {
                var max = 200;
                $(".readMore").each(function() {
                    var str = $(this).text();
                    if ($.trim(str).length > max) {
                        var subStr = str.substring(0, max);
                        var hiddenStr = str.substring(max, $.trim(str).length);
                        $(this).empty().html(subStr);
                        $(this).append(' <a href="javascript:void(0);" class="link">Read more…</a>');
                        $(this).append('<span class="addText">' + hiddenStr + '</span>');
                    }
                });
                $(".link").click(function() {
                    $(this).siblings(".addText").contents().unwrap();
                    $(this).remove();
                });
            });
    '''
def getCSSData():
    return '''
    * {
                font-family:Arial, Helvetica, sans-serif;
            }
            body{
                background-color:#F6FbFb;
                padding:12px 12px;
            }
            table, th, td {
                border: 2px solid black;
                border-collapse: collapse;
                padding: 8px;
                font-family: "Lucida Console", "Courier New", monospace;
            }
            th{
                background-color:#5F9EA0
            }
            hr.solid{
                border: 0;
                margin: 40px;
                height: 1px;
                background: #333;
                background-image: linear-gradient(to right, #ccc, #333, #ccc);
                width:80%;
            }
            .chart-panel {
                margin: 20px;
                padding: 20px;
                border-radius: 10px;
                background-color: #FFFFFF;
                box-shadow: 0 16px 28px 0 rgb(216 221 230 / 50%);
            }

            .readMore .addText {
                display: none;
            }
    '''

htmlData=""
if __name__ == "__main__":

    # Open the HTML file and create boilerplate HTML code
    OUTPUT_FILE = open("StackTraceReport.html","w")

    # HTML Boilerplate, CSS and Javascript code necessary
    # Currently, Javascript code is for "read more" functionality for stack traces.
    jsData=getJsData()
    cssData=getCSSData()
    htmlData='''
    <html>
    <head>
        <style>
            '''+cssData+'''
        </style>
        <script src="https://ajax.googleapis.com/ajax/libs/jquery/3.6.0/jquery.min.js"></script>
        <script type="text/javascript">
            '''+jsData+'''
        </script>
        <title>Stack Trace Report</title>
    </head> 
    <body>
        <h1>Stack Trace report for eu-stack of the mongod server</h1>           
    '''

    # Actual driver code for creating the report    
    print("Starting Python script at time: " + str(int(time.time())))
    # Dictionary to access thread objects by threadId

    threads=extractInformation()

    print("Starting creation of state distribution graph at time: " + str(int(time.time())))
    createStateDistributionGraph(threads)

    createThreadTable(threads)
    
    print("Starting creation of flame graph at time: " + str(int(time.time())))
    createFlameGraph(threads)
    
    print("Starting creation of stack trace count graph at time: " + str(int(time.time())))
    createIdenticalStackTracesGraph(threads)

    print("Starting creation of Function Count Table at time: " + str(int(time.time())))
    totalFunctionCounts=createTotalFunctionCountsTable(threads)

    print("Starting creation of Most CPU Consuming Threads: " + str(int(time.time())))
    createConsumingThreadTable(threads)

    # Finish the html data and save the file
    htmlData+='''
    </body>
</html>'''
    OUTPUT_FILE.write(htmlData)
    OUTPUT_FILE.close()

    print("completed")

