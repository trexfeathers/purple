import numba
import numpy as np
import typing

@numba.njit
def find_closest_setup():
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
        def decimal_steps(component: typing.List[float, float, float]):
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
        def component_effects(component_percent_effects: typing.List
                              [float, float, float, float, float, float]):
            return [i / 100 for i in component_percent_effects]

        return [component_effects(quality) for quality in qualities]

    component_effects_collated = collate_component_effects()

    ###########################################################################

    def iterate_setups(coords: typing.List[int, int, int, int, int, int] = None,
                       coord_advance: int = None):
        if coords is None:
            coords = [0, 0, 0, 0, 0, 0]
        for i in decimal_steps_collated[0]:
            for j in i:
                print(j)
            if iterate_index < decimal_steps_collated[0].size:
                iterate_setups(iterate_index + 1)
