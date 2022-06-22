pid=$1
query="$2"
for((i=0;i<10;i++));do
    sudo eu-stack -1 -p $pid >> "IndividualStacks/$2.txt"
    echo "" >> "IndividualStacks/$2.txt"
    sleep 0.1
done