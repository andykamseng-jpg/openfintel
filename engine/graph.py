from typing import Dict, List, Callable, Optional


class Node:
    def __init__(self, node_id: str, name: str, value: float = 0.0, calc_fn: Optional[Callable] = None):
        self.id = node_id
        self.name = name

        self.value = value
        self.target_value = value

        self.parents: List["Node"] = []
        self.children: List["Node"] = []

        self.calc_fn = calc_fn

    def connect(self, child: "Node"):
        if child not in self.children:
            self.children.append(child)
            child.parents.append(self)

    def set_value(self, value: float):
        self.value = value

    def set_target(self, value: float):
        self.target_value = value


class GraphEngine:
    def __init__(self):
        self.nodes: Dict[str, Node] = {}

    def add_node(self, node_id: str, name: str, value: float = 0.0, calc_fn: Optional[Callable] = None):
        node = Node(node_id, name, value, calc_fn)
        self.nodes[node_id] = node
        return node

    def connect(self, parent_id: str, child_id: str):
        self.nodes[parent_id].connect(self.nodes[child_id])

    def get_node(self, node_id: str) -> Node:
        return self.nodes[node_id]

    def recalculate(self):
        visited = set()

        def compute(node: Node):
            if node.id in visited:
                return
            visited.add(node.id)

            for parent in node.parents:
                compute(parent)

            if node.calc_fn:
                node.value = node.calc_fn(node.parents)

        for node in self.nodes.values():
            compute(node)


# helpers
def sum_parents(parents, use_target=False):
    return sum(p.target_value if use_target else p.value for p in parents)


def multiply_parents(parents, use_target=False):
    result = 1
    for p in parents:
        result *= (p.target_value if use_target else p.value)
    return result