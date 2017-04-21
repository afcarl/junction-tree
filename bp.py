"""Belief propagation, junction trees etc

Everything in this file is just rough sketching and ideas at the moment.
Probably many things will change when implementing and learning.


Factor graphs:
--------------

A factor graph is given as a list of keys that tell which variables are in the
factor. (A key corresponds to a variable.)

[keys1, ..., keysN]  # a list of N factors

The index in the list can be used as an ID for the factor, that is, the first
factor in the list has ID 0 and the last factor has ID N-1.

A companion list (of numpy arrays) of the same length as the factor list is
provided as a representation for the factor values

[values1, ..., valuesN]

Also, the size of each of the M variables can be given as a dictionary:

{
    key1: size1,
    ...
    keyM: sizeM
}

Here, size is an integer telling the size of the variable. It is the same as
the length of the corresponding axis in the array later.

No moralization function should be needed.


Generic trees (recursive definition):
-------------------------------------

[index, keys, child_tree1, ..., child_treeN]

The index can, for instance, refer to the index of the factor?


Junction trees:
---------------


[index, keys, (separator1_keys, child_tree1), ..., (separatorN_keys, child_treeN)]


Junction trees:

[
    index, keys
    (
        separator1_index, separator1_keys
        child_tree1
    ),
    ...,
    (
        separatorN_index, separatorN_keys
        child_treeN
    )
]

Potentials in (junction) trees:
-------------------------------

A list/dictionary of arrays. The node IDs in the tree graphs map
to the arrays in this data structure in order to get the numeric
arrays in the execution phase. The numeric arrays are not needed
in the compilation phase.


Idea:

Junction tree construction constructs a function which can then be used
multiple times to create the junction tree for particular array values in the
factor graph. This allows one to compile the junction tree only once and then
use the result for varying values in the factors (but with the same graph
structure, obviously). That is, the junction tree construction depends only on
the factor graph structure and the array shapes, but not the values in the
arrays.


One junction tree algorithm reference:
http://compbio.fmph.uniba.sk/vyuka/gm/old/2010-02/handouts/junction-tree.pdf


General guidelines:

- Use functional approach:

  - pure functions (no side effects)

  - immutable data structures

  - prefer expressions over statements (e.g., if-else expression rather than
    if-else statement)

- Provide functions as a library so that users can use only some functions
  alone without needing to use the full stack

- Try to keep the implementation such that it would be possible to use, for
  instance, TensorFlow or Theano for the library. Not a thing to focus now
  but just something to keep in mind.

- Write tests comprehensively, preferably before the actual implementation

"""

"""
According to Hugin reference (Section 3.1, p. 1083) Jensen (Junction Trees and Decomposable
Hypergraphs - 1988) proved that a junction tree can be constructed by a maximal spanning tree algorithm
"""

import numpy as np
import heapq


def find_triangulation(factor_graph, sizes):
    """Triangulate given factor graph.

    TODO: Provide different algorithms.

    Inputs:
    -------

    Factor graph syntax is a list of factor where each factor is given as a
    list of variable keys the factor contains:

    [keys1, ..., keysN]

    Also, give the sizes of the variables as a dictionary:

    {
        key1: size1,
        ...
        keyM: sizeM
    }

    Output:
    -------

    A list of maximal cliques where each maximal clique is a tuple/list of
    factor indices it contains:

    [clique1, ..., cliqueK]

    That is, if there are N factors, each clique contains some subset of
    numbers from {0, ..., N-1} as a tuple/list.

    Notes
    -----
    A clique may contain multiple factors.

    See:
    http://www.stat.washington.edu/courses/stat535/fall11/Handouts/l5-decomposable.pdf

    """
    raise NotImplementedError()


def triangulate(triangulation, arrays):
    """
    Apply pre-computed triangulation

    Inputs:
    -------

    Triangulation returned by find_triangulation.

    List of arrays for the factors

    Output:
    -------

    List of arrays for the cliques.

    """
    raise NotImplementedError()


def construct_junction_tree(tbd):
    """
    Input: ?

    Output: ?
    """
    raise NotImplementedError()


def get_maximum_weight_spanning_tree(tbd):
    """
    Input: ?

    Output: ?
    """
    raise NotImplementedError()


