
#Check Argument Errors
if (( $# < 2 ))
then
    printf "%b" "Error. Not enough arguments.\n" >&2
    printf "%b" "usage: stackShellScript.sh NUMCALLS INTERVAL(in seconds)\n" >&2
    exit 1
elif (( $# > 2 ))
then
    printf "%b" "Error. Too many arguments.\n" >&2
    printf "%b" "usage: stackShellScript.sh NUMCALLS INTERVAL(in seconds)\n" >&2
    exit 2
fi

# --------------Arguments--------------
NUMCALLS=$1
INTERVAL=$2

# --------------Global Constants--------------
OUTPUT_FILE_NAME="OutputFiles/NewMain"
CPU_THRESHOLD=0
NL=$'\n'                #Newline character used for some parsing purposes

# --------------Function Definitions--------------

# Takes stack trace using the euStackUtil.sh script. This is done so that stacks can be taken at exact INTERVAL interval,
# and are processed parallely
# Also stores CPU Usage of each thread.

takeStakeTraceUtil(){
    # $1 = currTime
    echo $"Taking stack dump at timestamp $1"
    # timeStamps+=(${1})
    stackDump="$(sudo eu-stack -p $pid --source))"
    local fileName="FullStack_$1"
    echo "$stackDump" > $fileName         
}

# Driver function to run the stack trace threads, and also get details of thread at that timestamp.
# Time taken to execute the lines between timestamp and sleep execution, is the minimum precision by which we can take intervals
# For ex. if it takes 0.2s to execute the lines, then we can adjust the difference in sleep interval.
# But this error adjust can only work till that extent ki the total time taken to execute those lines is not GREATER than the entire interval time
# For ex. if it takes 1s to execute the lines, and interval is 0.5, then there is nothing that can be done, and interval would be taken as 1s itself.
# This can be fixed if we multithread the thread details function too, but that would mean more temporary files, which we dont want.

# # Multithreaded process, will keep taking stack trace in background while we collect thread information. Synchronized Later

captureDetails(){
    for ((i=1;i<=NUMCALLS;i++)); do 
        echo "$i $NUMCALLS"
        local currTime=$(($(date +%s%N)/1000000))
        timeStamps+=($currTime)
        takeStakeTraceUtil $currTime &              # & for parallel processing, synchronization done later in code
        getThreadDetails                                # Get thread details

        if (( $i == $NUMCALLS ));then
            break
        fi
        #Handling Error in time
        local currTime2=$(($(date +%s%N)/1000000))
        local diff=$(bc <<< "scale=2; ($currTime2-$currTime)/1000")
        local newInterval=$(bc <<< "scale=2; ($INTERVAL-$diff)")
        if (( $(echo "$newInterval < 0" |bc -l) )); then
            newInterval=0
        fi
        #Error handling complete

        sleep $newInterval                            
    done

    # Refine the thread IDs. Remove those thread IDs which were not present in ALL the iterations. 
    # This is possible incase a thread finishes its execution in between, or starts in between
    # Rare scenario, but incase it happens, it can make the results unexpected due to non uniformity
    # Also, removing them won't be much of an issue as, if they are not present in high CPU category consistently,
    # it is most probable that they are not problematic. 
    local threadLength=${#threadIds[@]}
    # echo $threadLength
    for ((j=0;j<${#threadIds[@]};j++));
    do
        local threadId=${threadIds[j]}
        local threadStateString=${threadStates[$threadId]}
        local tempStateArray=($threadStateString)
        local stateArrayLength=${#tempStateArray[@]}
        # echo "$threadId: $stateArrayLength"
        if (( stateArrayLength < NUMCALLS ));then
            unset threadIds[j]
        fi
    done
}   


# CURRENTLY ASSUMING THAT EACH THREAD EXISTS FOR ENTIRE DURATION
# Function to get all thread parameters from "top -H" command. Takes threads which have high CPU usage and follow the pattern "conn" (for mongo clients)
getThreadDetails(){

    while read -r detail;
    do
        # This checks if the Current thread being processed is exerting higher CPU usage than the threshhold
        # Incase its lower than it, we can break as the records are in descending order.
        local checkCPUforThreshold="$(echo $detail | awk '{print $9}')"
        if (( $(echo "$checkCPUforThreshold < $CPU_THRESHOLD" |bc -l) )); then
            break;
        fi
        # Check if threadID already there, no need to add again
        local threadId=$(echo $detail | awk '{print $1}')
        if ! [[ -v "threadPresentMap[$threadId]" ]] ; then
            threadIds+=($threadId)
            threadPresentMap[$threadId]="Present" 
        fi

        # If state array for a threadID already exists, append, else create
        local threadState="$(echo $detail | awk '{print $8}')"
        if [[ -v "threadStates[$threadId]" ]] ; then
            local temp=${threadStates[$threadId]}
            threadStates[$threadId]="$temp $threadState"
        else
            threadStates[$threadId]="$threadState"
        fi

        # If CPU array for a threadID already exists, append, else create
        local threadCPU="$(echo $detail | awk '{print $9}')"
        if [[ -v "threadCPUs[$threadId]" ]] ; then
            local temp=${threadCPUs[$threadId]}
            threadCPUs[$threadId]="$temp $threadCPU"
        else
            threadCPUs[$threadId]="$threadCPU"
        fi

        # Can overwrite name in case of clashing thread ID (assuming same thread ID exists over entire duration)
        local threadName="$(echo $detail | awk '{print $12}')"
        if ! [[ $threadName == "" ]];then
            threadNames[$threadId]="$threadName"
        fi
    done < <(top -H -bn1 | grep "conn")
    #  awk '{ if ($9 >= 0 ) print $0}' |

    

}


#Utility function for getStackPerThread() function. Takes ThreadID as parameter and gets all stacks from every timestamp of full stacks
getStackPerThreadUtil(){

    local tempStackHold=()
    local threadId=$1
    for timeStamp in ${timeStamps[@]};
    do
        local tempFull="${fullStackTraces[$timeStamp]}"
        local currStack=$tempFull  
        local startPattern="$threadId:$NL"   #add newline character too, so that starts directly from stack
        local stackSubstring="${currStack#*${startPattern}}"   #removes everything before startingPattern from stack
        local endPattern="${NL}TID"
        stackSubstring="${stackSubstring%%${endPattern}*}"   #removes everything after endString from stack
        # Handling special case for stack of thread which is the last thread (ends an extra ")" in the end of stack)
        if [ "${stackSubstring: -1}" == ")" ]; then
            stackSubstring="${stackSubstring::-1}"
        fi
        # IMPORTANT -> Seperator used so that can access different stacks of same thread by splitting over seperator.
        tempStackHold+="$stackSubstring ${NL} SEPERATOR${NL}"                
    done

    echo "${tempStackHold[@]}"
  
}

# Extract stack for each thread from full stacks
getStackPerThread(){
    for threadId in ${threadIds[@]};
    do
        echo $threadId
        stackTraces[$threadId]=$(getStackPerThreadUtil "$threadId")
    done
}

# Utility function used to create Individual reports
getStackByTIDandTimestamp(){
    local threadId=$1
    local timeStampParameter=$2
    local combinationOfStacks="${stackTraces[$threadId]}" 

    for timeStamp in ${timeStamps[@]};do
        local startPattern=" $NL SEPERATOR$NL"   #add newline character too, so that starts directly from stack
        local endPattern=" $NL SEPERATOR"
        local stackSubstring="${combinationOfStacks%%${endPattern}*}"   #removes everything after endString from stack INCLUDING end pattern
        local combinationOfStacks="${combinationOfStacks#*${startPattern}}"   #removes everything before startingPattern from stack INCLUDING start pattern
        if [[ $timeStamp == $timeStampParameter ]];then
            echo "$stackSubstring"
            break
        fi
    done
}

# Takes index (integer) as parameter to reference to timestamp. (current issue is that all arrays MAY not have index present due to thread not being present)
createIndividualStackJSON(){
    local index=$1
    local currTime=${timeStamps[$index]}
    local currStack="${fullStackTraces[$currTime]}"
    local JSON_STRING=$( jq -n \
                  --arg currTime "$currTime" \
                  --arg fullStack "$currStack" \
                  --arg threadId "$threadId" \
                  '{timeStamp: $currTime, fullStack: $fullStack, threads:[]}')          # Create empty threads arary which will be filled later
    local fileName="OutputFiles/IndividualOutput_$currTime.json"            
    echo "$JSON_STRING" > "$fileName"
    
    # echo "$currStack"
    for threadId in ${threadIds[@]};do
        local threadName=${threadNames[$threadId]}

        # Seperating State of current index (space seperated string -> array -> index)
        local threadStateString=${threadStates[$threadId]}
        local tempStateArray=($threadStateString)
        local threadState=${tempStateArray[$index]}

        # Seperating State of current index (space seperated string -> array -> index)
        local threadCPUString=${threadCPUs[$threadId]}
        local tempCPUArray=($threadCPUString)
        local threadCPU=${tempCPUArray[$index]}

        local stack=$(getStackByTIDandTimestamp $threadId $currTime)
        # Appending json object into already existing array.
        local JSON_TEMP=$(jq \
        --arg threadId "$threadId" \
        --arg threadName "$threadName" \
        --arg threadState "$threadState" \
        --arg threadCPU "$threadCPU" \
        --arg threadStack "$stack" \
        '.threads += [{threadId: $threadId, threadName: $threadName, threadState: $threadState, threadCPU: $threadCPU, threadStack: $threadStack}]' "$fileName")
        echo "$JSON_TEMP" > "$fileName"
    done

}



# --------------Program Flow--------------

# Create Output File
echo > $OUTPUT_FILE_NAME

# Get PID of mongod
pid=$(pidof mongod)
echo "Process ID of mongod is: $pid" >> $OUTPUT_FILE_NAME
echo >> $OUTPUT_FILE_NAME

# # Get Entire Stack Trace according to input arguments
#         # timeStamps is an array of timeStamps. Size = NUMCALLS
#         # stackTraces is an array where we can retrieve stack using the different timestaps
timeStamps=()
threadIds=()    
declare -A threadPresentMap         # Utility map which tells if a thread was present or not (by threadId)
declare -A threadStates             # Stores states of thread in all iterations (Space separated)
declare -A threadCPUs               # Stores CPU usage of thread in all iterations (Space separated)
declare -A threadNames              # Stores name of thread by threadID (assuming name of thread stays same over iterations)
declare -A fullStackTraces          # Stores full stack traces of server, accessed by timestamp
declare -A totalCPUs            

captureDetails


# Synchronization point for stack traces, will store stacktrace in map and remove the temporary files.
wait                
for timeStamp in ${timeStamps[@]};
do
    fileName="FullStack_$timeStamp"
    fullStackTraces[$timeStamp]="$(<${fileName})"
    rm "FullStack_$timeStamp"
done


declare -A stackTraces
echo "Starting Stack per Thread"
getStackPerThread


# Create individual JSONs
for ((i=0;i<NUMCALLS;i++)); do
    createIndividualStackJSON $i
done






# Just storing output for reference
for timeStamp in ${timeStamps[@]};
do
    echo "" >> $OUTPUT_FILE_NAME
    echo "" >> $OUTPUT_FILE_NAME
    echo "$timeStamp" >> $OUTPUT_FILE_NAME
    echo "${fullStackTraces[$timeStamp]}" >> $OUTPUT_FILE_NAME
done

echo "" >> $OUTPUT_FILE_NAME
echo "" >> $OUTPUT_FILE_NAME

for threadId in ${threadIds[@]};
do
    echo $threadId >> $OUTPUT_FILE_NAME
    echo ${threadNames[$threadId]} >> $OUTPUT_FILE_NAME
    echo ${threadStates[$threadId]} >> $OUTPUT_FILE_NAME
    echo ${threadCPUs[$threadId]} >> $OUTPUT_FILE_NAME
    echo "Printing stacks of $threadId" >> $OUTPUT_FILE_NAME
    echo "" >> $OUTPUT_FILE_NAME

    # TO SEPERATE THE STACKS  ( stored as seperator ) FOR LOCAL USE
    combinationOfStacks="${stackTraces[$threadId]}" 

    for timeStamp in ${timeStamps[@]};do
        startPattern=" $NL SEPERATOR$NL"   #add newline character too, so that starts directly from stack
        endPattern=" $NL SEPERATOR"
        stackSubstring="${combinationOfStacks%%${endPattern}*}"   #removes everything after endString from stack INCLUDING end pattern
        combinationOfStacks="${combinationOfStacks#*${startPattern}}"   #removes everything before startingPattern from stack INCLUDING start pattern
        echo "$stackSubstring" >> $OUTPUT_FILE_NAME
        echo "" >> $OUTPUT_FILE_NAME
    done
done




# UTILITY FUNCTIONS
# To seperate stacks by the seperator use the following function
# for threadId in ${threadIds[@]};
# do
#     combinationOfStacks="${stackTraces[$threadId]}" 
#     for timeStamp in ${timeStamps[@]};do
#         startPattern=" $NL SEPERATOR$NL"   #add newline character too, so that starts directly from stack
#         endPattern=" $NL SEPERATOR"
#         stackSubstring="${combinationOfStacks%%${endPattern}*}"   #removes everything after endString from stack INCLUDING end pattern
#         combinationOfStacks="${combinationOfStacks#*${startPattern}}"   #removes everything before startingPattern from stack INCLUDING start pattern
#     done
# done

