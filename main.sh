





OUTPUT_FILE_NAME="JointAnalysis"

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
