import glob
import json
import os
import struct

from dask import array as da

from lz4 import block


class Component:
    def __init__(self, name: str, midpoint: float, breadth: float,
                 gradations: float, effects: tuple):
        self.name = name

        min_value = midpoint - breadth
        max_value = midpoint + breadth
        self.settings = da.linspace(min_value, max_value, gradations)

        assert len(effects) == 3
        effects = (round(effect / 50, 5) for effect in effects)
        self.effects = effects


effect_names = ["Downforce", "Handling", "Speed"]


components = [
    Component("Front Wing", 15., 5., 0.1, (-6., 1., -1.5)),
    Component("Rear Wing", 25., 5., 0.1, (-4., 1., -2.5)),
    Component("Pressure", 21., 3., 0.6, (0., 2.5, -2.5)),
    Component("Camber", -2., 2., 0.4, (0., -3.75, 3.75)),
    Component("Suspension", 50., 50., 6.25, (0., -0.05, 0.6)),
    Component("Gears", 50., 50., 6.25, (0., -0.6, 0.1))]


def optimum_setup():
    file_list = glob.glob(r"/home/ec2-user/python-practice/RaceSetups/*.sav")
    target_file = max(file_list, key=os.path.getctime)

    with open(target_file, "rb") as f:
        data_length_decoded = struct.unpack("i", f.read(4))[0]

        data_decompressed = block.decompress(
            f.read(),
            uncompressed_size=data_length_decoded
        )
        data_decoded = json.loads(data_decompressed.decode("utf-8", "ignore"))
        setup_stint_data = data_decoded["mSetupStintData"]
        setup_output = setup_stint_data["mSetupOutput"]

        downforce = setup_stint_data["mDeltaAerodynamics"] -\
            setup_output["aerodynamics"]
        handling = setup_stint_data["mDeltaHandling"] -\
            setup_output["handling"]
        speed = setup_stint_data["mDeltaSpeedBalance"] -\
            setup_output["speedBalance"]

        print("TARGET  Downforce: %f, Handling: %f, Speed: %f" %
              (downforce, handling, speed))
