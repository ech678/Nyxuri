"""PluginResolver — pure dependency-graph resolution (unit-model.md §2).

Pure functions only: a dependency graph in, a topological order out.
Zero I/O, zero state, and no sibling-kernel imports — the layering
contract freezes this module as the stateless computation transaction
(KM2) composes with. Table-driven and testable in isolation.
"""


def resolve_order(graph: dict[str, list[str]]) -> list[str]:
    """Return plugin ids in dependency-safe enable order (Kahn's algorithm).

    Edges pointing at ids outside the graph are ignored (a plugin may declare
    a dependency on something that is not a directory plugin yet). Raises
    ValueError when the graph contains a cycle — the caller must surface
    it instead of guessing an order.
    """
    in_degree = {u: 0 for u in graph}
    for u, deps in graph.items():
        for d in deps:
            if d in in_degree:
                in_degree[u] += 1

    queue = [u for u, deg in in_degree.items() if deg == 0]
    order: list[str] = []
    while queue:
        curr = queue.pop(0)
        order.append(curr)
        for u, deps in graph.items():
            if curr in deps:
                in_degree[u] -= 1
                if in_degree[u] == 0:
                    queue.append(u)

    if len(order) != len(graph):
        raise ValueError("Cyclic dependency detected in plugins")
    return order
