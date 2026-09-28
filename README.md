# student-project-allocation

Allocate students, or groups of students, to projects from their ranked choices.
The solver maximizes total satisfaction with integer programming (HiGHS via `scipy.optimize.milp`).
A group can have any size: a student working alone is just a group of one.

Documentation: https://pierremarchand20.github.io/student-project-allocation/

## Install

```
pip install git+<url of this repository>
```

## Command line

The package installs a command called `spa` (for Student-Project Allocation).

The input is a CSV file with one row per group and one column per choice, best choice first.
Blank choices are allowed and keep their position (a blank first choice does not promote the second one). Any other columns (names, emails…) are copied to the output unchanged.

```
name,first,second,third
Alice & Bob,Acoustics,Robotics,Optics
Carol,Robotics,Optics,
Dan & Eve,Acoustics,Optics,Robotics
```

```
spa answers.csv --choices first second third -o allocation.csv
```

This adds a `project` column and a `rank` column to the file (1 = first choice, empty = not chosen)
and prints how many groups got each rank.

Options:

- `--projects FILE`: every project, one per line. By default the projects are those chosen at least once.
  Pass this option when some project may be chosen by nobody but must still be filled.
- `--min N` / `--max N`: number of groups per project. By default it is the average ± 1.
- `--weight COLUMN`: a column that multiplies each group's satisfaction. Use it to lower the priority
  of late or incomplete answers, for example.
- `--balance-projects EPSILON`: after finding the best total satisfaction, accept losing up to `EPSILON`
  to maximize the total satisfaction of the least satisfied project.
- `--sep ';'`: the CSV separator.

A choice scores `k` for first, `k-1` for second, …, `1` for the `k`-th, and `0` if the project was not chosen.

## Python

```python
from student_project_allocation import allocate

allocate(
    {"alice-bob": ["P1", "P2"], "carol": ["P2", "P1"]},
    projects=["P1", "P2", "P3"],
    capacity={"P1": (0, 1), "P2": (0, 1), "P3": (0, 1)},  # or one (min, max) for all projects
    weights={"carol": 0.5},
    scores=[10, 5],  # custom score per rank
)
# {'alice-bob': 'P1', 'carol': 'P2'}
```

## Tests

```
pip install -e '.[test]' && pytest
```

## Acknowledgements

The integer programming formulation follows explanations by Sourour Elloumi.

## Documentation

```
pip install -e '.[docs]' && sphinx-build docs docs/_build/html
```
