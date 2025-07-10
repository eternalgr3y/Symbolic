python - << 'PY'
from grimp.adaptors.imports import ImportFinder
from grimp.adaptors.graph import ImportGraph

graph = ImportGraph()
ImportFinder().populate_graph(graph, ["symbolic_agi"])

cycles = graph.find_cycles()
if cycles:
    print("Found cycles:")
    for cycle in cycles:
        print("  -> ".join(cycle))
else:
    print("No cycles detected.")
PY
