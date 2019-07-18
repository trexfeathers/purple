import numba
import numpy as np
import typing
import random
import time


@numba.njit
def collate_decimal_steps():
    # [midpoint, breadth, gradations]
    components = [
        [15., 5., 0.4],
        [25., 5., 0.4],
        [21., 3., 0.6],
        [2., 2., 0.4],
        [50., 50., 6.25],
        [50., 50., 6.25]
    ]

    def decimal_steps(component):
        return np.linspace(-0.5, 0.5,
                           int((component[1] * 2) / component[2]) + 1)

    return_list = []
    for component in components:
        return_list.append(decimal_steps(component))
    return return_list
    # return [decimal_steps(component) for component in components]


@numba.njit
def collate_component_effects():
    # [1 element for each component]
    qualities = [
        [-60., -40., 0., 0., 0., 0.],
        [10., 10., 25. / 3., -3.75, -5., -60.],
        [-15., -25., -25. / 3., 3.75, 60., 10.]
    ]

    def component_effects(component_percent_effects):
        return [i / 100 for i in component_percent_effects]

    return_list = []
    for quality in qualities:
        return_list.append(component_effects(quality))
    return return_list
    # return [component_effects(quality) for quality in qualities]


@numba.njit
def iterate_setups(setup,
                   setup_best,
                   setup_delta_best,
                   level,
                   max_levels,
                   target,
                   decimal_steps_collated,
                   component_effects_collated):

    # target = [0., 0., 0.]
    # level = len(setup)
    for step in decimal_steps_collated[level]:
        if len(setup) <= level:
            setup.append(step)
        else:
            setup[level] = step
        if level < max_levels - 1:
            pass
            # setup_best, setup_delta_best = iterate_setups(setup,
            #                                               setup_best,
            #                                               setup_delta_best,
            #                                               level + 1,
            #                                               max_levels)
        else:
            setup_outcome = []
            for quality in component_effects_collated:
                for i in range(level + 1):
                    setup_outcome.append(setup[i] * quality[i])

            setup_delta = 0
            for i in range(len(target)):
                setup_delta += setup_outcome[i] - target[i]

            if abs(setup_delta) < abs(setup_delta_best):
                setup_best = setup.copy()
                setup_delta_best = setup_delta
                # print(setup_best)

    return setup_best, setup_delta_best


@numba.njit
def find_closest_setup(target):
    # target = [t1, t2, t3]
    # target_length = len(target)

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

    decimal_steps_collated = collate_decimal_steps()

    ###########################################################################

    component_effects_collated = collate_component_effects()

    ###########################################################################

    components_count = len(decimal_steps_collated)
    setup_best, setup_delta_best = \
        iterate_setups(setup=[0],
                       setup_best=[0] * components_count,
                       # setup_delta_best=float(len(target)),
                       setup_delta_best=3.,
                       level=0,
                       max_levels=components_count,
                       target=target,
                       decimal_steps_collated=decimal_steps_collated,
                       component_effects_collated=component_effects_collated)

    print(setup_best)


if __name__ == '__main__':
    st = time.time()
    target_setup = [random.random() - 0.5] * 3
    print('target:  ', target_setup)
    find_closest_setup(target_setup)
    elapsed = time.time() - st
    print(str(elapsed))