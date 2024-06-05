# requires graphviz dot (usually, the package is called graphviz)
# on Mac OS, use `open` instead of xdg-open; on Windows, use `start`
rm -f output.dot output.svg && \
    python3 curd.py /home/peter/Documents/research/entrance-exam/concepts.json && \
    dot -Tsvg -o output.svg output.dot && \
    xdg-open output.svg
