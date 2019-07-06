import glob
import json
import numpy as np
import os
import struct
import typing
import itertools
import random
import time

import numba


class Component:
    def __init__(self, midpoint: float, breadth: float, gradations: float):
        self.midpoint = midpoint
        self.breadth = breadth
        self.gradations = gradations

        self.decimal_steps = \
            np.linspace(-0.5, 0.5,
                        int((self.breadth * 2) / self.gradations) + 1)


class Quality:
    def __init__(self, component_percent_effects:
                 typing.Tuple[float, float, float, float, float, float]):
        self.component_effects = \
            np.asarray([i / 100 for i in component_percent_effects])


class Engineer:
    def __init__(self):
        self.components_index = (
            'Front Wing',
            'Rear Wing',
            'Pressure',
            'Camber',
            'Gears'
            'Suspension',
        )

        self.qualities_index = (
            'Downforce',
            'Handling',
            'Speed'
        )

        self.components = (
            Component(15, 5, 0.4),
            Component(25, 5, 0.4),
            Component(21, 3, 0.6),
            Component(2, 2, 0.4),
            Component(50, 50, 6.25),
            Component(50, 50, 6.25)
        )
        self.decimal_steps_collated = \
            [c.decimal_steps for c in self.components]

        self.qualities = (
            Quality((-60, -40, 0, 0, 0, 0)),
            Quality((10, 10, 25 / 3, -3.75, -5, -60)),
            Quality((-15, -25, -25 / 3, 3.75, 60, 10))
        )
        self.component_effects_collated = np.stack(
            [q.component_effects for q in self.qualities])

    def setup_delta(
            self,
            setup: np.ndarray(shape=[6]),
            target: np.ndarray(shape=[3])
    ):
        setup_outcome = np.sum(
            np.multiply(setup, self.component_effects_collated), 1)
        return np.sum(np.subtract(setup_outcome, target))

    def find_closest_setup(self, target: np.ndarray(shape=[3])):
        target = np.asarray(target)
        setup_base = np.zeros(6)
        setup_best = [setup_base, setup_delta(setup_base, target, self.component_effects_collated)]

        for setup in cartesian(self.decimal_steps_collated):
            target_delta = setup_delta(setup, target, self.component_effects_collated)
            if abs(target_delta) < abs(setup_best[1]):
                setup_best = [setup, target_delta]
                # print(setup_best)

        print(setup_best)


@numba.njit
def setup_delta(
        setup: np.ndarray(shape=[6]),
        target: np.ndarray(shape=[3]),
        component_effects_collated
):
    setup_outcome = np.sum(
        np.multiply(setup, component_effects_collated), 1)
    return np.sum(np.subtract(setup_outcome, target))


def cartesian(arrays_input, out=None):
    """
    Generate a cartesian product of input arrays.

    Parameters
    ----------
    arrays_input : list of array-like
        1-D arrays to form the cartesian product of.
    out : ndarray
        Array to place the cartesian product in.

    Returns
    -------
    out : ndarray
        2-D array of shape (M, len(arrays)) containing cartesian products
        formed of input arrays.

    Examples
    --------
    >>> cartesian(([1, 2, 3], [4, 5], [6, 7]))
    array([[1, 4, 6],
           [1, 4, 7],
           [1, 5, 6],
           [1, 5, 7],
           [2, 4, 6],
           [2, 4, 7],
           [2, 5, 6],
           [2, 5, 7],
           [3, 4, 6],
           [3, 4, 7],
           [3, 5, 6],
           [3, 5, 7]])

    """

    arrays = [x for x in arrays_input]

    n = np.prod([x.size for x in arrays])
    if out is None:
        out = np.zeros((n, len(arrays)))

    m = int(n / arrays[0].size)
    out[:, 0] = np.repeat(arrays[0], m)
    if arrays[1:]:
        cartesian(arrays[1:], out=out[0:m, 1:])
        for j in range(1, arrays[0].size):
            out[j*m:(j+1)*m, 1:] = out[0:m, 1:]
    return out


if __name__ == '__main__':
    st = time.time()
    target_setup = [random.random() - 0.5 for i in range(3)]
    print('target:  ', target_setup)
    engineer = Engineer()
    engineer.find_closest_setup(target_setup)
    elapsed = time.time() - st
    print(str(elapsed))

