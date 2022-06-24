
# Process the input options. Add options as needed.        #

Help()
{
   # Display Help
   echo
   echo "Syntax: ./newerMain.sh [-n 3 -I 0.5] [-c|N|h|t]"
   echo "options:"
   echo "n       Provide number of iterations for stack (REQUIRED)."
   echo "I       Provide the INTERVAL between iterations (in seconds) (REQUIRED)."
   echo "c       Provide the CPU Usage Threshold for threads (0-100) (OPTIONAL) - Default = 0"
   echo "N       Provide the Number of Threads to be taken (>0) (OPTIONAL) - Default = 20"
   echo "t       Provide the Threshold for minimum number of stacks of a thread to be considered (0<num<=iterations) (OPTIONAL) - Default = 0 (consider all threads)"
   echo "h       Show the help menu"
   echo
   exit
}
# Get the options
while getopts ":h:c:N:n:I:t:" option; do
   case $option in
    h) # display Help
        Help
        exit;;
    c) #Enter CPU Usage
        CPU_THRESHOLD=$OPTARG;; 
    N) #Enter Number of Threads Option
        TOP_N_THREADS=$OPTARG;;
    n) #Number of iterations
        NUMCALLS=$OPTARG;;
    I) #Intervals 
        INTERVAL=$OPTARG;;
    t) #Threshold for number of stacks of thread
        THREAD_FREQUENCY_THRESHOLD=$OPTARG;;
    \?) # Invalid option
        echo "Error: Invalid option"
        exit;;
   esac
done
shift $((OPTIND-1))

# Checking if options entered were valid, and setting default values for optional options.
# --------------Option Validation--------------
if [ -z "${CPU_THRESHOLD}" ]; then
    CPU_THRESHOLD=0
fi
if [ -z "${TOP_N_THREADS}" ]; then
    TOP_N_THREADS=20
fi
if [ -z "${INTERVAL}" ] || [ -z "${NUMCALLS}" ]; then   
    Help
fi
if [ -z "${THREAD_FREQUENCY_THRESHOLD}" ]; then
    THREAD_FREQUENCY_THRESHOLD=0
fi
if (( $(echo "$INTERVAL < 0" |bc -l) )); then
    echo "Interval should be greater than 0!"
    Help
fi
if [ $CPU_THRESHOLD -lt 0 ] || [ $CPU_THRESHOLD -gt 100 ]; then
    echo "CPU Threshold should be between 0 and 100"
    Help
fi
if [ $TOP_N_THREADS -lt 0 ]; then
    echo "Top N Threads should be greater than 0"
    Help
fi
if [ $NUMCALLS -lt 0 ]; then
    echo "Number of iterations should be greater than 0"
    Help
fi
if [ $THREAD_FREQUENCY_THRESHOLD -lt 0 ] || [ $THREAD_FREQUENCY_THRESHOLD -gt $NUMCALLS ]; then
    echo "Threshold for Iterations captured should be greater than 0 and less than or equal to NUMCALLS (number of iterations)"
    Help
fi
echo "CPU Threshold: $CPU_THRESHOLD"
echo "Top N Threads: $TOP_N_THREADS"
echo "Interval (s): $INTERVAL"
echo "Number of Iterations: $NUMCALLS"
echo "Iteration Threshold for thread: $THREAD_FREQUENCY_THRESHOLD"

# --------------Arguments--------------
currTime=$(($(date +%s%N)/1000000))
echo "Starting time: $currTime"


# --------------Global Constants--------------
OUTPUT_FILE_NAME="OutputFiles/NewerMain"
OUTPUT_MERGED_JSON="OutputFiles/merged.json"
NL=$'\n'                                    #Newline character used for some parsing purposes


