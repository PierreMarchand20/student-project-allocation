"""Allocate groups of students (a student alone is a group of one) to projects
by integer programming, maximizing the total satisfaction of their ranked choices."""

import argparse
import sys
from collections import Counter

import numpy as np
import pandas as pd
from scipy import sparse
from scipy.optimize import Bounds, LinearConstraint, milp


def allocate(
    choices,
    projects,
    capacity=None,
    weights=None,
    scores=None,
    epsilon=0,
    fewest_unsatisfied=False,
    balance_projects=False,
):
    """Assign each group to exactly one project, maximizing total satisfaction.

    :param choices: ``{group: [project, ...]}``, best choice first. ``None`` marks a
        blank choice, which keeps its position.
    :param projects: every project that can be allocated, chosen or not.
    :param capacity: ``(min, max)`` number of groups per project, the same for all
        projects, or ``{project: (min, max)}``. Default: the average number of
        groups per project ± 1.
    :param weights: ``{group: weight}`` multiplying the group's satisfaction.
        Default: 1 for every group.
    :param scores: score of each rank, best first. Default: ``(k, k-1, ..., 1)``
        for ``k`` choices. A project the group did not choose scores 0.
    :param epsilon: total satisfaction that ``fewest_unsatisfied`` and
        ``balance_projects`` may give up, below the best possible total.
    :param fewest_unsatisfied: minimize the number of groups given a project they
        did not choose.
    :param balance_projects: maximize the satisfaction of the least satisfied project.
        With ``fewest_unsatisfied`` too, only among the allocations with the fewest
        unsatisfied groups.
    :returns: ``{group: project}``.
    :raises ValueError: if a choice is not in ``projects``.
    :raises RuntimeError: if no allocation satisfies the capacities.
    """
    projects = list(dict.fromkeys(projects))
    unknown = (
        {p for ranked in choices.values() for p in ranked} - set(projects) - {None}
    )
    if unknown:
        raise ValueError(f"choices contain unknown projects: {sorted(unknown)}")

    if scores is None:
        k = max(map(len, choices.values()), default=0)
        scores = range(k, 0, -1)
    scores = list(scores)
    weights = weights or {}
    if capacity is None:
        average = len(choices) // len(projects)
        capacity = (max(average - 1, 0), average + 1)
    if isinstance(capacity, tuple):
        capacity = dict.fromkeys(projects, capacity)

    groups = list(choices)
    column = {p: j for j, p in enumerate(projects)}
    satisfaction = np.zeros((len(groups), len(projects)))
    chosen = np.zeros(satisfaction.shape, dtype=bool)
    for i, g in enumerate(groups):
        for rank, p in reversed(list(enumerate(choices[g][: len(scores)]))):
            if p is not None:  # reversed: a repeated choice keeps its best rank
                satisfaction[i, column[p]] = weights.get(g, 1) * scores[rank]
                chosen[i, column[p]] = True

    # x[i, j] = 1 if group i gets project j, flattened row by row
    one_project_per_group = LinearConstraint(
        sparse.kron(sparse.eye(len(groups)), np.ones((1, len(projects)))), 1, 1
    )
    groups_per_project = LinearConstraint(
        sparse.kron(np.ones((1, len(groups))), sparse.eye(len(projects))),
        [capacity[p][0] for p in projects],
        [capacity[p][1] for p in projects],
    )
    constraints = [one_project_per_group, groups_per_project]
    total = satisfaction.ravel()
    binary = dict(integrality=1, bounds=Bounds(0, 1))
    x = _solve(-total, constraints, **binary)
    if not (fewest_unsatisfied or balance_projects):
        return _assignment(x, groups, projects)

    # Each step keeps the optimum of the previous ones as a constraint
    constraints.append(LinearConstraint(total, total @ x - epsilon - 1e-6, np.inf))

    if fewest_unsatisfied:
        unchosen = (~chosen).ravel().astype(float)
        x = _solve(unchosen, constraints, **binary)
        constraints.append(LinearConstraint(unchosen, 0, unchosen @ x + 1e-6))

    if balance_projects:
        # theta, the satisfaction of the least satisfied project, is one more variable
        n = total.size
        project_satisfaction = groups_per_project.A @ sparse.diags(total)
        theta = _solve(
            np.append(np.zeros(n), -1),
            [LinearConstraint(_with_column(c.A, 0), c.lb, c.ub) for c in constraints]
            + [LinearConstraint(_with_column(project_satisfaction, -1), 0, np.inf)],
            integrality=np.append(np.ones(n), 0),
            bounds=Bounds(0, np.append(np.ones(n), np.inf)),
        )[-1]
        constraints.append(LinearConstraint(project_satisfaction, theta - 1e-6, np.inf))

    # Finally the best total under these constraints, so none is given up for nothing
    x = _solve(-total, constraints, **binary)
    return _assignment(x, groups, projects)


