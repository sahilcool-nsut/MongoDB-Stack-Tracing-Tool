# input="4052_1654837235439"
# idleStack="$(echo "$(sed 's| 0x................\b\b||g' "$input")")"
# echo "$idleStack"

# fileName="IDLE_STACK_FORMAT"
# echo "$idleStack" > $fileName

# threadRemote="$(sudo jq '. | select(.ctx=="conn1" and .c=="NETWORK" and .msg=="client metadata" and .attr.remote)' /var/log/mongodb/mongod.log | grep 'remote": "127' | tail -n 1 | awk '{print $2}' | grep -oP '(?<=").*?(?=")')" 
# echo "$threadRemote"

# pid=5061
# threadId=6193
# cpuValue=$(ps -o spid,pcpu,comm -T ${pid} | grep "$threadId" | awk '{print $2}' )
# echo "${cpuValue}"


# state=$(sudo cat /proc/5377/task/5464/status | grep "State")
# echo "${state}"



# pattern="mongo .* ${threadId} .* EST"
    # echo "$pattern"
    # echo "$networkDetail" | grep "$pattern"
    # threadRemote=$("$networkDetail" | grep "mongo ${threadId}.*EST" | awk '{print $9}')
    # echo $threadRemote
    # netstat -an | grep ":${27017}.*ESTAB"
# $threadRemote=$(sudo lsof -i | grep "mongo .*EST" | awk '{print $2" : "$9}')
# echo "$threadRemote"

currTime=$(($(date +%s%N)/1000000))
echo $currTime
totalCalls=$(ps -T -p 8188 | grep "conn" -c)

multiThreadDetail(){
    index=$1
    local JSON_STRING=$( jq -n \
                  '{threads:[]}')
    echo "$JSON_STRING" > "json$index.json"
    while read -r detail;
    do
        resultsArray=($(echo $detail | awk '{ print $1, $8, $9, $12 }'))
        threadId=${resultsArray[0]}
        threadState=${resultsArray[1]}
        threadCPU=${resultsArray[2]}
        # echo 
        # if (( $(echo "$threadCPU < 20" |bc -l) )); then
        #     break;
        # fi
        # echo $threadId
        threadName=${resultsArray[3]}
        stack="$(sudo eu-stack -1 -p $threadId)"
                  # Create empty threads arary which will be filled later
        local fileName="OutputFiles/IndividualOutput_$currTime.json"            
        
        local JSON_TEMP=$(jq \
        --arg threadId "$threadId" \
        --arg threadName "$threadName" \
        --arg threadState "$threadState" \
        --arg threadCPU "$threadCPU" \
        --arg threadStack "$stack" \
        '.threads += [{threadId: $threadId, threadName: $threadName, threadState: $threadState, threadCPU: $threadCPU, threadStack: $threadStack}]' "json$index.json")
        echo "$JSON_TEMP" > "json$index.json"
        # echo "$stack"
        # threadId=$(echo $detail | awk '{print $1}')
        
    #     # If state array for a threadID already exists, append, else create
        # threadState="$(echo $detail | awk '{print $8}')"
        # 

    #     # If CPU array for a threadID already exists, append, else create
    #    threadCPU="$(echo $detail | awk '{print $9}')"
        
    #     # Can overwrite name in case of clashing thread ID (assuming same thread ID exists over entire duration)
        # threadName="$(echo $detail | awk '{print $12}')"
        
        # echo $threadId
        # currTime=$(($(date +%s%N)/1000000))
        # echo $currTime
        # printf "\n"
    done < <(top -H -bn1 | grep -m 10 "conn")
}
for ((i=0;i<3;i++)); do
    multiThreadDetail $i &
    sleep 0.2
done

wait
currTime=$(($(date +%s%N)/1000000))
echo $currTime
# 1655438447582