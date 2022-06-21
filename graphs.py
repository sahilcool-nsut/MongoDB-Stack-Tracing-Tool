import math
from queue import Queue
import json
import re
import pydot
import numpy as np
import matplotlib.pyplot as plt

# childrenMap = Dictionary with Key as "Function Name" and Value as the "Next" Node
# data = Entire "Function" String
# count = Number of times the function was encountered while traversing the trie (NOT HOW MANY TIMES IT WAS FOUND IN ENTIRE STACKS, but according to order of Trie)
# nodeNumber = unique node serial number to distinguish nodes (Required for visualization purposes)
# graphNode = pydot.Node() instance for this node (For visualization purposes)
class Node:
    def __init__(self,data,nodeNumber,graphNode):
        self.childrenMap={}
        self.data=data
        self.count=1
        self.nodeNumber=nodeNumber
        self.graphNode=graphNode

# Used to just match the total count of functions in entire json file
def countTotalFunctions(totaFunctionCounts,stack):
    for function in stack.splitlines():

        # Extract functions from the entire stack
        tempFunctions=re.split(' +',function,maxsplit=2)
        if len(tempFunctions) <=2:
            continue

        currFunction=tempFunctions[2]
        currFunction=currFunction.replace(':',';')
        if currFunction in totalFunctionCounts:
            totalFunctionCounts[currFunction] = totalFunctionCounts[currFunction] + 1
        else:
            totalFunctionCounts[currFunction] = 1

nodeNum=0
countsDictionary={}
def insertInRoot(root,stack,totalFunctionCounts):
    global nodeNum
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
    currNode=root
    for function in reversed(functionsList):
        # If function not current in present childrenMap, then add it as new node in trie
        if function not in currNode.childrenMap:
            
            # Would require to add double quotes around function name, but now already replaced colons with semicolons, so no need
            newChildNode=pydot.Node(str((function,nodeNum )))
            currNode.childrenMap[function] = Node(function,nodeNum,newChildNode)
            graph.add_node(newChildNode)
            nodeNum=nodeNum+1

            # Updating Counts Dictionary
            if 1 not in countsDictionary:
                countsDictionary[1]=0
            countsDictionary[1]+=1
        else:
            countsDictionary[currNode.childrenMap[function].count]-=1
            # only trie operation present here, rest are manipulating countsDictionary
            currNode.childrenMap[function].count +=1

            if currNode.childrenMap[function].count not in countsDictionary:
                countsDictionary[currNode.childrenMap[function].count]=0
            countsDictionary[currNode.childrenMap[function].count]+=1
        currNode=currNode.childrenMap[function]

colorsList=["#FFA500","#FFA50099","#FFA50075","#FFA50050","#FFA50040"]

# Used to traverse the Trie in level order and create edges of existing ndoes.
def traversal(root,maximumCount,minimumCount):
    q = Queue()
    q.put(root)
    while not q.empty():
        temporaryFront = q.get()
        parentNode=temporaryFront.graphNode
        # Took substring of entire function for now (even though it doesnt make sense, but need it for some level of visualization)
        parentNode.set('label',temporaryFront.data[:100] + "\nCount: " + str(temporaryFront.count))

        for childKey,childValue in temporaryFront.childrenMap.items():
            newChildNode=childValue.graphNode
            newChildNode.set('label',childValue.data[:100] + "\nCount: " + str(childValue.count))
           
            newChildNode.set('style','filled')
            currCount = childValue.count
            normalizedCountIndexColor = min(len(colorsList)-1,math.floor((((maximumCount-currCount)/(maximumCount-minimumCount)) * 1.0) * len(colorsList)))
            newChildNode.set('fillcolor',colorsList[normalizedCountIndexColor])
            # newChildNode.set('fontcolor','white')

            edge=pydot.Edge(temporaryFront.graphNode,childValue.graphNode)
            graph.add_edge(edge)

            q.put(childValue)

# def getMinimumAndMaximum:
# Program Flow
print("Starting")

jsonFile = open('OutputFiles/merged.json', 'r')
values = json.load(jsonFile)
stacks=[]
currentIterationBeingConsidered=1

totalFunctionCounts={}  # For cross checking if counts are correct

print("Extracting Stacks")
for threadId in values["threads"]:
    currStack=values["threads"][threadId]["iterations"][currentIterationBeingConsidered]["threadStack"]
    # Corner case for bad stacks colelcted
    if len(currStack.split('\n')) <=1:
        continue
    stacks.append(currStack)
    countTotalFunctions(totalFunctionCounts,currStack)


