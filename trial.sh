# input="4052_1654837235439"
# idleStack="$(echo "$(sed 's| 0x................\b\b||g' "$input")")"
# echo "$idleStack"

# fileName="IDLE_STACK_FORMAT"
# echo "$idleStack" > $fileName

threadRemote="$(sudo jq '. | select(.ctx=="conn1" and .c=="NETWORK" and .msg=="client metadata" and .attr.remote)' /var/log/mongodb/mongod.log | grep 'remote": "127' | tail -n 1 | awk '{print $2}' | grep -oP '(?<=").*?(?=")')" 
echo "$threadRemote"


# pattern="mongo .* ${threadId} .* EST"
    # echo "$pattern"
    # echo "$networkDetail" | grep "$pattern"
    # # threadRemote=$("$networkDetail" | grep "mongo ${threadId}.*EST" | awk '{print $9}')
    # echo $threadRemote
    # netstat -an | grep ":${27017}.*ESTAB" | awk '{print $4":"$5}'