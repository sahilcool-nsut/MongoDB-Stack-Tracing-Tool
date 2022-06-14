takeStakeTraceUtil(){
    # $1 = currTime
    echo $"Taking stack dump at timestamp $1"
    # timeStamps+=(${1})
    stackDump="$(sudo eu-stack -p $pid --source))"    
    # stackTraces[$1]="$stackDump"         
    echo "$stackDump"
}

takeStakeTraceUtil