print("Creating Trie")
graph=pydot.Dot(graph_type='digraph')
# graph.set('colorscheme','oranges9')
rootGraphNode=pydot.Node(str(("Root",-1)))
graph.add_node(rootGraphNode)
root=Node("Root",-1,rootGraphNode)

totalFunctionCounts["Root"]=1
for stack in stacks:
    insertInRoot(root,stack,totalFunctionCounts)


maximumCount = max(k for k, v in countsDictionary.items() if v > 0)
minimumCount = min(k for k, v in countsDictionary.items() if v > 0)

print("Creating Visualization")
# Insert Edges
traversal(root,maximumCount,minimumCount)


print("completed")

graph.write_png('graphs/flameGraph.png') # or pdf too



numIterations=int(values["numCalls"])
fig = plt.figure()
for i in range(0,numIterations):
    stateMap={}
    for threadId in values["threads"]:
        currState=values["threads"][threadId]["iterations"][i]["threadState"]
        if currState not in stateMap:
            stateMap[currState]=1
        else:
            stateMap[currState]+=1
    countList=[]
    labels=[]
    explode=[]
    for state in stateMap:
        countList.append(stateMap[state])
        labels.append(state)
        if(state=="R"):
            explode.append(0.2)
        else:
            explode.append(0)
    plt.subplot(1,numIterations,i+1)
    plt.pie(countList, labels = labels, explode = explode)

plt.savefig('graphs/statePie')


# Trial Graph Code




# counter=0
# def draw(parent, child):
#     global counter
#     counter = counter+1
#     # p_name = (shortNames[parent][:100] + "\nCount: " + str(totalFunctionCounts[parent]))
#     # c_name = (shortNames[child][:100]+ "\nCount: " + str(totalFunctionCounts[child]))
#     p_name=parent+"\nCount: " + str(totalFunctionCounts[parent])
#     c_name=child+"\nCount: " + str(totalFunctionCounts[child])
#     parentNode = pydot.Node("\"" + p_name +"\"", label="\""+parent[:50]+"\"")
#     # counter = counter+1
#     childNode = pydot.Node("\"" + c_name + "\"", label="\""+child[:50]+"\"")
#     # graph.add_node(parentNode)
#     # graph.add_node(childNode)
#     edge = pydot.Edge(parentNode, childNode)
#     graph.add_edge(edge)
#     # graph.node((storeUniqueHashWithCounter[parent.data]),p_label)
#     # graph.node((storeUniqueHashWithCounter[child]), c_label)
# #     # graph.edge((storeUniqueHashWithCounter[parent.data]), (storeUniqueHashWithCounter[child]))


# def visit(node, parent=None):
#     # print(node.data)
#     if len(node.childrenMap)==0:
#         draw(parent.data,node.data)
#         return
#     for childKey,childValue in node.childrenMap.items():
#         print("I was found in map. I am: " + str(childKey) + " \nand my parent is: " + node.data)
#         visit(childValue,node)
#     if parent:
#         print(parent.data)
#         print(node.data)
#         print("#####PRINTING PARENT AND NDOE BEFORE DRAW")
#         draw(parent.data, node.data)

# graph=pydot.Dot(graph_type='digraph',strict=True)
# # graph.add_node(pydot.Node(name="AAAAAAAAA",label="BBBBBBBBBBbb"))
# visit(root)
# graph.write_pdf('output.pdf')

# graph=graphviz.Digraph('digraph')
# # print(graph)
# # print(graph.source)
# visit(root)
# print(graph.source)
# graph.render(view=True)


# FIX STRING UTIL FUNCTION (NOT USED NOW)


# def fixString(currFunction):
#     tempString=""
#     closeBrack=0
#     closeAngular=0
#     nameFound=False
#     if currFunction[len(currFunction)-1]== ')':
#         for i in range(len(currFunction)-1,-1,-1):
#             if nameFound==True and closeAngular==0:
#                 if currFunction[i]==':' and currFunction[i-1]==':':
#                     break
#             if currFunction[i]==')':
#                 closeBrack = closeBrack+1
#             elif currFunction[i]=='(':
#                 closeBrack = closeBrack-1
#             tempString+=currFunction[i]
#             if closeBrack==0:
#                 if currFunction[i-1]=='>':
#                     closeAngular = closeAngular+1
#                 nameFound=True
#             if currFunction[i]=='<':
#                 closeAngular=closeAngular-1
#             if currFunction[i]=='>':
#                 closeAngular=closeAngular+1

            
#         tempString = tempString[::-1]
#     else:
#         tempString=currFunction

#     return tempString