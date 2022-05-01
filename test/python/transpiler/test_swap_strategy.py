# This code is part of Qiskit.
#
# (C) Copyright IBM 2022.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Tests for swap strategies."""

from typing import List
from ddt import data, ddt, unpack
import numpy as np

from qiskit import QiskitError
from qiskit.test import QiskitTestCase
from qiskit.transpiler import CouplingMap

from qiskit.transpiler.passes.routing.swap_strategies import SwapStrategy


@ddt
class TestSwapStrategy(QiskitTestCase):
    """A class to test the swap strategies."""

    def setUp(self):
        super().setUp()
        self.line_coupling_map = CouplingMap(
            couplinglist=[
                (0, 1),
                (1, 2),
                (2, 3),
                (3, 4),
                (1, 0),
                (2, 1),
                (3, 2),
                (4, 3),
            ]
        )

        self.line_swap_layers = (
            ((0, 1), (2, 3)),
            ((1, 2), (3, 4)),
            ((0, 1), (2, 3)),
            ((1, 2), (3, 4)),
            ((0, 1), (2, 3)),
        )

        self.line_edge_coloring = {(0, 1): 0, (1, 2): 1, (2, 3): 0, (3, 4): 1}
        self.line_strategy = SwapStrategy(self.line_coupling_map, self.line_swap_layers)

    @data(
        (0, [0, 1, 2, 3, 4]),
        (1, [1, 0, 3, 2, 4]),
        (2, [1, 3, 0, 4, 2]),
        (3, [3, 1, 4, 0, 2]),
        (4, [3, 4, 1, 2, 0]),
        (5, [4, 3, 2, 1, 0]),
    )
    @unpack
    def test_inverse_composed_permutation(self, layer_idx: int, expected: List[int]):
        """Test the inverse of the permutations."""
        self.assertEqual(self.line_strategy.inverse_composed_permutation(layer_idx), expected)

    def test_apply_swap_layer(self):
        """Test that swapping a list of elements is correct."""
        list_to_swap = [0, 10, 20, 30, 40]

        swapped_list = self.line_strategy.apply_swap_layer(list_to_swap, 0)
        self.assertEqual(swapped_list, [10, 0, 30, 20, 40])
        self.assertFalse(list_to_swap == swapped_list)

        swapped_list = self.line_strategy.apply_swap_layer(list_to_swap, 1, inplace=True)
        self.assertEqual(swapped_list, [0, 20, 10, 40, 30])
        self.assertTrue(list_to_swap == swapped_list)

    def test_length(self):
        """Test the __len__ operator."""
        self.assertEqual(len(self.line_strategy), 5)

    def test_swapped_coupling_map(self):
        """Test the edges generated by a swap strategy."""
        edge_set = {(2, 0), (0, 4), (4, 1), (1, 3), (3, 1), (1, 4), (4, 0), (0, 2)}
        swapped_map = self.line_strategy.swapped_coupling_map(3)
        self.assertEqual(edge_set, set(swapped_map.get_edges()))

    def test_check_configuration(self):
        """Test that tries to initialize an invalid swap strategy."""
        with self.assertRaises(QiskitError):
            SwapStrategy(
                coupling_map=self.line_coupling_map,
                swap_layers=(((0, 1), (2, 3)), ((1, 3), (2, 4))),
            )

    def test_only_one_swap_per_qubit_per_layer(self):
        """Test that tries to initialize an invalid swap strategy."""
        message = "The 0th swap layer contains a qubit with multiple swaps."
        with self.assertRaises(QiskitError, msg=message):
            SwapStrategy(
                coupling_map=self.line_coupling_map,
                swap_layers=(((0, 1), (1, 2)),),
            )

    def test_distance_matrix(self):
        """Test the computation of the swap strategy distance matrix."""
        line_distance_matrix = np.array(
            [
                [0, 0, 3, 1, 2],
                [0, 0, 0, 2, 3],
                [3, 0, 0, 0, 1],
                [1, 2, 0, 0, 0],
                [2, 3, 1, 0, 0],
            ]
        )
        self.assertTrue(np.all(line_distance_matrix == self.line_strategy.distance_matrix))

        # Check that the distance matrix cannot be written to.
        with self.assertRaises(ValueError):
            self.line_strategy.distance_matrix[1, 2] = 5

    def test_reaches_full_connectivity(self):
        """Test to reach full connectivity on the longest line of Mumbai."""

        # The longest line on e.g. Mumbai has 21 qubits
        ll27 = list(range(21))

        ll27_map = [[ll27[idx], ll27[idx + 1]] for idx in range(len(ll27) - 1)]
        ll27_map += [[ll27[idx + 1], ll27[idx]] for idx in range(len(ll27) - 1)]

        # Create a line swap strategy on this line
        layer1 = tuple((ll27[idx], ll27[idx + 1]) for idx in range(0, len(ll27) - 1, 2))
        layer2 = tuple((ll27[idx], ll27[idx + 1]) for idx in range(1, len(ll27), 2))

        n = len(ll27)
        for n_layers, result in [
            (n - 4, False),
            (n - 3, False),
            (n - 2, True),
            (n - 1, True),
        ]:
            swap_strat_ll = []
            for idx in range(n_layers):
                if idx % 2 == 0:
                    swap_strat_ll.append(layer1)
                else:
                    swap_strat_ll.append(layer2)

            strat = SwapStrategy(CouplingMap(ll27_map), tuple(swap_strat_ll))
            self.assertEqual(len(strat.missing_couplings) == 0, result)

    def test_possible_edges(self):
        """Test that possible edges works as expected."""
        coupling_map = CouplingMap(couplinglist=[(0, 1), (1, 2), (2, 3)])

        strat = SwapStrategy(coupling_map, (((0, 1), (2, 3)), ((1, 2),)))

        expected = set()
        for i in range(4):
            for j in range(4):
                if i != j:
                    expected.add((i, j))

        self.assertSetEqual(strat.possible_edges, expected)


