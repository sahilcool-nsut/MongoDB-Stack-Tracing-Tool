
# --------------Arguments--------------
timeStamp=$1
pid=$2

# --------------Globals--------------
OUTPUT_FILE_NAME="OutputFiles/IndividualAnalysis_$timeStamp"


# --------------Function Definitions--------------

# Get Thread names (of only those threads which were present in stack trace) using ps command. 
# Had to hardcode "mongod" case due to same PID and ThreadID in its case
getThreadNames(){       
         
    processList=$(ps -T -p $pid) 
    for threadId in ${threadIds[@]};
    do
        # echo $threadId $pid
        if [ "$threadId" == "$pid" ]; then
            threadNames[$threadId]="mongod"
            continue
        fi


        while read -r line ; do
            local threadName="$(echo $line | awk '{print $5}')"
            threadNames[$threadId]="$threadName"      # %5 is for taking 5th number (threadName)
        done < <(echo "$processList" | grep " $threadId .*")     
    done

}

# Extract Thread IDs from the stack trace
getThreadIds(){
    while read -r line ; do
    # echo "Processing $line"
    local currId=$(echo $line | grep -oP '(?<=D).*?(?=:)')
    # echo $currId
    threadIds+=$currId
    done < <(echo "$fullStackTrace" | grep "TID .*:")

}

# Get States of each thread, and also the total number of threads in each state
getThreadStates(){


    for threadId in ${threadIds[@]};
    do
        state=$(sudo cat /proc/$pid/task/$threadId/status | grep "State")
        threadStates[$threadId]="$state"
        # echo "$state"
        if [[ ${stateCounts[$state]} ]]; then
            local count=${stateCounts[$state]}
            let count=$count+1
            stateCounts[$state]=$count
        else
            stateCounts[$state]=1
        fi
    done

}

extractStackOfThread(){
    for threadId in ${threadIds[@]};
    do
        local currStack=$fullStackTrace
        local NL=$'\n'    
        local startPattern="$threadId:$NL"   #add newline character too, so that starts directly from stack
        local stackSubstring="${currStack#*${startPattern}}"   #removes everything before startingPattern from stack
        local endPattern="${NL}TID"
        stackSubstring="${stackSubstring%%${endPattern}*}"   #removes everything after endString from stack
        
        # Handling special case for stack of thread which is the last thread (ends an extra ")" in the end of stack)
        if [ "${stackSubstring: -1}" == ")" ]; then
            stackSubstring="${stackSubstring::-1}"
        fi
        threadStacks[$threadId]="$stackSubstring"
    done
  
}

getIndividualStackCounts(){

    for threadId in ${threadIds[@]};
    do
        stack="${threadStacks[$threadId]}"
        # echo "$stack"
        if [[ ${stackCounts[$stack]} ]]; then
            local count=${stackCounts[$stack]}
            let count=$count+1
            stackCounts[$stack]=$count
        else
            stackCounts[$stack]=1
        fi
    done
}

# --------------Program Workflow--------------

echo "Starting Individual with timeStamp ${timeStamp}"
fileName="stackDumps/FullStack_${timeStamp}"
fullStackTrace="$(<${fileName})"

echo "$fullStackTrace" > $OUTPUT_FILE_NAME

# Get Thread IDs from stack
threadIds=()
getThreadIds

# Get Thread Names
declare -A threadNames
getThreadNames
 
declare -A threadStates
declare -A stateCounts
# Get Thread States
getThreadStates

declare -A threadStacks
declare -A stackCounts
extractStackOfThread 
# echo "${threadStacks[@]}"

getIndividualStackCounts


# --------------PRINT OUTPUT--------------
# printf "\n\n\n\n"
echo "" >> $OUTPUT_FILE_NAME
echo "Thread Details" >> $OUTPUT_FILE_NAME
for threadId in ${threadIds[@]};
do
    name=${threadNames[$threadId]}
    echo -e "$threadId: ${threadNames[$threadId]}\t\t\t ${threadStates[$threadId]} " >> $OUTPUT_FILE_NAME
done   
echo "" >> $OUTPUT_FILE_NAME
echo "State Counts: " >> $OUTPUT_FILE_NAME
for state in "${!stateCounts[@]}"; do
  echo "$state -> Count: ${stateCounts[$state]} " >> $OUTPUT_FILE_NAME
done

echo "" >> $OUTPUT_FILE_NAME
echo "" >> $OUTPUT_FILE_NAME
echo "Stack Counts: " >> $OUTPUT_FILE_NAME
for stack in "${!stackCounts[@]}"; do
  echo -e "Count: ${stackCounts[$stack]}\n $stack\n\n" >> $OUTPUT_FILE_NAME
done

echo "Individual Analysis for timestamp $timeStamp done"