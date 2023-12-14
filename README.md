[![Purple](purple_logo.svg)]()

[![Black](https://img.shields.io/badge/code/style-black-000000.svg)](https://github.com/psf/black)

# Purple
A toy project for up-skilling Python - finds the optimal setup for a driver's
race weekend in the PC game [Motorsport Manager](http://www.motorsportmanager.com/).

Once I had played the setup minigame a few times, I could clearly see the rule
mechanics behind it, which spoiled my enjoyment:

## The rule mechanics

The game pre-determines the ideal setup for a driver's weekend. This ideal setup is
made up of 3 aspects, each of which is a float between `-1` and `1`:

- `Downforce`
- `Handling`
- `Speed Balance`

To get each of these 3 numbers as close as possible to their ideal target, the player
uses 6 input sliders. Each of these sliders represents a setting for a different car
component:

- `Front Wing`
- `Rear Wing`
- `Pressure`
- `Camber`
- `Gearing`
- `Suspension`

The effect of each slider on `Downforce`/`Handling`/`Speed Balance` varies in direction 
and intensity. E.g. `Pressure` has no effect on `Downforce`, but increasing `Pressure`
will slightly decrease the `Speed Balance` number. Each slider also moves in different
increments. See [`components.yml`](components.yml) for the more details.

## The frustration

Knowing the above, I now know that there are over 300 million combinations of settings,
each of which producing a different combination of the 3 aspects. With the different
setting affects and increments, this is designed to provide some fun trying to reach
the best compromise. For me, knowing that there was one answer that is closer to ideal
than all the others, and that this could be predicted numerically, just became a source
of frustration.

## Solutions

Enumerating all 300 million possible combinations - with nested loops or using
[`itertools`](https://docs.python.org/3/library/itertools.html) - took too much
computation and was therefore unworkably slow (the setup minigame occurs multiple
times during one play session).

I explored using NumPy, but this needed to represent all 300 million combinations
at once and therefore hit memory limitations. Since [NumPy](https://numpy.org/) does 
not label dimensions, I also found it very difficult to work out the correct 
incantations to link aspect combinations to their original settings.

Learning to use [Dask Array}(https://docs.dask.org/en/stable/array.html) potentially 
solved the memory problem, but the difficulty with unlabelled arrays remained.

The solution finally became apparent when I attended my first 
[SciPy conference](https://conference.scipy.org/) (2020, virtual attendance), which
included a workshop on learning [Xarray](https://docs.xarray.dev/en/stable/).
Xarray is all about labelled arrays, and can operate via Dask. It was very intuitive
for this self-contained problem, and I was able to put together the solution that
evening. I could represent each combination of settings as a 6-dimensional `Dataset`
of the difference from the ideal, 3 times over - once for each aspect. I could then
look for the minimum value across all 3, and access the settings as the dimension
labels. See [`purple.py`](purple.py). On a mid-range laptop the operation takes less
than 30 seconds - well within a tolerable wait.
