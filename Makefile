CXX ?= g++
CXXFLAGS ?= -O2 -std=c++17 -Wall -Wextra

.PHONY: all test bench clean

all: sched

sched: solution.cpp
	$(CXX) $(CXXFLAGS) -o $@ $<

bench:
	$(CXX) $(CXXFLAGS) -o /tmp/ref_sequential bench/ref_sequential.cpp
	$(CXX) $(CXXFLAGS) -o /tmp/v1 bench/v1_13k.cpp

test: sched bench
	./sched < tests/example1.in | diff -u tests/example1.out -
	python3 tests/sim.py /tmp/v1 ./sched

clean:
	rm -f sched