def _with_column(A, value):
    A = sparse.csr_matrix(A)  # also turns a 1-D row into a matrix
    return sparse.hstack([A, np.full((A.shape[0], 1), value)])


def _assignment(x, groups, projects):
    x = x.reshape(len(groups), len(projects))
    return {g: projects[j] for g, j in zip(groups, x.argmax(axis=1))}


def _solve(c, constraints, **kwargs):
    result = milp(c, constraints=constraints, **kwargs)
    if not result.success:
        raise RuntimeError(f"no allocation found ({result.message}), check capacities")
    return result.x


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Allocate projects to students or groups of students from a CSV "
        "file with one row per group and one column per ranked choice."
    )
    parser.add_argument("answers", help="CSV file, one row per group")
    parser.add_argument(
        "--choices",
        nargs="+",
        required=True,
        metavar="COLUMN",
        help="columns holding the choices, best first",
    )
    parser.add_argument(
        "--projects",
        metavar="FILE",
        help="text file with one project per line (default: every project chosen at least once)",
    )
    parser.add_argument("--min", type=int, help="minimum number of groups per project")
    parser.add_argument("--max", type=int, help="maximum number of groups per project")
    parser.add_argument(
        "--weight", metavar="COLUMN", help="column holding each group's weight"
    )
    parser.add_argument(
        "--epsilon",
        type=float,
        default=0,
        help="total satisfaction the options below may give up (default: 0)",
    )
    parser.add_argument(
        "--fewest-unsatisfied",
        action="store_true",
        help="give as few groups as possible a project they did not choose",
    )
    parser.add_argument(
        "--balance-projects",
        action="store_true",
        help="raise the satisfaction of the least satisfied project "
        "(after --fewest-unsatisfied if both are given)",
    )
    parser.add_argument("--sep", default=",", help="CSV separator (default: ,)")
    parser.add_argument(
        "-o", "--output", default="-", help="output CSV (default: stdout)"
    )
    args = parser.parse_args(argv)

    data = pd.read_csv(args.answers, sep=args.sep, encoding="utf-8-sig")
    choices = {
        i: [p if pd.notna(p) and str(p).strip() else None for p in row]
        for i, row in zip(data.index, data[args.choices].itertuples(index=False))
    }
    if args.projects:
        with open(args.projects, encoding="utf-8") as f:
            projects = [line.strip() for line in f if line.strip()]
    else:
        projects = sorted({p for ranked in choices.values() for p in ranked} - {None})

    capacity = None
    if args.min is not None or args.max is not None:
        average = len(choices) // len(projects)
        capacity = (
            args.min if args.min is not None else max(average - 1, 0),
            args.max if args.max is not None else average + 1,
        )
    weights = data[args.weight].to_dict() if args.weight else None

    try:
        allocation = allocate(
            choices,
            projects,
            capacity,
            weights,
            epsilon=args.epsilon,
            fewest_unsatisfied=args.fewest_unsatisfied,
            balance_projects=args.balance_projects,
        )
    except (ValueError, RuntimeError) as e:
        sys.exit(f"error: {e}")

    data["project"] = pd.Series(allocation)
    data["rank"] = pd.Series(
        {i: choices[i].index(p) + 1 for i, p in allocation.items() if p in choices[i]},
        dtype="Int64",
    )
    output = sys.stdout if args.output == "-" else args.output
    data.to_csv(output, index=False, lineterminator="\n")  # os.linesep doubles \r on Windows stdout

    ranks = Counter(data["rank"].fillna(0))
    for rank in sorted(ranks, key=lambda r: r or float("inf")):
        label = f"choice {rank}" if rank else "not chosen"
        print(f"{label}: {ranks[rank]}", file=sys.stderr)


if __name__ == "__main__":
    main()