class TestSwapStrategyExceptions(QiskitTestCase):
    """A class to test the exceptions raised by swap strategies."""

    def test_invalid_strategy(self):
        """Test that a raise properly occurs."""

        coupling_map = CouplingMap(couplinglist=[(0, 1), (1, 2)])
        swap_layers = (((0, 1), (2, 3)), ((1, 2), (3, 4)))

        with self.assertRaises(QiskitError):
            SwapStrategy(coupling_map, swap_layers)

    def test_invalid_line_strategy(self):
        """Test the number of layers."""
        message = "Negative number -1 passed for number of swap layers."
        with self.assertRaises(ValueError, msg=message):
            SwapStrategy.from_line([0, 1, 2], -1)


class TestLineSwapStrategy(QiskitTestCase):
    """A class to test the line swap strategy."""

    def test_invalid_line(self):
        """Test that lines should be longer than 1."""
        message = "The line cannot have less than two elements, but is [1]"
        with self.assertRaises(ValueError, msg=message):
            SwapStrategy.from_line([1], 0)

    def test_full_line(self):
        """Test to reach full connectivity on a line."""

        n_nodes = 5
        strategy = SwapStrategy.from_line(list(range(n_nodes)))

        self.assertEqual(len(strategy._swap_layers), n_nodes - 2)

        # The LineSwapStrategy will apply the following permutations
        layers = [
            [0, 1, 2, 3, 4],  # coupling map
            [1, 0, 3, 2, 4],  # layer 1
            [1, 3, 0, 4, 2],  # layer 2
            [3, 1, 4, 0, 2],  # layer 3 <-- full connectivity is reached.
        ]

        for layer_idx, layer in enumerate(layers):
            expected = set()
            for idx in range(len(layer) - 1):
                expected.add((layer[idx], layer[idx + 1]))
                expected.add((layer[idx + 1], layer[idx]))

            strat_edges = strategy.swapped_coupling_map(layer_idx).get_edges()
            self.assertEqual(len(strat_edges), len(expected))
            for edge in strat_edges:
                self.assertTrue(edge in expected)

        self.assertEqual(strategy.swap_layer(0), [(0, 1), (2, 3)])
        self.assertEqual(strategy.swap_layer(1), [(1, 2), (3, 4)])
        self.assertEqual(strategy.swap_layer(2), [(0, 1), (2, 3)])

        self.assertEqual(len(strategy.missing_couplings), 0)

    def test_line(self):
        """Test the creation of a line swap strategy."""

        n_nodes = 5
        strategy = SwapStrategy.from_line(list(range(n_nodes)))

        self.assertEqual(strategy.swap_layer(0), [(0, 1), (2, 3)])
        self.assertEqual(strategy.swap_layer(1), [(1, 2), (3, 4)])
        self.assertEqual(strategy.swap_layer(2), [(0, 1), (2, 3)])

        self.assertEqual(len(strategy.missing_couplings), 0)

    def test_repr(self):
        """The the representation."""
        expected = (
            "SwapStrategy with swap layers:\n((0, 1),),\non "
            "[[0, 1], [1, 0], [1, 2], [2, 1]] coupling map."
        )
        self.assertEqual(repr(SwapStrategy.from_line([0, 1, 2])), expected)
