# Get PID of mongod server
pid="$(pidof mongod)"
currTime=$(($(date +%s%N)/1000000))
dir="dataByCommand"
mkdir -p $dir
sudo eu-stack --pid "$pid" > "$dir/entireStackTrace_$currTime".txt 2>&- &
# Get all threads at time of taking stack
top -H -p $pid -bn1 -w512 | grep "mongo" > "$dir/threadDetailsTopH_$currTime".txt 2>&-
wait

