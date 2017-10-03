import copy
import bp
import numpy as np

class JunctionTree(object):
    def __init__(self, key_sizes, trees=[]):
        self.key_sizes = key_sizes
        self.labels = {vl:i for i, vl in enumerate(sorted(key_sizes.keys()))}
        self.sorted_labels = self._get_labels()
        self.struct = []
        self.clique_keys = {} # clique_ix -> list of keys
        self.tree_cliques = [[]]*len(trees) # tree_ix -> list of clique_ixs
        self.keys_to_cliques = {} # key -> list of cliques containing key
        self.cliques_to_trees = {} # clique_ix -> tree_ix
        for t_i, tree in enumerate(trees):
            indexed_tree = self.map_keys(tree, self.labels)
            self.struct.append(indexed_tree)
            clique_id_keys = list(bp.df_traverse([indexed_tree]))
            for i in range(0, len(clique_id_keys), 2):
                clique_ix = clique_id_keys[i]
                clique_keys = clique_id_keys[i+1]
                self.clique_keys[clique_ix] = clique_keys
                self.cliques_to_trees[clique_ix] = t_i
                self.tree_cliques[t_i].append(clique_ix)
                for key in clique_keys:
                    self.keys_to_cliques.setdefault(key, [])
                    self.keys_to_cliques[key].append(clique_ix)






    def find_key(self, key_label):
        """
        Return index of key in tree keys

        Input:
        ------

        Key label as provided when junction tree constructed

        Output:
        -------

        Key index (or None if key not in tree)

        """
        try:
            key_ix = self.labels[key_label]
            return key_ix
        except ValueError:
            return None

    def get_key_ix(self, clique_ix, key_label):
        """
        Returns index of key in clique's set of keys

        Input:
        ------

        Clique ID

        Key label

        Output:
        -------

        Index of key in clique's keys

        """
        try:
            keys = self.clique_keys[clique_ix]
            key_ix = self.find_key(key_label)
            return keys.index(key_ix)
        except (AttributeError, ValueError):
            return None

    def get_key_sizes(self):
        """
        Returns dictionary of key labels as keys
            and key size as values

        """
        return self.key_sizes

    def get_label_order(self):
        """
        Return dictionary with key label as key
            and index as value
        """
        return self.labels

    def _get_labels(self):
        """
        Returns key labels in sorted order

        """
        labels = [None]*len(self.labels)
        for k,i in self.labels.items():
            labels[i] = k

        return labels

    def get_struct(self):
        """
        Return structure of junction tree

        """
        return self.struct

    def get_sorted_labels(self):
        """
        Return get labels in sorted order
        """
        return self.sorted_labels

    def get_clique_keys(self):
        """
        Return get clique key mappings
        """
        return self.clique_keys

    def get_clique_sepset(self):
        """
        Return the mapping of clique keys to sepset keys
        """
        return self.clique_sepset

    @staticmethod
    def map_keys(tree, lookup):
        """
        Map keys of cliques to index values

        Input:
        ------

        Tree structure

        Lookup dictonary with key label as key and
            key index (in junction tree) as value

        Output:
        -------
        Return tree with re-indexed clique keys


        """
        cp_tree = copy.deepcopy(tree)

        def __run(tree, lookup, ss_parent=None):
            ix, keys = tree[0:2]
            for i, k in enumerate(keys):
                keys[i] = lookup[k]
            m_keys = {k:i for i,k in enumerate(keys)}
            mapped_keys = [m_keys[k] for k in keys]
            if ss_parent:
                sep_ix, sep_keys = ss_parent[0:2]

            separators = tree[2:]

            for separator in separators:
                separator_ix, separator_keys, c_tree = separator
                for i, k in enumerate(separator_keys):
                    separator_keys[i] = lookup[k]

                __run(c_tree, lookup, separator[0:2])

        __run(cp_tree, lookup)
        return cp_tree


    @staticmethod
    def from_factor_graph(factor_graph):
        """
        Construct a junction tree from factor graph

        Input:
        ------

        Factor graph as list of key sizes, list of
            factors (keys), and list of factor potentials

        Output:
        -------

        Resulting JunctionTree and initial potentials


        """
        key_sizes = factor_graph[0]
        factors = factor_graph[1]
        values = factor_graph[2]
        tri,induced_clusters = bp.find_triangulation(
                            key_sizes=factor_graph[0],
                            factors=factor_graph[1]
        )
        cliques = bp.identify_cliques(induced_clusters)
        trees = bp.construct_junction_tree(cliques, key_sizes)
        jt = JunctionTree(key_sizes, trees)
        phi = JunctionTree.init_potentials(jt, factors, values)
        return jt, phi

    @staticmethod
    def init_potentials(tree, factors, values):
        """
        Creates initial potentials based on factors

        Input:
        ------

        Tree structure of the junction tree

        List of factors (key lists)

        List of factor potentials

        Output:
        -------

        Initial potentials

        """
        clique_id_keys = list(bp.bf_traverse(tree.get_struct()))
        clique_lookup = {}
        potentials = [[]]*(int(len(clique_id_keys)/2))

        labels = tree.get_sorted_labels()
        key_sizes = tree.get_key_sizes()
        mapped_keys = {}

        for clique_ix, clique_keys in tree.get_clique_keys().items():
            # initialize all potentials
            clique_lookup[clique_ix] = clique_keys
            potentials[clique_ix] = np.ones([key_sizes[labels[ix]] for ix in clique_keys])
            # map keys to get around variable count limitation in einsum
            m_keys = {k:i for i,k in enumerate(clique_keys)}
            mapped_keys[clique_ix] = (m_keys,[m_keys[k] for k in clique_keys])

        for i, factor in enumerate(factors):
            # convert factor to its indexed keys
            factor_keys = [tree.find_key(key) for key in factor]
            # find clique to multiply factor into
            for clique_ix, clique_keys in clique_lookup.items():
                if set(factor_keys).issubset(clique_keys):
                    mapped_clique_keys = mapped_keys[clique_ix][1]
                    mapper = mapped_keys[clique_ix][0]

                    # multiply factor into clique
                    potentials[clique_ix] = bp.sum_product.einsum(
                                                potentials[clique_ix],
                                                mapped_clique_keys,
                                                values[i],
                                                [mapper[k] for k in factor_keys],
                                                mapped_clique_keys
                    )
                    break

        return(potentials)

    def observe(self, potentials, data):
        """
        Return updated clique potentials based on observed data

        Input:
        ------

        List of potentials

        Dictionary of key label as key and key assignment as value

        Output:
        -------

        List of likelihood potentials

        List of updated clique potentials

        Shrink mapping of clique to reduced key set

        """
        key_sizes = self.get_key_sizes()
        # set values of ll based on data argument
        ll = {
                    key_lbl:[1 if j == data[key_lbl] else 0 for j in range(0, key_sizes[key_lbl])]
                        if key_lbl in data else [1]*key_sizes[key_lbl]
                            for key_lbl in self.sorted_labels
                }

        # shrink mapping filled with (array indexer, shrunk key) pairs for
        # each potential
        shrink_mapping = [
                            (
                                [slice(None)]*len(potentials[i].shape),
                                list(self.clique_keys[i])
                            )
                            for i in range(len(potentials))
                        ]


        # alter potentials based on likelihoods
        for key_lbl,val in data.items():
            # find clique that contains key
            key_ix = self.find_key(key_lbl)
            for tree in self.get_struct():
                clique_ix, clique_keys = bp.get_clique_of_key(
                                                        tree,
                                                        key_ix
                )
                if clique_ix and clique_keys: break

            # map keys to get around variable count limitation in einsum
            mapped_keys = []
            m_keys = {}
            for i,k in enumerate(clique_keys):
                m_keys[k] = i
                mapped_keys.append(i)


            # multiply clique's potential by likelihood
            potentials[clique_ix] = bp.sum_product.einsum(
                                        potentials[clique_ix],
                                        mapped_keys,
                                        ll[key_lbl],
                                        [m_keys[key_ix]],
                                        mapped_keys
            )
            # remove key_ix from key set for all clique's containing key
            for clique_ix in self.keys_to_cliques[key_ix]:
                shrink_mapping[clique_ix][1].remove(key_ix)
                # update key to have observed value in array indexer
                keys = self.clique_keys[clique_ix]
                c_key_ix = keys.index(key_ix)
                shrink_mapping[clique_ix][0][c_key_ix] = val

        # convert array indexer to tuple
        for i in range(len(shrink_mapping)):
            shrink_mapping[i] = (tuple(shrink_mapping[i][0]), shrink_mapping[i][1])

        return (ll, potentials, shrink_mapping)

    def propagate(self, potentials, in_place=True, data=None):
        """
        Return consistent potentials

        Input:
        ------

        List of inconsistent potentials

        Boolean to do updates in place

        Dictionary of key label as key and key assignment as value

        Output:
        -------

        Updated list of (consistent) potentials and
            normalization constants for each tree

        """
        new_potentials = potentials if in_place else copy.deepcopy(potentials)
        shrink_mapping = None
        if data:
            likelihood, new_potentials, shrink_mapping = self.observe(new_potentials, data=data)

        for i, tree in enumerate(self.get_struct()):
            new_potentials = bp.hugin(
                                    tree,
                                    self.get_label_order(),
                                    new_potentials,
                                    bp.sum_product,
                                    shrink_mapping
        )

        return new_potentials

    def marginalize(self, potentials, key_labels, normalize=False):
        """
        Marginalize key from consistent potentials

        Input:
        ------

        List of consistent potentials

        Key to marginalize

        Normalize value?

        Output:
        -------

        Marginalized value of key (unnormalized by default)

        """
        if len(key_labels) > 1:
            raise NotImplementedError

        for key_label in key_labels:
            if key_label not in self.key_sizes:
                raise ValueError("Key %s not in tree" % key_label)


        key_ix = self.find_key(key_labels[0])
        clique_ix = self.keys_to_cliques[key_ix][0]
        clique_keys = self.clique_keys[clique_ix]


        # map keys to get around variable count limitation in einsum
        mapped_keys = []
        m_keys = {}
        for i,k in enumerate(clique_keys):
            m_keys[k] = i
            mapped_keys.append(i)

        try:
            value = bp.compute_marginal(
                                potentials[clique_ix],
                                mapped_keys,
                                m_keys[key_ix]
            )
        except ValueError:
            # key_ix not in mapped keys
            return 0.0

        Z = 1. if not normalize else np.sum(value)
        if Z == 0:
            Z = 1.

        return value/Z
