import glob
import json
import os
from pprint import pprint
import struct

from dask import array as da

from lz4 import block


class Component:
    def __init__(self, name: str, midpoint: float, breadth: float,
                 gradations: float, aspects: list):
        self.name = name

        min_value = midpoint - breadth
        max_value = midpoint + breadth
        self.settings = da.linspace(min_value, max_value, gradations)

        self.settings_aspects = \
            [self.settings * aspect / 50 for aspect in aspects]


def optimum_setup(component_list: list, aspect_targets: dict):
    assert all(isinstance(c, Component) for c in component_list)
    assert all(
        len(c.settings_aspects) == len(aspect_targets) for c in component_list)
    
    deltas_by_aspect = []
    for aspect_ix, aspect in enumerate(aspect_targets.keys()):
        settings_aspects_list = \
            [c.settings_aspects[aspect_ix] for c in component_list]
        aspect_values = da.outer(*settings_aspects_list)
        deltas_by_aspect.append(aspect_values - aspect_targets[aspect])

    deltas_total = da.add(*deltas_by_aspect)
    delta_min_ix = da.argmin(deltas_total)
    delta_min_coord = da.unravel_index(
        delta_min_ix, deltas_total.shape).compute()

    optimum_settings = []
    for component_ix, setting_ix in enumerate(delta_min_coord):
        component = component_list[component_ix]
        setting = component.settings[setting_ix]
        optimum_settings.append(setting)
    return optimum_settings


def extract_targets(file_path):
    with open(file_path, "rb") as f:
        data_length_decoded = struct.unpack("i", f.read(4))[0]

        data_decompressed = block.decompress(
            f.read(),
            uncompressed_size=data_length_decoded
        )
        data_decoded = json.loads(data_decompressed.decode("utf-8", "ignore"))
        setup_stint_data = data_decoded["mSetupStintData"]
        setup_output = setup_stint_data["mSetupOutput"]

        aspect_targets = dict.fromkeys(setup_output.keys())
        for aspect in aspect_targets.keys():
            if aspect == "speedBalance":
                # Hack fix for source mistake.
                delta_lookup = "SpeedBalance"
            else:
                delta_lookup = aspect
            delta_lookup = f"mDelta{delta_lookup}"
            target = setup_stint_data[delta_lookup] - setup_output[aspect]
            aspect_targets[aspect] = target

        return aspect_targets


def __main__():
    file_list = glob.glob(r"/home/ec2-user/python-practice/RaceSetups/*.sav")
    target_file = max(file_list, key=os.path.getctime)
    aspect_targets = extract_targets(target_file)

    pprint("TARGET", aspect_targets)

    components = [
        Component("Front Wing", 15., 5., 0.1, [-6., 1., -1.5]),
        Component("Rear Wing", 25., 5., 0.1, [-4., 1., -2.5]),
        Component("Pressure", 21., 3., 0.6, [0., 2.5, -2.5]),
        Component("Camber", -2., 2., 0.4, [0., -3.75, 3.75]),
        Component("Suspension", 50., 50., 6.25, [0., -0.05, 0.6]),
        Component("Gears", 50., 50., 6.25, [0., -0.6, 0.1])]

    optimum_list = optimum_setup(components, aspect_targets)
    optimum_dict = {}
    for component_ix, component in components:
        optimum_dict[component.name] = optimum_list[component_ix]

    pprint("OPTIMUM", optimum_dict)
