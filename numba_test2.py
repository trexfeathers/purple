import numpy as np
import random

import numba


@numba.njit
def find_closest_setup(target: tuple):
    # [midpoint, breadth, gradations]
    components = [
        [15., 5., 0.4],
        [25., 5., 0.4],
        [21., 3., 0.6],
        [2., 2., 0.4],
        [50., 50., 6.25],
        [50., 50., 6.25]
    ]
    decimal_steps_collated = []
    for component in components:
        decimal_steps_collated.append(
            np.linspace(-0.5, 0.5, int((component[1] * 2) / component[2]) + 1)
        )

    # [1 element for each component]
    qualities = [
        [-60., -40., 0., 0., 0., 0.],
        [10., 10., 25. / 3., -3.75, -5., -60.],
        [-15., -25., -25. / 3., 3.75, 60., 10.]
    ]
    component_effects_collated = []
    for quality in qualities:
        component_effects_collated.append(
            [i / 100 for i in quality]
        )

    component_count = len(components)
    setup_ix = [0] * component_count
    shape = [len(component) for component in decimal_steps_collated]

    descend = False
    component_ix = len(shape) - 1
    combinations = 1
    for component_ix in shape:
        combinations = component_ix * combinations
    for step in range(combinations):



    # for component_ix in range(component_count):
    #     for step_ix in decimal_steps_collated[component_ix]:



if __name__ == '__main__':
    target_setup = []
    for i in range(3):
        target_setup.append(random.random() - 0.5)
    find_closest_setup(tuple(target_setup))
