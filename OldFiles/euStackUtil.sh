#!/bin/bash
timeStamp=$1
pid=$2

echo "Taking Stack Trace with timestamp: ${timeStamp} and pid: ${pid}"

stackDump="$(sudo eu-stack -p $pid --source))"
echo "$stackDump" > "stackDumps/FullStack_${timeStamp}"

