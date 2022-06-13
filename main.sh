
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
OUTPUT_FILE_NAME="OutputFiles/Main"

# --------------Function Definitions--------------

# Takes stack trace using the euStackUtil.sh script. This is done so that stacks can be taken at exact INTERVAL interval,
# and are processed parallely
# Also stores CPU Usage of each thread.
takeStackTrace(){
  for ((i=1;i<=NUMCALLS;i++)); do
    local currTime=$(($(date +%s%N)/1000000))
    timeStamps+=($currTime)
    ./euStackUtil.sh $currTime $pid &         # & for parallel processing.
    sleep $INTERVAL
  done
  wait
}

# Begin multithreaded analysis of individual stack traces
beginIndividualAnalysis(){
  for timeStamp in ${timeStamps[@]};
  do
    ./individualAnalysis.sh $timeStamp $pid &         # & for parallel processing.
  done
}

# --------------Program Flow--------------

# Create File
echo > $OUTPUT_FILE_NAME

# Get PID of mongod
pid=$(pidof mongod)
echo "Process ID of mongod is: $pid" >> $OUTPUT_FILE_NAME
echo >> $OUTPUT_FILE_NAME

# # Get Entire Stack Trace according to input arguments
#         # timeStamps is an array of timeStamps. Size = NUMCALLS
# After this function call, individual thread stacks are stored in file with filenames threadId_timeStamp. Can be retrieved from there
timeStamps=()
takeStackTrace



echo "" >> $OUTPUT_FILE_NAME       
echo "-----resynchronization-----" >> $OUTPUT_FILE_NAME
echo "" >> $OUTPUT_FILE_NAME

echo "Joint Starting"
./jointAnalysis.sh $pid "${timeStamps[@]}" &
beginIndividualAnalysis 


wait
