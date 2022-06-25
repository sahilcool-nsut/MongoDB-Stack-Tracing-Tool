# Get PID of mongod server
pid="$(pidof mongod)"
# Get the stack trace and save it in a txt file
currTime=$(($(date +%s%N)/1000000))
echo "Starting script at time: $currTime"
sudo eu-stack --pid "$pid" > data/entireStackTrace.txt &
# Get all threads at time of taking stack
top -H -bn1 | grep "conn" | sort -n -k1 > data/threadDetailsTopH.txt

wait

currTime=$(($(date +%s%N)/1000000))
echo "Collected data at time: $currTime"
echo ""
# Call python script to generate report
python createStackReport.py