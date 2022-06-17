# MongoDB-Stack-Tracing-Tool
This Repository contains a tool used to acquire live Stack Traces of a running MongoDB Server.
This utility can be useful in debugging issues in real-time when the server is experiencing high CPU usage due to client queries. 

The shell script is built to run on linux based systems, utilising the eu-stack utility of elfutils package. 
It further refines the results and can provide:
  1) Individual Stack Trace Reports in JSON format
  2) Information regarding individual thread states, CPU usage, client names etc.