# --------------Function Definitions--------------
multiThreadDetail(){
    index=$1
    local fileName="OutputFiles/json$index.json"
    local JSON_STRING=$( jq -n \
                    --arg numCalls "$NUMCALLS" \
                  '{threads:{},numCalls:$numCalls}')
    echo "$JSON_STRING" > $fileName
    while read -r detail;
    do
        # Faster to echo just once and then retrieve values using array. Seperate echos were taking too much time.
        local resultsArray=($(echo $detail | awk '{ print $1, $8, $9, $12 }'))
        local threadId=${resultsArray[0]}
        local threadState=${resultsArray[1]}
        local threadCPU=${resultsArray[2]}
        if (( $(echo "$threadCPU < $CPU_THRESHOLD" |bc -l) )); then
            break;
        fi
        # echo $threadId
        local threadName=${resultsArray[3]}
        local stack="$(sudo eu-stack -1 -p $threadId)"
         
        local currTime=$(($(date +%s%N)/1000000))
        # echo $currTime
        local JSON_TEMP=$(jq \
        --arg threadId "$threadId" \
        --arg threadName "$threadName" \
        --arg threadState "$threadState" \
        --arg threadCPU "$threadCPU" \
        --arg threadStack "$stack" \
        --arg currTime "$currTime" \
        --arg iteration "$index" \
        '.threads += {($threadId): {threadId: $threadId, iterations: [{iteration: $iteration, timeStamp: $currTime, threadId:$threadId,threadName: $threadName, threadState: $threadState, threadCPU: $threadCPU, threadStack: $threadStack, analysis:{}}] }}' $fileName)
        echo "$JSON_TEMP" > $fileName
    # Have to sort by 1st field (threadId) so that order of taking stack remains consistent in all threads. 
    done < <(top -H -bn1 | grep -m $TOP_N_THREADS "conn" | sort -n -k1) 
}

mergeJson(){
    # Function used to merge JSON objects based on their keys.
    jq -s 'def deepmerge(a;b):
    reduce b[] as $item (a;
        reduce ($item | keys_unsorted[]) as $key (.;
        $item[$key] as $val | ($val | type) as $type | .[$key] = if ($type == "object") then
            deepmerge({}; [if .[$key] == null then {} else .[$key] end, $val])
        elif ($type == "array") then
            (.[$key] + $val | unique)
        else
            $val
        end)
        );
    deepmerge({}; .)' OutputFiles/json*.json > $OUTPUT_MERGED_JSON
    sudo rm OutputFiles/json*.json
}

thresholdRecords(){
    threadIdsToRemove=()
    echo $THREAD_FREQUENCY_THRESHOLD
    while read -r line;do
        echo $line
        threadIdsToRemove+=("$line")
    done< <(jq --arg threadThreshold "$THREAD_FREQUENCY_THRESHOLD" --raw-output '.threads[] |  select((.iterations | length)<= ($threadThreshold |tonumber)) | .threadId' $OUTPUT_MERGED_JSON)
    cat $OUTPUT_MERGED_JSON > "temporary.json"
    for tid in "${threadIdsToRemove[@]}";do
        # echo "$tid"
        jq --arg threadId "$tid" 'del(.threads[$threadId])' "temporary.json" > $OUTPUT_MERGED_JSON
        cat $OUTPUT_MERGED_JSON > "temporary.json"
    done
    sudo rm "temporary.json"
}

