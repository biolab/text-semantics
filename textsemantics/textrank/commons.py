"""
Module was removed from gensim - this is a fixed copy.

This module provides functions of creating graph from sequence of values and
removing unreachable nodes.


Examples
--------

Create simple graph and add edges. Let's take a look at the nodes.

.. sourcecode:: pycon

    >>> from textsemantics.textrank.commons import build_graph, remove_unreachable_nodes
    >>> gg = build_graph(['Felidae', 'Lion', 'Tiger', 'Wolf'])
    >>> gg.add_edge(("Felidae", "Lion"))
    >>> gg.add_edge(("Felidae", "Tiger"))
    >>> sorted(gg.nodes())
    ['Felidae', 'Lion', 'Tiger', 'Wolf']

Remove nodes with no edges.

.. sourcecode:: pycon

    >>> remove_unreachable_nodes(gg)
    >>> sorted(gg.nodes())
    ['Felidae', 'Lion', 'Tiger']

"""

from textsemantics.textrank.graph import Graph


def build_graph(sequence):
    """Creates and returns undirected graph with given sequence of values.

    Parameters
    ----------
    sequence : list of hashable
        Sequence of values.

    Returns
    -------
    :class:`~textsemantics.textrank.graph.Graph`
        Created graph.

    """
    graph = Graph()
    for item in sequence:
        if not graph.has_node(item):
            graph.add_node(item)
    return graph


def remove_unreachable_nodes(graph):
    """Removes unreachable nodes (nodes with no edges), inplace.

    Parameters
    ----------
    graph : :class:`~textsemantics.textrank.graph.Graph`
        Given graph.

    """

    for node in graph.nodes():
        if all(graph.edge_weight((node, other)) == 0 for other in graph.neighbors(node)):
            graph.del_node(node)