def eliminate_variables(junction_tree):
    """Eliminate all other variables except the root variables"""

    def __run(tree, variables):
        """Run variable elimination recursively

        Construct trees with nested lists as:

        [array, axis_keys, child_tree1, ..., child_treeN]

        where each child tree has the same syntax recursively.

        Axis keys are some unique identifiers used to determine which axis in
        different array correspond to each other and they are used directly as
        keys for numpy.einsum. It should hold that len(axis_keys) ==
        np.ndim(array). TODO: numpy.einsum supports only keys up to 32, thus in
        order to support arbitrary number keys in the whole tree, one should
        map the keys for the curren numpy.einsum to unique integers starting
        from 0.

        """

        common_child_variables = [
            [
                variable
                for variable in variables
                if variable in child_tree[1]
            ]
            for child_tree in tree[2:]
        ]

        xs = [
            __run(
                child_tree,
                child_variables
            )
            for (child_tree, child_variables) in zip(tree[2:], common_child_variables)
        ]

        xs_is = zip(xs, common_child_variables)
        args = [
            z
            for x_i in xs_is
            for z in x_i
        ] + [tree[0], tree[1], variables]

        return np.einsum(*args)

    return __run(junction_tree, junction_tree[1])


def initialize(tree):
    """Given Junction tree, initialize separator arrays

    TODO/FIXME: Perhaps this should be part of the junction tree constructor
    function. That is, this shouldn't need to be run when array values change
    but only once for a graph!

    Input tree format:

    [array, keys, (separator1_keys, child_tree1), ..., (separatorN_keys, child_treeN)]

    Output tree format:

    [array, keys, (separator1_array, separator1_keys, child_tree1), ... (separatorN_array, separatorN_keys, child_treeN)]

    QUESTION: How to separate the graph structure and its junction tree from
    the array values in each factor? Perhaps use a list of arrays and then the
    tree just contains indices to find the correct array in that list?

    """
    raise NotImplementedError()


def collect(tree, potentials, visited, clique_index=0):
    """ Used by Hugin algorithm to collect messages """
    # set clique_index in visited to 1

    # loop over neighbors of clique
        # call collect on neighbor if not marked as visited
    # return messages from neighbors (in what form? setting a new value for the potential?)
    raise NotImplementedError()


def distribute(tree, potentials, visited, clique_index=0):
    """ Used by Hugin algorithm to distribute messages """
    # set clique_index in visited to 1

    # loop over neighbors of clique_index
        # if neighbor unmarked
            # pass a message (in what form? update to clique's potential) to neighbor if not marked
            # call distribute on neighbor

    raise NotImplementedError()


def hugin(junction_tree, potentials, distributive_law, root_index=0):
    """Run hugin algorithm by using the given distributive law.

    Input tree format:

    [array, keys, (separator1_array, separator1_keys, child_tree1), ... (separatorN_array, separatorN_keys, child_treeN)]

    Output tree format is the same?

    See page 3:
    http://compbio.fmph.uniba.sk/vyuka/gm/old/2010-02/handouts/junction-tree.pdf
    """
    # initialize visited array which has the same number of elements as potentials array
    #visited = [0]*len(potentials)

    # call collect on root_index storing the result in new_potentials

    # initialize visited array again
    #visited = [0]*len(potentials)

    # return the result of a call to distribute on root index

    # Not implemented yet. Just return the potentials.
    return potentials

def get_clique(tree, var_label):
    idx, keys = tree[0:2]
    separators = tree[2:]
    if var_label in keys:
        return idx
    if separators == (): # base case reached (leaf)
        return None

    for separator in separators:
        separator_idx, separator_keys, c_tree = separator
        if var_label in separator_keys:
            return separator_idx
        clique_idx = get_clique(c_tree, var_label)
        if clique_idx:
            return clique_idx

    return None

def compute_marginal(arr, _vars, _vars_ss):
    return np.einsum(arr, _vars, _vars_ss)

def project(arr, _vars):
    return compute_marginal(arr, _vars)

def absorb(phiC, phiSo, phiSn):
    if not np.count_nonzero(phiSo):
        return np.zeros_like(phiSo)
    return phiC*(phiSn/phiSo)

def observe(tree, potentials, likelihood, data):
    # set values of ll based on data argument
    ll = [
                [1 if j == data[var_lbl] else 0 for j in range(0, tree.get_vars()[var_lbl])]
                    if var_lbl in data else [1]*tree.get_vars()[var_lbl]
                        for var_lbl in tree.get_labels()
            ]
    # alter potentials based on likelihoods
    for var_lbl in data:
        # find clique that contains var
        clique_idx = tree.get_clique_of_var(var_lbl)
        # multiply clique's potential by likelihood
        pot = potentials[clique_idx]
        var_idx = tree.get_var_idx(clique_idx, var_lbl)
        # reshape likelihood potential to allow multiplication with pot
        ll_pot = np.array(ll[var_lbl]).reshape([1 if i!=var_idx else s for i, s in enumerate(pot.shape)])
        potentials[clique_idx] = pot*ll_pot
    return (ll,potentials)

