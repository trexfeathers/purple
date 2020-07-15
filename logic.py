"""
A module for finding the closest-to-perfect setup in the Motorsport Manager
strategy game.

Extracts the targets from the latest saved setup file, then compares to the
full array of possible setups.
"""

from json import loads as json_loads
from pathlib import Path
from struct import unpack
from yaml import load as yaml_load, FullLoader

from lz4 import block
from numpy import float16, linspace, median, unravel_index
from xarray import DataArray, Dataset

from os.path import getmtime


def parse_components(yaml_path: Path):
    """Extract component configurations from a YAML file."""
    with open(yaml_path) as file:
        content = yaml_load(file, Loader=FullLoader)

    component_list = []
    for name, info in content.items():
        settings = info["settings"]
        component_list.append(component(name=name,
                                        min=settings["min"],
                                        max=settings["max"],
                                        increments=settings["increments"],
                                        aspect_effects=info["aspect_effects"]))

    return component_list


def component(name: str, min: float, max: float,
              increments: float, aspect_effects: dict):
    """Generate an xarray Dataset of a component's settings and effects."""
    num_steps = int((max - min) / increments) + 1
    assert num_steps % 2 == 1, f"Settings must include a midpoint. For " \
                               f"{name} got {num_steps} steps " \
                               f"(even - no midpoint)."
    settings = linspace(min, max, num_steps, dtype=float16)
    midpoint = median(settings)

    aspect_dict = {}
    for aspect, effect in aspect_effects.items():
        # Convert effect to effect-per-unit change.
        effect = effect / (max - min)
        # Convert effect from % to a scale of -1.0 to +1.0.
        effect /= 50

        # Corresponding aspect value for each setting value.
        aspect_array = (settings - midpoint) * effect

        aspect_dict[aspect] = DataArray(name=aspect,
                                        data=aspect_array,
                                        dims=name,
                                        coords={name: settings})

    # Combine the DataArrays for each aspect into a single dataset.
    return Dataset(aspect_dict)


def optimum_setup(component_list: list, aspect_targets: dict):
    """
    Generate all possible setups from a list of components, compare each
    to the target outcomes, print out the best setup.
    """
    assert all(isinstance(component, Dataset) for component in component_list)
    # Ensure all aspect keys are identical.
    assert all(component.data_vars.keys() == aspect_targets.keys()
               for component in component_list)

    print("TARGET: ", aspect_targets)

    # Use chunk to convert to lazy arrays - a large computation is upcoming.
    setups_by_aspect = sum(component_list).chunk("auto")
    for aspect, target in aspect_targets.items():
        setups_by_aspect[aspect] = abs(setups_by_aspect[aspect] - target)
    setups_overall = setups_by_aspect.to_array(dim="delta").sum("delta")

    optimum_index = setups_overall.argmin().data.compute()
    optimum_address = unravel_index(optimum_index, setups_overall.shape)
    optimum_setup = setups_overall[optimum_address]

    print(optimum_setup.coords)


def extract_targets(file_path):
    """Extract the targets from a specified saved setup file."""
    with open(file_path, "rb") as f:
        stepforward = unpack("i",f.read(4))[0];
        dataLengthEncoded = unpack("i",f.read(4))[0];
        data_length_decoded = unpack("i", f.read(4))[0]

        data_decompressed = block.decompress(
            f.read(),
            uncompressed_size=data_length_decoded
        )

    data_decoded = json_loads(data_decompressed.decode("utf-8", "ignore"))
    setup_stint_data = data_decoded["mSetupStintData"]
    setup_output = setup_stint_data["mSetupOutput"]

    aspect_targets = dict.fromkeys(setup_output.keys())
    aspect_targets.pop("$version")
    for aspect in aspect_targets.keys():
        if aspect == "speedBalance":
            # Hack fix for source mistake.
            delta_lookup = "SpeedBalance"
        else:
            delta_lookup = aspect.title()
        delta_lookup = f"mDelta{delta_lookup}"
        target = setup_stint_data[delta_lookup] - setup_output[aspect]
        aspect_targets[aspect] = target

    return aspect_targets


def main():
    components = parse_components("components.yml")

    setups_path = Path.home().joinpath("AppData", "LocalLow", "Playsport Games",
                                       "Motorsport Manager", "Cloud", "RaceSetups")
    file_list = setups_path.glob("*.sav")
    target_file = max(file_list, key=getmtime)
    aspect_targets = extract_targets(target_file)

    optimum_setup(components, aspect_targets)


if __name__ == "__main__":
    main()