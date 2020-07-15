"""
A module for finding the closest-to-perfect setup in the Motorsport Manager
strategy game.

Extracts the targets from the latest saved setup file, then compares to the
full array of possible setups.
"""

from collections import namedtuple
from json import loads as json_loads
from time import sleep
from pathlib import Path
from struct import unpack
from yaml import load as yaml_load, FullLoader

from lz4 import block
from numpy import float16, linspace, median, unravel_index
from xarray import DataArray, Dataset

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


def parse_components(yaml_path: Path):
    """Generate setups using component configurations from a YAML file."""
    def component(name: str, min: float, max: float,
                  increments: float, aspect_effects: dict):
        """Generate an xarray Dataset of a component's settings and effects."""
        num_steps = int((max - min) / increments) + 1
        assert_msg = f"Settings must include a midpoint. For {name} got " \
                     f"{num_steps} steps (is even - no midpoint)."
        assert num_steps % 2 == 1, assert_msg
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

    # Ensure all aspect keys are identical.
    assert_msg = "Inconsistent aspect names across components."
    assert all(component.data_vars.keys() == component_list[0].data_vars.keys()
               for component in component_list), assert_msg

    # Combine component_list into a Dataset of all possible setups.
    # Use chunk to convert to lazy arrays - a large computation is upcoming.
    setups_by_aspect = sum(component_list).chunk("auto")

    return setups_by_aspect


def optimum_setup(setups_by_aspect: Dataset, aspect_targets: dict):
    """
    Compare every setup to the target outcomes, print out the best setup.
    """
    assert_msg = f"Incorrect type for setups_by_aspect: expected xarray " \
                 f"Dataset, got {type(setups_by_aspect)}."
    assert isinstance(setups_by_aspect, Dataset), assert_msg

    assert_msg = f"Inconsistent aspects between aspect_targets and setups_by_aspect: " \
                 f"{aspect_targets.keys()} != {setups_by_aspect.data_vars.keys()}."
    assert aspect_targets.keys() == setups_by_aspect.data_vars.keys(), assert_msg

    print("TARGET: ", aspect_targets)

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
        stepforward = unpack("i",f.read(4))[0]
        dataLengthEncoded = unpack("i",f.read(4))[0]
        data_length_decoded = unpack("i", f.read(4))[0]

        data_decompressed = block.decompress(
            f.read(),
            uncompressed_size=data_length_decoded
        )

    data_decoded = json_loads(data_decompressed.decode("utf-8", "ignore"))
    setup_stint_data = data_decoded["mSetupStintData"]
    setup_deltas = {k.replace("mDelta", ""): v
                    for k, v in setup_stint_data.items() if k.startswith("mDelta")}
    setup_output = setup_stint_data["mSetupOutput"]

    # Aspects have different names in different places.
    # Map the different names, anchored to the names in setup_deltas.
    alt_names = namedtuple("AspectAlternativeNames", ("gui", "setup_output"))
    delta_name_mapping = {
        "Aerodynamics": alt_names("Downforce", "aerodynamics"),
        "Handling": alt_names("Handling", "handling"),
        "SpeedBalance": alt_names("Speed Balance", "speedBalance")}

    # Use the name handling above to get the relevant values from dictionaries
    # and determine the target.
    aspect_targets = {}
    for aspect, delta in setup_deltas.items():
        aspect_names = delta_name_mapping[aspect]
        target = delta - setup_output[aspect_names.setup_output]
        aspect_targets[aspect_names.gui] = target

    return aspect_targets


class _NewSetupHandler(FileSystemEventHandler):
    """Watchdog event handler to analyse new setup files when they land."""
    def __init__(self, setups_by_aspect):
        self.setups_by_aspect = setups_by_aspect
        super().__init__()

    def on_created(self, event):
        source_path = Path(event.src_path)
        if source_path.suffix == ".sav":
            print(f"\nAnalysing {source_path.name}...")
            # Wait for the file to be released.
            sleep(1)
            aspect_targets = extract_targets(source_path)
            optimum_setup(self.setups_by_aspect, aspect_targets)


def main():
    """Set up a watchdog observer to analyse any new setups that come in."""
    print("Setting up...")
    setups_by_aspect = parse_components("components.yml")
    print("Components loaded.")

    setups_path = Path.home().joinpath("AppData", "LocalLow", "Playsport Games",
                                       "Motorsport Manager", "Cloud", "RaceSetups")

    handler = _NewSetupHandler(setups_by_aspect)
    observer = Observer()
    observer.schedule(handler, setups_path)

    print(f"Watching {setups_path}")
    observer.start()
    try:
        while observer.is_alive():
            # sleep(1)
            observer.join(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == "__main__":
    main()
