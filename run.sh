f="$1"
b=`basename "$f" .json`

python3 curd.py -f "$f" && dot -Tpng "$b.dot" > "$b.png" && xdg-open "$b.png"
