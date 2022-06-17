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
currTime=$(($(date +%s%N)/1000000))
echo "Starting time: $currTime"
# --------------Global Constants--------------
OUTPUT_FILE_NAME="OutputFiles/NewerMain"
CPU_THRESHOLD=0
TOP_N_THREADS=20
NL=$'\n'                #Newline character used for some parsing purposes

# --------------Function Definitions--------------
multiThreadDetail(){
    index=$1
    local fileName="json$index.json"
    local JSON_STRING=$( jq -n \
                  '{threads:{}}')
    echo "$JSON_STRING" > $fileName
    while read -r detail;
    do
        # echo "$detail"
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
        '.threads += {($threadId): {threadId: $threadId, iterations: [{iteration: $iteration, timeStamp: $currTime, threadName: $threadName, threadState: $threadState, threadCPU: $threadCPU, threadStack: $threadStack}] }}' $fileName)
        echo "$JSON_TEMP" > $fileName
    # Have to sort by 1st field (threadId) so that order of taking stack remains consistent in all threads. 
    done < <(top -H -bn1 | grep -m $TOP_N_THREADS "conn" | sort -n -k1) 
}
mergeJson(){

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
    deepmerge({}; .)' json*.json > "merged.json"

}
# --------------Program Flow--------------
# Create Output File
echo > $OUTPUT_FILE_NAME

# Get PID of mongod
pid=$(pidof mongod)
echo "Process ID of mongod is: $pid" >> $OUTPUT_FILE_NAME
echo >> $OUTPUT_FILE_NAME

for ((i=0;i<NUMCALLS;i++)); do
    multiThreadDetail $i &
    sleep $INTERVAL
done

wait 

echo "Merging"
mergeJson
echo "Merged"

currTime=$(($(date +%s%N)/1000000))
echo "Ending time: $currTime"
