import numpy as np

import bp
from bp import get_clique, compute_marginal, project, absorb
import unittest


# Tests here using pytest


def assert_junction_tree_equal(t1, t2):
    """Test equality of two junction trees

    Junction tree syntax:

    [array, keys, child_tree1, ..., child_treeN]

    Note this syntax supports separators in the trees because the separators
    just add levels.

    """
    # Equality of arrays
    np.testing.assert_allclose(t1[0], t2[0])
    # Equality of keys
    assert t1[1] == t2[1]

    # Same number of child trees
    assert len(t1) == len(t2)
    # Equality of child trees (recursively)
    for (child_t1, child_t2) in zip(t1[2:], t2[2:]):
        assert_junction_tree_equal(child_t1, child_t2)

    pass


def get_arrays_and_keys(tree):
    """Get all arrays and their keys as a flat list

    Output: [array1, keys1, ..., arrayN, keysN]

    """
    return list(tree[:2]) + sum(
        [
            get_arrays_and_keys(child_tree)
            for child_tree in tree[2:]
        ],
        []
    )


def brute_force_sum_product(junction_tree):
    """Compute brute force sum-product with einsum """

    # Function to compute the sum-product with brute force einsum
    arrays_keys = get_arrays_and_keys(junction_tree)
    f = lambda output_keys: np.einsum(*(arrays_keys + [output_keys]))

    def __run(tree, f):
        return [
            f(tree[1]),
            tree[1],
            *[
                __run(child_tree, f)
                for child_tree in tree[2:]
            ]
        ]

    return __run(junction_tree, f)


def assert_sum_product(tree):
    """ Test hugin vs brute force sum-product """
    assert_junction_tree_equal(
        brute_force_sum_product(tree),
        bp.hugin(tree, bp.sum_product)
    )
    pass


def test_hugin():
    """ Test hugin sum-product """

    # One scalar node
    assert_sum_product(
        [
            np.random.randn(),
            []
        ]
    )

    # One matrix node
    assert_sum_product(
        [
            np.random.randn(2, 3),
            [3, 5]
        ]
    )

    # One child node with all variables shared
    assert_sum_product(
        [
            np.random.randn(2, 3),
            [3, 5],
            (
                np.ones((3, 2)),
                [5, 3],
                [
                    np.random.randn(3, 2),
                    [5, 3],
                ]
            )
        ]
    )

    # One child node with one common variable
    assert_sum_product(
        [
            np.random.randn(2, 3),
            [3, 5],
            (
                np.ones((3,)),
                [5],
                [
                    np.random.randn(3, 4),
                    [5, 9]
                ]
            )
        ]
    )

    # One child node with no common variable
    assert_sum_product(
        [
            np.random.randn(2),
            [3],
            (
                np.ones(()),
                [],
                [
                    np.random.randn(3),
                    [9]
                ]
            )
        ]
    )

    # One grand child node (not sharing with grand parent)
    assert_sum_product(
        [
            np.random.randn(2, 3),
            [3, 5],
            (
                np.ones((3,)),
                [5],
                [
                    np.random.randn(3, 4),
                    [5, 9],
                    (
                        np.ones((4,)),
                        [9],
                        [
                            np.random.randn(4, 5),
                            [9, 1]
                        ]
                    )
                ]
            )
        ]
    )

    # One grand child node (sharing with grand parent)
    assert_sum_product(
        [
            np.random.randn(2, 3),
            [3, 5],
            (
                np.ones((3,)),
                [5],
                [
                    np.random.randn(3, 4),
                    [5, 9],
                    (
                        np.ones((3,)),
                        [5],
                        [
                            np.random.randn(6, 3),
                            [1, 5]
                        ]
                    )
                ]
            )
        ]
    )

    # Two children (not sharing)
    assert_sum_product(
        [
            np.random.randn(2, 3),
            [3, 5],
            (
                np.ones((3,)),
                [5],
                [
                    np.random.randn(3, 4),
                    [5, 9],
                ]
            ),
            (
                np.ones((2,)),
                [3],
                [
                    np.random.randn(2, 5),
                    [3, 1]
                ]
            )
        ]
    )

    # Two children (sharing)
    assert_sum_product(
        [
            np.random.randn(2, 3),
            [3, 5],
            (
                np.ones((3,)),
                [5],
                [
                    np.random.randn(3, 4),
                    [5, 9],
                ]
            ),
            (
                np.ones((3,)),
                [5],
                [
                    np.random.randn(3),
                    [5]
                ]
            )
        ]
    )

    # Two children (with 3-D tensors)
    assert_sum_product(
        [
            np.random.randn(2, 3, 4),
            [3, 5, 7],
            (
                np.ones((3, 4)),
                [5, 7],
                [
                    np.random.randn(3, 4, 5),
                    [5, 7, 9],
                ]
            ),
            (
                np.ones((3,)),
                [5],
                [
                    np.random.randn(3, 6),
                    [5, 1]
                ]
            )
        ]
    )

    pass

