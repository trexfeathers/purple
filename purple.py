"""
Module for finding the closest-to-perfect setup in the
`Motorsport Manager <http://www.motorsportmanager.com/>`_ strategy game.

Extracts the targets from the latest saved setup file, then compares to the
full array of possible setups.

Key concepts
************
* Aspect: a value between -1 and 1 that has a target value per driver per race
  weekend. There are several aspects of a setup - the challenge is to
  simultaneously get every aspect close to its target value.

* Component: an array of settings with a corresponding impact on each
  **aspect**. There are several components to adjust, each with varying and
  conflicting impacts on the setup **aspects**.
"""

from collections import namedtuple, OrderedDict
from json import loads as json_loads
from time import sleep
from pathlib import Path
from struct import unpack
from yaml import load as yaml_load, FullLoader

from lz4 import block
from numpy import float16, linspace, median, prod, unravel_index
from xarray import DataArray, Dataset

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


def parse_components(yaml_path: Path) -> Dataset:
    """
    Generate setups using component configurations from a YAML file.

    :param yaml_path: location of the YAML file containing component info.
    :return: xarray Dataset containing settings for each component
    (coordinates) and their effects on aspects (data_vars).
    """

    def component(
        name: str, min: float, max: float, increments: float, aspect_effects: dict
    ) -> Dataset:
        """
        Generate an xarray Dataset of a component's settings and effects.

        :param name: component name.
        :param min: minimum setting for component.
        :param max: maximum setting for component.
        :param increments: setting increments for component.
        :param aspect_effects: dictionary: {aspect: percent change from
        increasing component setting from min to max}
        :return: xarray Dataset with the component settings (coordinate) and
        the corresponding effects on aspects (data_vars).
        """
        num_steps = int((max - min) / increments) + 1
        assert_msg = (
            f"Settings must include a midpoint. For {name} got "
            f"{num_steps} steps (is even - no midpoint)."
        )
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

            aspect_dict[aspect] = DataArray(
                name=aspect, data=aspect_array, dims=name, coords={name: settings}
            )

        # Combine the DataArrays for each aspect into a single dataset.
        return Dataset(aspect_dict)

    with open(yaml_path) as file:
        content = yaml_load(file, Loader=FullLoader)

    component_list = []
    for name, info in content.items():
        settings = info["settings"]
        component_list.append(
            component(
                name=name,
                min=settings["min"],
                max=settings["max"],
                increments=settings["increments"],
                aspect_effects=info["aspect_effects"],
            )
        )

    # Ensure all aspect keys are identical.
    assert_msg = "Inconsistent aspect names across components."
    assert all(
        component.data_vars.keys() == component_list[0].data_vars.keys()
        for component in component_list
    ), assert_msg

    # Combine component_list into a Dataset of all possible setups.
    # Use chunk to make the array lazy, since it could now be very large.
    setups_by_aspect = sum(component_list).chunk("auto")

    return setups_by_aspect


