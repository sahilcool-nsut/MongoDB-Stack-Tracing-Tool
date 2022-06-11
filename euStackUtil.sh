#!/bin/bash
timeStamp=$1
pid=$2
shift
shift
threadIds=("$@")

echo "inside util script with timestamp: ${timeStamp} and pid: ${pid}"

extractStackOfThread(){
  # $1 = threadId
  local NL=$'\n'    
  local startPattern="$1:$NL"   #add newline character too, so that starts directly from stack
  local stackSubstring="${stackDump#*${startPattern}}"   #removes everything before startingPattern from stack
  local endPattern="${NL}TID"
  local stackSubstring="${stackSubstring%%${endPattern}*}"   #removes everything after endString from stack

  # Handling special case for stack of thread which is the last thread (ends an extra ")" in the end of stack)
  if [ "${stackSubstring: -1}" == ")" ]; then
    stackSubstring="${stackSubstring::-1}"
  fi
  local fileName="${1}_${timeStamp}"

  echo "$stackSubstring" > $fileName
}


stackDump="$(sudo eu-stack -p $pid --source))"

for val in "${threadIds[@]}";
do
    extractStackOfThread $val
done