class TestHUGINFunctionality(unittest.TestCase):
    '''
    examples taken from here:
    https://www.cs.ru.nl/~peterl/BN/examplesproofs.pdf
    http://www.inf.ed.ac.uk/teaching/courses/pmr/docs/jta_ex.pdf
    background here:
    http://web4.cs.ucl.ac.uk/staff/D.Barber/textbook/171216.pdf
    comparison between HUGIN and Shafer-Shenoy
    https://arxiv.org/pdf/1302.1553.pdf
    some python code for junction tree algorithm
    http://leo.ugr.es/pgm2012/proceedings/eproceedings/evers_a_framework.pdf
    https://github.com/eBay/bayesian-belief-networks

    var -> key_id:
    V1 -> 0
    V2 -> 1
    V3 -> 2

    factor -> factor_id:
    f(V2) -> 0 [f(1)]
    f(V1,V2) -> 1 [f(0,1)]
    f(V3,V2) -> 2 [f(2,1)]

    clique -> clique_id:
    (V1,V2) -> 0
    (V2) -> 1
    (V2,V3) -> 2

    [0, [0,1], (1, [1], [2, [1,2]]),]


    which potentials need to be represented????

    '''

    def test_marginalize_variable(self):
        '''
            given consistent clique potentials, calculate the marginal probability of
            a variable in the clique
            use example from Huang and Darwiche (H&D)

             a   b   d  |  phi_ABD(abd)
            --------------------------
            on  on  on  |   0.225
            on  on  off |   0.025
            on  off on  |   0.125
            on  off off |   0.125
            off on  on  |   0.180
            off on  off |   0.020
            off off on  |   0.150
            off off off |   0.150

            >>> ABD = np.ndarray(shape=(2,2,2))
            >>> ABD[1,1,1] = 0.225
            >>> ABD[1,1,0] = 0.025
            >>> ABD[1,0,1] = 0.125
            >>> ABD[1,0,0] = 0.125
            >>> ABD[0,1,1] = 0.180
            >>> ABD[0,1,0] = 0.020
            >>> ABD[0,0,1] = 0.150
            >>> ABD[0,0,0] = 0.150
        '''

        phiABD=np.array([
                            [
                                [ 0.15 ,  0.15 ],
                                [ 0.02 ,  0.18 ]
                            ],
                            [
                                [ 0.125,  0.125],
                                [ 0.025,  0.225]
                            ]
                        ])
        # https://obilaniu6266h16.wordpress.com/2016/02/04/einstein-summation-in-numpy/
        # marginal probability of A, P(A)
        assert np.allclose(compute_marginal(phiABD, [0]), np.array([0.500, 0.500])) == True
        # marginal probability of D, P(D)
        assert np.allclose(np.array([0.32,0.68]), np.array([0.320, 0.680])) == True


    def test_pass_message(self):
        '''
            Example taken from here: https://www.cs.ru.nl/~peterl/BN/examplesproofs.pdf
            Example will be processed under the assumption that potentials have been
            properly initialized outside of this test

            Variables: V1, V2, V3
            \pi_{V1} = [V2] # parents of V1
            \pi_{V2} = [] # parents of V2
            \pi_{V3} = [V2] # parents of V3
            F_{V1} = [V1, V2]
            F_{V2} = [V2]
            F_{V3} = [V2, V3]

            P(v1|v2) = 0.2
            P(v1|~v2) = 0.6
            P(~v1|v2) = 0.8
            P(~v1|~v2) = 0.4
            P(v3|v2) = 0.5
            P(v3|~v2) = 0.7
            P(~v3|v2) = 0.5
            P(~v3|~v2) = 0.3
            P(v2) = 0.9
            P(~v2) = 0.1


            V1  V2  |   \phi_{V1V2} (P(V1|V2))
            ------------------------
            0   0   |   0.4
            0   1   |   0.8
            1   0   |   0.6
            1   1   |   0.2


            V2  |   \phi_{V2} (1)
            -----------------
            0   |   1
            1   |   1

            V2  V3  |   \phi_{V2V3} (P(V3|V2)P(V2))
            -------------------------
            0   0   |   0.3 * 0.1 = 0.03
            0   1   |   0.7 * 0.1 = 0.07
            1   0   |   0.5 * 0.9 = 0.45
            1   1   |   0.5 * 0.9 = 0.45

        '''

        phi12 = np.array([
                            [0.4, 0.8],
                            [0.6, 0.2]
                        ])

        phi2 = np.array([1, 1])
        phi23 = np.array([
                            [0.03, 0.07],
                            [0.45, 0.45]
                        ])

        phi2n = project(phi12, [1])
        np.allclose(phi2n, np.array([1,1])) == True
        phi23 = absorb(phi23, phi2, phi2n)
        np.allclose(phi23, np.array([
                                        [0.03,0.07],
                                        [0.45,0.45]
                                    ])) == True

        phi2nn = project(phi23, [0])
        np.allclose(phi2nn, np.array([0.9, 0.1])) == True
        phi12 = absorb(phi12, phi2n, phi2nn)
        np.allclose(phi12, np.array([
                                        [0.04,0.72],
                                        [0.06,0.18]
                                    ]))


    def test_collect_messages(self):
        '''
            Potentials to be used based on assignments in:
            http://www.inf.ed.ac.uk/teaching/courses/pmr/docs/jta_ex.pdf

            peace = 1
            war = 0
            yes = 1
            no = 0
            stay = 0
            run = 1
            decrease = 0
            no change = 1
            increase = 2

            P(L=1) = 0.4
            P(Q=1) = 0.6
            P(S=1|L=1) = 0.8
            P(S=0|L=1) = 0.2
            P(S=1|L=0) = 0.3
            P(S=0|L=0) = 0.7


            S   L   |   \phi_{SL} (P(L)P(S|L))
            ----------------------------------
            0   0   |   0.6 x 0.7 = 0.42
            0   1   |   0.4 x
        '''
        pass

    def test_distribute_messages(self):
        pass

    def test_consistency(self):
        # consistency: summing the potential of a cluster X over variables in the cluster not included in
        # sepset S, is equal to potential of S
        pass


class TestJunctionTreeConstruction(self):
    def test_can_locate_clique_containing_variable(self):
        tree = [0, [0,1], (1, [1], [2, [1,2]])]
        clique = get_clique(tree, 2)
        assert clique == 2

    def test_assign_var_to_cluster(self):
        pass

    def test_initialize_potentials(self):
        # this initialization is important to get proper messages passed
        # discussed on page 111 of Bayesian Reasoning and Machine Learnging
        # discussed on page 723 of Machine Learning: A Probabilistic Perspective
        pass