def optimum_setup(setups_by_aspect: Dataset, aspect_targets: dict):
    """
    Compare every setup to the target outcomes, print out the best setup.

    :param setups_by_aspect: xarray Dataset containing settings for each
    component (coordinates) and their effects on aspects (data_vars).
    :param aspect_targets: dictionary of the target value for each aspect.
    """
    assert_msg = (
        f"Incorrect type for setups_by_aspect: expected xarray "
        f"Dataset, got {type(setups_by_aspect)}."
    )
    assert isinstance(setups_by_aspect, Dataset), assert_msg

    assert_msg = (
        f"Inconsistent aspects between aspect_targets and setups_by_aspect: "
        f"{aspect_targets.keys()} != {setups_by_aspect.data_vars.keys()}."
    )
    assert aspect_targets.keys() == setups_by_aspect.data_vars.keys(), assert_msg

    setups_by_aspect = setups_by_aspect.copy(deep=True)

    # Print target in similar format to xarray coords.
    col_width = max(len(key) for key in aspect_targets.keys()) + 2  # padding
    aspect_targets_str = [
        "".join([aspect.ljust(col_width), str(target)])
        for aspect, target in aspect_targets.items()
    ]
    print("\n\t".join(["TARGET:", *aspect_targets_str]))

    # Calculate the absolute delta between aspect value and target for
    # every setup, then combine the aspect deltas into an overall delta.
    for aspect, target in aspect_targets.items():
        setups_by_aspect[aspect] = abs(setups_by_aspect[aspect] - target)
    setups_overall = setups_by_aspect.to_array(dim="delta").sum("delta")

    print(
        f"{prod(setups_overall.shape):,} setup combinations. "
        f"Analysing against target ..."
    )

    # Find the address of the setup with the smallest delta. This will be a long
    # computation if the array is large.
    optimum_index = setups_overall.argmin().data.compute()
    optimum_address = unravel_index(optimum_index, setups_overall.shape)
    optimum_setup = setups_overall[optimum_address].compute()

    # Piggyback on xarray coords string representation, modifying for our purposes.
    output = str(optimum_setup.coords).replace("Coordinates", "OPTIMUM")
    output += f"\n\t(delta: {optimum_setup.data})"
    print(output)


def extract_targets(file_path: Path) -> dict:
    """
    Extract the targets from a specified saved setup file.

    :param file_path: location of the saved setup file.
    :return: dictionary of the target value for each aspect.
    """
    print(f"Reading '{file_path.name}' ...")

    # Read the desired content from the file, which is compressed in the lz4 format.
    with open(file_path, "rb") as f:
        step_forward = unpack("i", f.read(4))[0]
        data_length_encoded = unpack("i", f.read(4))[0]
        data_length_decoded = unpack("i", f.read(4))[0]

        data_decompressed = block.decompress(
            f.read(), uncompressed_size=data_length_decoded
        )

    # Get desired dictionaries from the file content.
    data_decoded = json_loads(data_decompressed.decode("utf-8", "ignore"))
    setup_stint_data = data_decoded["mSetupStintData"]
    # All deltas in setup_stint_data begin with "mDelta", which we look for
    # but then remove from the string when storing the data.
    setup_deltas = {
        k.replace("mDelta", ""): v
        for k, v in setup_stint_data.items()
        if k.startswith("mDelta")
    }
    setup_output = setup_stint_data["mSetupOutput"]

    # Aspects have different names in different places.
    # Map the different names, anchored to the names in setup_deltas.
    # (Sorted in same way as is displayed in GUI).
    alt_names = namedtuple("AspectAlternativeNames", ("gui", "setup_output"))
    delta_name_mapping = OrderedDict(
        [
            ("Aerodynamics", alt_names("Downforce", "aerodynamics")),
            ("Handling", alt_names("Handling", "handling")),
            ("SpeedBalance", alt_names("Speed Balance", "speedBalance")),
        ]
    )

    # Use the name handling above to get the relevant values from dictionaries
    # and determine the target.
    aspect_targets = OrderedDict()
    for aspect, aspect_names in delta_name_mapping.items():
        delta = setup_deltas[aspect]
        target = setup_output[aspect_names.setup_output] + delta
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
            print("\n")
            # Wait for the file to be released.
            sleep(1)
            aspect_targets = extract_targets(source_path)
            optimum_setup(self.setups_by_aspect, aspect_targets)


def main():
    """Set up a :class:`_NewSetupHandler` to analyse any new setups that come in."""
    print("Setting up ...")
    setups_by_aspect = parse_components(
        Path(__file__).parent.joinpath("components.yml")
    )
    print("Components loaded.")

    setups_path = Path.home().joinpath(
        "AppData",
        "LocalLow",
        "Playsport Games",
        "Motorsport Manager",
        "Cloud",
        "RaceSetups",
    )

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
