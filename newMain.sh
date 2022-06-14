
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

takeStackTrace(){
    for ((i=1;i<=NUMCALLS;i++)); 
    do
        local currTime=$(($(date +%s%N)/1000000))
        timeStamps+=($currTime)
        takeStakeTraceUtil $currTime &              # & for parallel processing, synchronization done later in code
        sleep $INTERVAL
    done
}   


getThreadIds(){

    while read -r detail;
    do
        local threadId=$(echo $detail | awk '{print $1}')
        threadIds+=$threadId

        local threadState="$(echo $detail | awk '{print $8}')"
        threadStates[$threadId]="$threadState"

        local threadCPU="$(echo $detail | awk '{print $9}')"
        threadCPUs[$threadId]="$threadCPU"

        local threadName="$(echo $detail | awk '{print $12}')"
        threadNames[$threadId]="$threadName"

    done < <(top -H -bn1 | grep "conn")
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
# # Multithreaded process, will keep taking stack trace in background while we collect thread information. Synchronized Later
timeStamps=()
declare -A stackTraces
takeStackTrace

echo "hehehe1"


threadIds=()
declare -A threadStates
declare -A threadCPUs
declare -A threadNames
getThreadIds

echo "hehehe2"








# Synchronization point for stack traces, will store stacktrace in map and remove the temporary files.
wait                
for timeStamp in ${timeStamps[@]};
do
    fileName="FullStack_$timeStamp"
    stackTraces[$timeStamp]="$(<${fileName})"
    rm "FullStack_$timeStamp"
done

# Just storing output for reference
for timeStamp in ${timeStamps[@]};
do
    echo "" >> $OUTPUT_FILE_NAME
    echo "" >> $OUTPUT_FILE_NAME
    echo "$timeStamp" >> $OUTPUT_FILE_NAME
    echo "${stackTraces[$timeStamp]}" >> $OUTPUT_FILE_NAME
done

echo "" >> $OUTPUT_FILE_NAME
echo "" >> $OUTPUT_FILE_NAME

echo "hehe3"
echo "${threadIds[@]}"
for threadId in ${threadIds[@]};
do
    echo "$threadId"
    echo $threadId >> $OUTPUT_FILE_NAME
    echo ${threadNames[$threadId]} >> $OUTPUT_FILE_NAME
    echo ${threadStates[$threadId]} >> $OUTPUT_FILE_NAME
    echo "${threadCPUs[$threadId]}" >> $OUTPUT_FILE_NAME
done

echo "hehe4"