assignQueryType(){
    # Read all thread IDs. Necessary as threadIds are required later
    threadIds=()
    while read -r line;do
        threadIds+=("$line")
    done< <(jq --raw-output '.threads[] | .threadId' $OUTPUT_MERGED_JSON)

    
    # Read stack for each threadId
    for threadId in "${threadIds[@]}";do
        for ((i=0;i<NUMCALLS;i++)); do

            # Extract current Stack
            local currIteration=$i 
            local currStack="$(jq --arg threadId $threadId --arg iteration $i '.threads[] | select(.threadId==$threadId) | .iterations[] | select(.iteration==$iteration) | .threadStack' $OUTPUT_MERGED_JSON)"
            currStack="$(echo -e "$currStack")"

            local currState="$(jq --arg threadId $threadId --arg iteration $i '.threads[] | select(.threadId==$threadId) | .iterations[] | select(.iteration==$iteration) | .threadState' $OUTPUT_MERGED_JSON)"
            
            # Analysis field is already created in the iteration adding step
            # clear map for fresh iteration
            unset analysisMap
            declare -A analysisMap
            # set default as running, if recvmsg found, then will overwrite
            if [[ $currState == "R" ]];then
                analysisMap["queryState"]="Running"
            fi

            # Start Analysis by filling analysis map with key = property, and value = propertyVaue
            while read -r individualLine; do
                
                # Major analysis is done at this point, dont need to traverse ahead.
                if [[ $individualLine == *"ExecCommandDatabase::_commandExec"* ]]; then
                        break
                fi
                if [[ $individualLine == *"recvmsg"* ]]; then
                    # echo "Idle Found"
                    analysisMap["queryState"]="Idle"
                    break
                fi
                if [[ $individualLine == *"__poll"* ]]; then
                    # echo "Idle Found"
                    analysisMap["queryState"]="Idle"
                    break
                fi
                # Type of scan encountered
                if [[ $individualLine == *"CollectionScan"* ]]; then
                    analysisMap["includesCollectionScan"]="True"
                fi
                if [[ $individualLine == *"CountScan"* ]]; then
                    analysisMap["includesCountScan"]="True"
                fi
                # Which stage is included in call stack (usually in top of stack)
                if [[ $individualLine == *"CountStage"* ]]; then
                    analysisMap["includesCountingStage"]="True"
                fi
                if [[ $individualLine == *"SortStage"* ]]; then
                    analysisMap["includesSortingStage"]="True"
                fi
                if [[ $individualLine == *"UpdateStage"* ]]; then
                    analysisMap["includesUpdationStage"]="True"
                fi
                if [[ $individualLine == *"ProjectionStage"* ]]; then
                    analysisMap["includesProjectionStage"]="True"
                fi

                # Query Type by Invocation Function in call stack
                if [[ $individualLine == *"FindCmd"* ]]; then
                    analysisMap["queryType"]="Find"
                fi
                if [[ $individualLine == *"CmdCount"* ]]; then
                    analysisMap["queryType"]="Count"
                fi
                if [[ $individualLine == *"CmdFindAndModify"* ]]; then
                    analysisMap["queryType"]="FindAndModify"
                fi
                if [[ $individualLine == *"PipelineCommand"* ]]; then
                    analysisMap["queryType"]="Pipeline"
                fi
                if [[ $individualLine == *"runAggregate"* ]]; then
                    analysisMap["queryType"]="Aggregation"
                fi
                if [[ $individualLine == *"CmdInsert"* ]]; then
                    analysisMap["queryType"]="Insert"
                fi

                # # other useful information
                # if [[ $individualLine == *"RunCommandAndWaitForWriteConcern"* ]]; then
                #     analysisMap["runningParallelWithInsert"]="True"
                # fi

                # Highest level in stack, to capture these, interval has to be very precise 

                if [[ $individualLine == *"ExprMatchExpression"* ]]; then
                    analysisMap["includesExpressionMatching"]="True"
                fi
                if [[ $individualLine == *"PathMatchExpression"* ]]; then
                    analysisMap["currentlyMatchingDocuments"]="Matching Path for expression (still deciding path)"
                fi
                if [[ $individualLine == *"InMatchExpression"* ]]; then
                    analysisMap["currentlyMatchingDocuments"]="Matching 'in' expression"
                fi
                if [[ $individualLine == *"RegexMatchExpression"* ]]; then
                    analysisMap["currentlyMatchingDocuments"]="Matching 'Regex' expression"
                fi
                if [[ $individualLine == *"ComparisonMatchExpression"* ]]; then
                    analysisMap["currentlyComparingValues"]="True"
                fi
                if [[ $individualLine == *"getNextDocument"* ]]; then
                    analysisMap["fetchingNextDocument"]="True"
                fi
                if [[ $individualLine == *"compareElementStringValues"* ]]; then
                    analysisMap["currentlyComparingStringValues"]="True"
                fi
            done <<< "$currStack"

            # Traverse analysisMap and add fields in the analysis object. JQ FORMAT IS IMPORTANT (basically |= to update and we wanted the entire file back, hence had to update everything since start. Also after |=, next field has to be enclosed in (). While adding new field, Key has to be enclosed in ())
            for key in "${!analysisMap[@]}"; do
                tmp=$(mktemp)
                jq --arg threadId $threadId --argjson iteration $currIteration --arg key "${key}" --arg value "${analysisMap[$key]}" '.threads |= (.[$threadId] |= (.iterations[$iteration] |= (.analysis += {($key):$value})))' $OUTPUT_MERGED_JSON > "$tmp" && mv "$tmp" $OUTPUT_MERGED_JSON
                # sudo rm "$tmp"
                          
            done 
        done
      
    done
}

