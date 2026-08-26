CXX ?= g++
CXXFLAGS ?= -O2 -std=c++17 -Wall -Wextra

.PHONY: all test clean

all: sched

sched: solution.cpp
	$(CXX) $(CXXFLAGS) -o $@ $<

test: sched
	./sched < tests/example1.in | diff -u tests/example1.out -
	python3 tests/sim.py ./sched

clean:
	rm -f sched
