GCC=gcc
EXEC=antichains
SRC=$(EXEC).dl
LIB=libfunctors
LIB_SO=$(LIB).so
LIB_O=$(LIB).o
LIB_SRC=helpers.c

.PHONY=run
run: $(EXEC)
	./$(EXEC)

$(EXEC): $(SRC) # $(LIB_SO)
	souffle $< -o $(EXEC) -j8

$(LIB_O): $(LIB_SRC)
	gcc -c -fPIC -o $@ $<

$(LIB_SO): $(LIB_O)
	gcc -shared -o $@ $<

.PHONY=clean
clean:
	rm -f $(EXEC) *.csv $(LIB_O) $(LIB_SO)
