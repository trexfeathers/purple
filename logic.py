import glob
import json
import os
from pprint import pprint
import struct

from dask import array as da
from numpy import float16

from lz4 import block


class Component:
    def __init__(self, name: str, midpoint: float, breadth: float,
                 gradations: float, aspects: list):
        self.name = name
        self.midpoint = midpoint
        self.aspects = aspects

        self.min_value = midpoint - breadth
        self.max_value = midpoint + breadth
        self.steps_max = int((2 * breadth) / gradations) + 1

    def generate_settings(self, decimation: int):
        decimation = min(decimation, self.steps_max)
        settings = da.linspace(self.min_value, self.max_value, self.steps_max,
                               dtype=float16)
        settings = settings[::int(decimation)]
        settings_aspects = [(settings - self.midpoint) * aspect / 50 for
                            aspect in self.aspects]

        return settings, settings_aspects


class DecimatedComponent:
    def __init__(self, Component, decimation):
        self.name = Component.name
        self.settings, self.settings_aspects = \
            Component.generate_settings(decimation)


def optimum_setup(component_list: list, aspect_targets: dict):
    def decimated_optimum(decimated_component_list: list):
        assert all(
            isinstance(d, DecimatedComponent) for d in decimated_component_list)

        deltas_by_aspect = []
        for aspect_ix, aspect in enumerate(aspect_targets.keys()):
            settings_aspects_list = [
                d.settings_aspects[aspect_ix] for d in decimated_component_list]
            aspect_values_mesh = da.array(da.meshgrid(*settings_aspects_list))
            aspect_values = da.sum(aspect_values_mesh, axis=0)
            deltas_by_aspect.append(da.absolute(
                aspect_values - aspect_targets[aspect]))

        deltas_total = da.add(*deltas_by_aspect)
        print(f"combinations: {deltas_total.size} ...")
        delta_min_ix = da.argmin(deltas_total)
        delta_min_coord = da.unravel_index(delta_min_ix, deltas_total.shape)

        optimum_dict = {}
        for component_ix, setting_ix in enumerate(delta_min_coord):
            component = decimated_component_list[component_ix]
            setting = component.settings[setting_ix].compute()
            optimum_dict[component.name] = setting
        print(optimum_dict)

    assert all(isinstance(c, Component) for c in component_list)
    assert all(
        len(c.aspects) == len(aspect_targets) for c in component_list)

    decimation = 64
    while decimation >= 1:
        decimated_component_list =\
            [DecimatedComponent(c, decimation) for c in component_list]
        decimated_optimum(decimated_component_list)
        decimation /= 2

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


if __name__ == "__main__":
    aspect_targets = {"DF": 0.0, "H": 0.0, "S": 0.0}
    # file_list = glob.glob(r"/home/ec2-user/python-practice/RaceSetups/*.sav")
    # target_file = max(file_list, key=os.path.getctime)
    # aspect_targets = extract_targets(target_file)

    pprint(["TARGET", aspect_targets])

    components = [
        Component("Front Wing", 15., 5., 0.1, [-6., 1., -1.5]),
        Component("Rear Wing", 25., 5., 0.1, [-4., 1., -2.5]),
        Component("Pressure", 21., 3., 0.6, [0., 2.5, -2.5]),
        Component("Camber", -2., 2., 0.4, [0., -3.75, 3.75]),
        Component("Suspension", 50., 50., 6.25, [0., -0.05, 0.6]),
        Component("Gears", 50., 50., 6.25, [0., -0.6, 0.1])]

    optimum_setup(components, aspect_targets)
