
import json

def performAnalysis():
    mergedFile = open("OutputFiles/merged.json", "r")
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
            
            currentOpsFile = open("OutputFiles/currentOp"+currIteration+".json", "r")
            currentOpObject = json.load(currentOpsFile)
            currentOpsFile.close()
            
            if len(currentOpObject)!=0:
                myCurrentOpObject={}
                for item in currentOpObject["inprog"]:
                    if item["desc"] == currName:
                        myCurrentOpObject["command"] = item
                        break
                jsonObject["threads"][threadId]["iterations"][i]["currentOp"]=myCurrentOpObject

    a_file = open("OutputFiles/merged.json", "w")
    json.dump(jsonObject, a_file)
    a_file.close()

performAnalysis()