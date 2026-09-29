# student-project-allocation

Allocate students, or groups of students, to projects from their ranked choices.
The solver maximizes total satisfaction with integer programming (HiGHS via `scipy.optimize.milp`).
A group can have any size: a student working alone is just a group of one.

Documentation: https://pierremarchand20.github.io/student-project-allocation/

## Install

```
pip install git+https://github.com/PierreMarchand20/student-project-allocation
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
- `--capacities FILE`: a CSV with the projects in the first column and `min` and `max` columns, for a
  different number of groups per project. It replaces `--projects`, `--min` and `--max`.
  The minimums must add up to at most the number of groups and the maximums to at least that number:

  ```
  project,min,max
  Acoustics,2,4
  Robotics,1,3
  ```
- `--weight COLUMN`: a column that multiplies each group's satisfaction. Use it to lower the priority
  of late or incomplete answers, for example.
- `--fewest-unsatisfied`: first give as few groups as possible a project they did not choose;
  everything else is then optimized with that fewest number of unsatisfied groups.
- `--balance-projects`: maximize the total satisfaction of the least satisfied project. Project
  totals add up over their groups, so this only makes sense for projects of similar sizes.
- `--epsilon EPSILON`: total satisfaction `--balance-projects` may give up (default 0);
  `inf` balances the projects first, whatever the cost.
- `-v` / `--verbose`: print the solver (HiGHS) log on stderr, one section per problem solved.
- `--sep ';'`: the CSV separator.

For example, with a capacity per project, as few groups as possible outside their choices, and a
balance between projects costing at most 2 points of total satisfaction:

```
spa answers.csv --choices first second third --capacities capacities.csv \
    --fewest-unsatisfied --epsilon 2 --balance-projects -o allocation.csv
```

The documentation explains when to use each option.

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
