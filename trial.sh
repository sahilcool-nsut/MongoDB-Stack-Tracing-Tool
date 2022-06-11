input="4052_1654837235439"
idleStack="$(echo "$(sed 's| 0x................\b\b||g' "$input")")"
echo "$idleStack"

fileName="IDLE_STACK_FORMAT"
echo "$idleStack" > $fileName