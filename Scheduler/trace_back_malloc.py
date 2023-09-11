import tracemalloc
tracemalloc.start()

# Allocate some objects
a = [1] * 1000000
b = [2] * 1000000
c = [3] * 1000000

# Get the memory usage
current, peak = tracemalloc.get_traced_memory()
print(f"Current memory usage: {current / 10**6} MB")
print(f"Peak memory usage: {peak / 10**6} MB")

# Get the memory usage for each object
snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics('lineno')

# Print the top 10 memory consumers
print("[ Top 10 ]")
for stat in top_stats[:10]:
    print(stat)

# Get the allocation traceback for an object
address = id(a)
traceback = tracemalloc.get_object_traceback(address)
print(traceback)
