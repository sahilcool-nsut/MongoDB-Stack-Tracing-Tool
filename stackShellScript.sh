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
IDLE_STACK_FORMAT="$(<"IDLE_STACK_FORMAT")"
OUTPUT_FILE_NAME="JointAnalysis"
# --------------Global Variables used--------------
# threadIds -> stores useful threads at any time
# threadNames -> map using key as threadId and value as Name (context) of client connection
# threadRemotes -> map using key as threadId and value as IP address of client
# timeStamps -> contains timestamps at which stack was taken, hence used for retrieving the stacks from saved files
# pid -> pid of mongod process


# --------------Function Definitions--------------

# Takes stack trace using the euStackUtil.sh script. This is done so that stacks can be taken at exact INTERVAL interval,
# and are processed parallely
# Also stores CPU Usage of each thread.
takeStackTrace(){
  for ((i=1;i<=NUMCALLS;i++)); do
    local currTime=$(($(date +%s%N)/1000000))
    timeStamps+=($currTime)
    ./euStackUtil.sh $currTime $pid "${threadIds[@]}" &         # & for parallel processing.
    sleep $INTERVAL
  done
  wait
}

# ----

# Abhi uses global variable threadIds and threadNames, have to convert into parameters for multithreading
getConnectionThreads(){                  
  readarray -t conn_array < <(ps -T -p $pid | grep "conn")      # grep is for pattern matching
                                                                # output is like:    4099    4453 ?        00:00:11 conn1
  for val in "${conn_array[@]}";
  do
    threadId=$(echo $val | awk '{print $2}')                    # $2 is for taking 2nd number (threadId)
    threadIds+=($threadId)
    threadName="$(echo $val | awk '{print $5}')"
    threadNames[$threadId]="${threadName}"      # %5 is for taking 5th number (threadName)
    threadRemote="$(sudo jq --arg threadName "$threadName" '. | select(.ctx==$threadName and .c=="NETWORK" and .msg=="client metadata" and .attr.remote)' /var/log/mongodb/mongod.log | grep 'remote' | tail -n 1 | awk '{print $2}' | grep -oP '(?<=").*?(?=")')" 
    threadRemotes[$threadId]=$threadRemote
  done
}

# ----

# Compares the various stacks of a given thread (parameter) with the IDLE_STACK_FORMAT.
# IDLE_STACK_FORMAT is stripped off the hexadecimal addresses, and hence same has been applied for the stack of each thread before comparing.
checkIdleOrNot(){
  # $1 = val (threadID)
  local count=0
  for timeStamp in ${timeStamps[@]};
  do
    local fileName="${1}_$timeStamp"
    stack="$(echo "$(sed 's| 0x................\b\b||g' "$fileName")")"         # Currently matched by assuming 16 digits (16hexadecimal address) and two spaces (\b = breaks)
    if [ "$stack" == "$IDLE_STACK_FORMAT" ]; then
      let count=count+1
    fi
  done
  echo "Thread ID = ${val} : count of idle frame = ${count}" >> $OUTPUT_FILE_NAME                # >&2 is used to output on stderr, else, yaha se echo kiya to returns from function
  if [ $count -eq $NUMCALLS ]; then
      echo 1                                                      # echo returns from function
  else
    echo 0
  fi
}

# ----

# Checks individual thread stacks with each other, to check if a certain thread has the same stack for the entire duration.
checkHungOrNot(){
  # $1 = val (threadID)
  local count=0
  local tempFile="${val}_${timeStamps[1]}"
  local firstStack="$(<${tempFile})"                              # extract first stack, to compare with rest of all
  for timeStamp in ${timeStamps[@]};
  do
    local fileName="${1}_$timeStamp"
    local stack="$(<${fileName})"      
    if [ "$stack" == "$firstStack" ]; then
      let count=count+1
    fi
  done
  echo "Thread ID = ${val} : count of equal frames = ${count}" >> $OUTPUT_FILE_NAME                # >&2 is used to output on stderr, else, yaha se echo kiya to returns from function
  if [ $count -eq $NUMCALLS ]; then
      echo 1                                                     
  else
    echo 0
  fi
}