getFunctionCounts(){

    while read -r line;do
        currStack=$(echo -e "$line")
        # echo "$currStack"
        while read -r individualLine; do
            # For lines #TID: where no output will be produced in this while loop
            if [[ "$individualLine" = "" ]];then

                continue
            fi
            if [[ ${functionCallCounts[$individualLine]} ]]; then
                
                local count=${functionCallCounts[$individualLine]}
                let count=$count+1
                functionCallCounts[$individualLine]=$count
            else
                functionCallCounts[$individualLine]=1
            fi
        done< <(echo "$currStack" | awk '{$1=$2=""; print $0}')

    done< <(jq --raw-output '.threads[] | .iterations[] | .threadStack' OutputFiles/merged.json)
    
    
    currTime=$(($(date +%s%N)/1000000))
    echo "Sorting Started": $currTime <&2
    # Basically first echo the COUNT first, and then the FUNCTION, so that if FUNCTION has spaces, they occur later
    # And we can sort by first field
    # -r = sorting in reverse
    # -n = numeric sorting
    # By default takes first field, else have to specify as -k2 for 2nd etc.
    for function in "${!functionCallCounts[@]}"; do 
        echo "${functionCallCounts["$function"]} ${function}"
    done | sort -rn | while read number function; do 
        echo "${function} - ${number}" >> $OUTPUT_FILE_NAME
        echo "" >> $OUTPUT_FILE_NAME
    done

}

# --------------Program Flow--------------
# Create Output File
echo > $OUTPUT_FILE_NAME

# Going in!!
# Get PID of mongod
pid=$(pidof mongod)
echo "Process ID of mongod is: $pid" >> $OUTPUT_FILE_NAME
echo >> $OUTPUT_FILE_NAME

for ((i=0;i<NUMCALLS;i++)); do
    multiThreadDetail $i &
    sleep $INTERVAL
    echo "starting next iteration of eu-stack at timestamp: $(($(date +%s%N)/1000000))"
done

# sequentialThreadDetail

wait 

echo "Merging"
mergeJson
echo "Merged"


currTime=$(($(date +%s%N)/1000000))
echo "Thresholding starting: $currTime"
thresholdRecords

# currTime=$(($(date +%s%N)/1000000))
# echo "Function Call Starting Time: $currTime"
# declare -A functionCallCounts
# getFunctionCounts

currTime=$(($(date +%s%N)/1000000))
echo "Assign Query Starting Time: $currTime"
assignQueryType



currTime=$(($(date +%s%N)/1000000))
echo "Creating Graphs at time :$currTime"
python graphs.py

currTime=$(($(date +%s%N)/1000000))
echo "Ending time: $currTime"





# OTHER TESTING CODE
# sequentialThreadDetail(){
#     local fileName="jsonSequential$index.json"
#     local JSON_STRING=$( jq -n \
#                   '{threads:{}}')
#     echo "$JSON_STRING" > $fileName
#     while read -r detail;
#     do
#         for ((i=0;i<NUMCALLS;i++)); do
#             # echo "$detail"

#             local resultsArray=($(echo $detail | awk '{ print $1, $8, $9, $12 }'))
#             local threadId=${resultsArray[0]}
#             local threadState=${resultsArray[1]}
#             local threadCPU=${resultsArray[2]}
#             if (( $(echo "$threadCPU < $CPU_THRESHOLD" |bc -l) )); then
#                 break;
#             fi
#             # echo $threadId
#             local threadName=${resultsArray[3]}
#             local stack="$(sudo eu-stack -1 -p $threadId)"
            
#             local currTime=$(($(date +%s%N)/1000000))
#             # echo $currTime
#             local JSON_TEMP=$(jq \
#             --arg threadId "$threadId:$i" \
#             --arg threadName "$threadName" \
#             --arg threadState "$threadState" \
#             --arg threadCPU "$threadCPU" \
#             --arg threadStack "$stack" \
#             --arg currTime "$currTime" \
#             --arg iteration "$i" \
#             '.threads += {($threadId): {threadId: $threadId, iterations: [{iteration: $iteration, timeStamp: $currTime, threadName: $threadName, threadState: $threadState, threadCPU: $threadCPU, threadStack: $threadStack}] }}' $fileName)
#             echo "$JSON_TEMP" > $fileName
            
#             # Handling Error in time
#             local currTime2=$(($(date +%s%N)/1000000))
#             local diff=$(bc <<< "scale=2; ($currTime2-$currTime)/1000")
#             local newInterval=$(bc <<< "scale=2; ($INTERVAL-$diff)")
#             if (( $(echo "$newInterval < 0" |bc -l) )); then
#                 newInterval=0
#             fi
#         #Error handling complete
            
#             sleep $newInterval
#         done
        
#     done < <(top -H -bn1 | grep -m $TOP_N_THREADS "conn") 
# }
