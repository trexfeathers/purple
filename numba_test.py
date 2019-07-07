import numba
import numpy as np
import typing
import random
import time


# @numba.njit
def find_closest_setup(target: list):
    target_length = len(target)

    components_index = (
        'Front Wing',
        'Rear Wing',
        'Pressure',
        'Camber',
        'Gears'
        'Suspension',
    )

    qualities_index = (
        'Downforce',
        'Handling',
        'Speed'
    )

    ###########################################################################

    # [midpoint, breadth, gradations]
    components = [
        [15, 5, 0.4],
        [25, 5, 0.4],
        [21, 3, 0.6],
        [2, 2, 0.4],
        [50, 50, 6.25],
        [50, 50, 6.25]
    ]

    def collate_decimal_steps():
        def decimal_steps(component: list):
            return np.linspace(-0.5, 0.5,
                               int((component[1] * 2) / component[2]) + 1)

        return [decimal_steps(component) for component in components]

    decimal_steps_collated = collate_decimal_steps()

    ###########################################################################

    # [1 element for each component]
    qualities = [
        [-60, -40, 0, 0, 0, 0],
        [10, 10, 25 / 3, -3.75, -5, -60],
        [-15, -25, -25 / 3, 3.75, 60, 10]
    ]

    def collate_component_effects():
        def component_effects(component_percent_effects: list):
            return [i / 100 for i in component_percent_effects]

        return [component_effects(quality) for quality in qualities]

    component_effects_collated = collate_component_effects()

    ###########################################################################

    def iterate_setups(setup: list,
                       setup_best: list,
                       setup_delta_best: float,
                       level: int,
                       max_levels: int):

        # level = len(setup)
        for step in decimal_steps_collated[level]:
            if len(setup) <= level:
                setup.append(step)
            else:
                setup[level] = step
            if level < max_levels - 1:
                setup_best, setup_delta_best = iterate_setups(setup,
                                                              setup_best,
                                                              setup_delta_best,
                                                              level + 1,
                                                              max_levels)
            else:
                setup_outcome = [
                    sum([setup[i] * quality[i] for i in range(level + 1)])
                    for quality in component_effects_collated
                ]
                setup_delta = sum([
                    setup_outcome[i] - target[i]
                    for i in range(target_length)
                ])
                if setup_delta < setup_delta_best:
                    setup_best = setup
                    setup_delta_best = setup_delta

        return setup_best, setup_delta_best

    components_count = len(decimal_steps_collated)
    iterate_setups(setup=[],
                   setup_best=[0] * components_count,
                   setup_delta_best=float(target_length),
                   level=0,
                   max_levels=components_count)


if __name__ == '__main__':
    st = time.time()
    target_setup = [random.random() - 0.5] * 3
    print('target:  ', target_setup)
    find_closest_setup(target_setup)
    elapsed = time.time() - st
    print(str(elapsed))