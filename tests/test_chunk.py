# SPDX-License-Identifier: MIT
# Copyright (c) 2021 The Pybricks Authors


from pybricksdev.tools import chunk


def test_chunk():
    expected = [
        [1, 2, 3],
        [4, 5, 6],
        [7, 8, 9],
        [10],
    ]

    count = 0

    for c, e in zip(chunk([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 3), expected):
        assert c == e
        count += 1

    assert count == len(expected)