beginIndividualAnalysis(){
  for timeStamp in ${timeStamps[@]};
  do
    ./individualAnalysis.sh $timeStamp $pid &         # & for parallel processing.
  done
}

# --------------Program Workflow Start--------------

# Create File
echo > $OUTPUT_FILE_NAME

# Get PID of mongod
pid=$(pidof mongod)
echo "Process ID of mongod is: $pid" >> $OUTPUT_FILE_NAME
echo >> $OUTPUT_FILE_NAME

# Get Connnection Thread details
threadIds=()
declare -A threadNames
declare -A threadRemotes
getConnectionThreads

echo "Connection Clients found are: " >> $OUTPUT_FILE_NAME
echo ${threadIds[@]} >> $OUTPUT_FILE_NAME
echo ${threadNames[@]} >> $OUTPUT_FILE_NAME
echo ${threadRemotes[@]} >> $OUTPUT_FILE_NAME
echo >> $OUTPUT_FILE_NAME

# # Get Entire Stack Trace according to input arguments
#         # timeStamps is an array of timeStamps. Size = NUMCALLS
# After this function call, individual thread stacks are stored in file with filenames threadId_timeStamp. Can be retrieved from there
timeStamps=()
takeStackTrace
echo "" >> $OUTPUT_FILE_NAME       
echo "-----resynchronization-----" >> $OUTPUT_FILE_NAME
echo "" >> $OUTPUT_FILE_NAME


# Get Individual Analysis of each timestamp
beginIndividualAnalysis 


# --------------Analysis Part Starts--------------

# Check Idle/Non Idle Threads
newThreadIds=()
for val in "${threadIds[@]}";
do
  value=$(checkIdleOrNot $val)
    # echo $value
    if [ $value -eq 0 ]; then  # Non-Idle 
      newThreadIds+=($val)
    else
      echo "Thread $val is Idle" >> $OUTPUT_FILE_NAME
      echo  >> $OUTPUT_FILE_NAME
    fi
done
echo "The Non-idle Threads are: " >> $OUTPUT_FILE_NAME
threadIds=(${newThreadIds[@]})
echo ${threadIds[@]} >> $OUTPUT_FILE_NAME                         # Array updated. No need to update threadNames, as it is accessed using threadId values itself
echo "" >> $OUTPUT_FILE_NAME


hungThreadIds=()
# Identify Hung Processes
for val in "${threadIds[@]}";
do
  value=$(checkHungOrNot $val)
    # echo $value
    if [ $value -eq 1 ]; then  # Hung
      hungThreadIds+=($val)
    else
      echo "Thread $val is NOT Hung" >> $OUTPUT_FILE_NAME
      echo >> $OUTPUT_FILE_NAME
    fi
done

echo "The Hung threads are: " >> $OUTPUT_FILE_NAME
echo ${hungThreadIds[@]} >> $OUTPUT_FILE_NAME

wait





# JUNK CODE
# ----

# Calculates Average CPU Usage using info stored in file CPU_${timeStamp} of each thread and prints it
# getCpuUsage(){
#   declare -A cpuUsage
#   local currThread
#   local currCPU
#   for timeStamp in ${timeStamps[@]};
#   do
#     local fileName="CPU_$timeStamp"
#     while read -r line; 
#     do 
#       currThread="$(echo $line | awk '{print $1;}')"
#       currCPU="$(echo $line | awk '{print $2;}')"
#       cpuUsage[$currThread]=$(awk '{print $1+$2}' <<<"${cpuUsage[currThead]:-0} ${currCPU}")
#       echo "$currThread: $currCPU: ${cpuUsage[$currThread]}"
#     done < $fileName
#   done
#   for thread in ${threadIds[@]};
#   do
#     echo "$thread: ${cpuUsage[$currThread]}"
#   done
  
# }


# # Get Average CPU Usage of each thread and store in map $cpuUsage
# getCpuUsage
# echo ${cpuUsage[@]}