def generate_potential_pairs(tree, potentials):
    if len(tree) < 3:
        return []
    root_idx, root_keys = tree[0:2]
    separators = tree[2:]

    pairs = []
    for sep in separators:
        sep_idx, sep_keys = sep[0:2]
        child_tree = sep[2]
        c_root_idx, c_root_keys = child_tree[0:2]
        pairs.extend(generate_potential_pairs(child_tree, potentials))
        # making a pair from seperator and root of seperator's subtree
        pairs.append(
                        (
                            potentials[c_root_idx],
                            c_root_keys,
                            potentials[sep_idx],
                            sep_keys
                        )
                    )
        # making a pair from root of input tree and seperator
        pairs.append(
                        (
                            potentials[root_idx],
                            root_keys,
                            potentials[sep_idx],
                            sep_keys
                        )
                    )
    return pairs

def yield_id_and_keys(tree):
    yield tree[0]
    yield tree[1]

def yield_clique_pairs(tree):
    for child in tree[2:]:
        yield (tree[0], tree[1], child[0], child[1])


def bf_traverse(tree, clique_id=None, func=yield_id_and_keys):
    """Breadth-first traversal of tree

    Early termination of search is performed
    if clique_id provided

    Output: [id1, keys1, ..., idN, keysN] (or [id1, keys1, ..., cid, ckeys])
    """
    queue = [tree]
    while queue:
        tree = queue.pop(0)
        yield from func(tree)
        if tree[0] == clique_id:
            raise StopIteration
        queue.extend([child for child in tree[2:]])

def df_traverse(tree, clique_id=None, func=yield_id_and_keys):
    """Depth-first traversal of tree

    Early termination of search is performed
    if clique_id provided

    Output: [id1, keys1, ..., idN, keysN] (or [id1, keys1, ..., cid, ckeys])
    """
    stack = [tree]
    while stack:
        tree = stack.pop()
        yield from func(tree)
        if tree[0] == clique_id:
            raise StopIteration
        stack.extend([child for child in reversed(tree[2:])])

def get_clique_keys(tree, clique_id):
    """Return keys for clique with clique_id
        (if clique_id not in tree return None)

    Output: clique_id_keys (or None)
    """
    flist = list(bf_traverse(tree, clique_id))
    return flist[-1] if flist[-2] == clique_id else None


def generate_potential_pairs(tree):
    return []

class SumProduct():
    """ Sum-product distributive law """


    def __init__(self, einsum):
        # Perhaps support for different frameworks (TensorFlow, Theano) could
        # be provided by giving the necessary functions.
        self.einsum = einsum
        return


    def initialize(self, tbd):
        raise NotImplementedError()


    def update(self, clique_a, clique_b, separator):
        # See page 2:
        # http://compbio.fmph.uniba.sk/vyuka/gm/old/2010-02/handouts/junction-tree.pdf

        # Sum variables in A that are not in B
        new_separator = self.einsum(
            clique_a, variables_a,
            variables_separator
        )

        # Compensate the updated separator in the clique
        new_clique_b = self.einsum(
            new_separator / separator, variables_separator,
            clique_b, variables_b,
            variables_b
        )

        return (new_clique_b, new_separator) # may return unchanged clique_a
                                             # too if it helps elsewhere


# Sum-product distributive law for NumPy
sum_product = SumProduct(np.einsum)

class JunctionTree(object):
    def __init__(self, _vars, tree=[]):
        self._vars = _vars
        self.labels = sorted(_vars.keys())
        self.struct = tree

    def find_var(self, var_label):
        try:
            var_idx = self.labels.index(var_label)
            return var_idx
        except ValueError:
            return None

    def get_clique(self, clique_idx):
        idx, keys = self.struct[0:2]
        separators = self.struct[2:]

        if idx == clique_idx:
            return keys
        if separators == (): # base case reached (leaf)
            return None

        for separator in separators:
            separator_idx, separator_keys, c_tree = separator
            if idx == separator_idx:
                return separator_keys
            result = self.get_clique_of_var(c_tree, var_label)
            if result != None:
                return result

        return None


    def get_clique_of_var(self, var_label):
        #for seperator in self.
        idx, keys = self.struct[0:2]
        separators = self.struct[2:]
        if var_label in keys:
            return idx
        if separators == (): # base case reached (leaf)
            return None

        for separator in separators:
            separator_idx, separator_keys, c_tree = separator
            if var_label in separator_keys:
                return separator_idx
            clique_idx = self.get_clique_of_var(c_tree, var_label)
            if clique_idx:
                return clique_idx

        return None

    def get_var_idx(self, clique_idx, var_label):
        try:
            clique = self.get_clique(clique_idx)
            return clique.index(var_label)
        except (AttributeError, ValueError):
            return None

    def get_vars(self):
        return self._vars

    def get_labels(self):
        return self.labels

    def get_struct(self):
        return self.struct
