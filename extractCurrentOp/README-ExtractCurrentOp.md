# III. CPU-Intensive Current Ops Extraction
./extractCurrentOp

This is a which returns a JSON file which contains details of the current High CPU-Intensive mongo clients, and what command the threads have hit. 

This is achieved through the use of the top -H command and the db.currentOp() command feature provided by mongosh.

> top -H -bn1 | grep "conn" > topH.txt
>
> mongosh localhost:27017 --eval 'EJSON.stringify(db.currentOp())' --quiet
