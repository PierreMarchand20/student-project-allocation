student-project-allocation
==========================

Allocate students, or groups of students, to projects from their ranked choices.
A group can have any size: a student working alone is just a group of one.
The allocation maximizes the total satisfaction of the groups by integer
programming, solved with HiGHS through :func:`scipy.optimize.milp`.

Installation
------------

.. code-block:: console

   pip install git+https://github.com/PierreMarchand20/student-project-allocation

Command line
------------

The package installs a command called ``spa`` (for Student-Project Allocation).

The input is a CSV file with one row per group and one column per choice, best
choice first. Blank choices are allowed and keep their position: a blank first
choice does not promote the second one. Any other columns (names, emails…) are
copied to the output unchanged.

.. code-block:: text

   name,first,second,third
   Alice & Bob,Acoustics,Robotics,Optics
   Carol,Robotics,Optics,
   Dan & Eve,Acoustics,Optics,Robotics

.. code-block:: console

   $ spa answers.csv --choices first second third -o allocation.csv
   choice 1: 3

This adds a ``project`` column and a ``rank`` column to the file. ``rank`` is
1 for a first choice and empty for a project the group did not choose. The
command also prints how many groups got each rank.

.. program:: spa

.. option:: --choices COLUMN [COLUMN ...]

   Columns holding the choices, best first. Required.

.. option:: --projects FILE

   Text file with every project, one per line. By default the projects are
   those chosen at least once. Pass this option when a project may be chosen by
   nobody but must still be filled.

.. option:: --min N, --max N

   Minimum and maximum number of groups per project. Default: the average
   number of groups per project ± 1.

.. option:: --capacities FILE

   CSV file for a different number of groups per project: the projects in the
   first column and the ``min`` and ``max`` columns. It replaces
   :option:`--projects`, :option:`--min` and :option:`--max`. The minimums
   must add up to at most the number of groups and the maximums to at least
   that number, otherwise the command stops with an error saying so.

   .. code-block:: text

      project,min,max
      Acoustics,2,4
      Robotics,1,3

.. option:: --weight COLUMN

   Column holding a weight that multiplies each group's satisfaction. Use it to
   lower the priority of late or incomplete answers, for example.

.. option:: --fewest-unsatisfied

   First give as few groups as possible a project they did not choose. The
   satisfaction, and the balance with :option:`--balance-projects`, are then
   optimized among the allocations with that fewest number of unsatisfied groups.

.. option:: --balance-projects

   Maximize the satisfaction of the least satisfied project, giving up at most
   :option:`--epsilon` of the best total satisfaction. The satisfaction of a
   project adds up over its groups, so this only makes sense for projects of
   similar sizes: a small project always has a low total.

.. option:: --epsilon EPSILON

   Total satisfaction that :option:`--balance-projects` may give up. Default: 0,
   so the balance only chooses among the allocations with the best total.
   ``inf`` balances the projects first, whatever the cost.

.. option:: -v, --verbose

   Print the log of the solver (HiGHS) on the standard error, with one titled
   section per problem solved: status, objective, gap and timing. HiGHS always
   minimizes, so a maximized objective shows as its negative. The CSV on the
   standard output is unchanged.

.. option:: --sep SEP

   CSV separator. Default: ``,``.

.. option:: -o FILE, --output FILE

   Output CSV. Default: standard output.

Choosing the options
--------------------

- **Start with the plain command.** It maximizes the total satisfaction, and
  often gives everyone one of their choices already.
- **Add** :option:`--fewest-unsatisfied` to make sure that as few groups as
  possible get a project they did not choose. It changes nothing when
  everyone can get a choice anyway, so it is safe to always use.
- **Add** :option:`--balance-projects` only when the projects have similar
  sizes, to avoid a project where most groups got a poor choice. Start with a
  small :option:`--epsilon` (a few points) and compare with the plain result:
  the counts of first, second… choices show what the balance costs.
- **Use** :option:`--weight` to give less priority to some groups, for
  example 0.75 for a late answer.
- **Use** :option:`-v` to check that every problem was solved to optimality.

.. code-block:: console

   $ spa answers.csv --choices first second third --capacities capacities.csv \
         --fewest-unsatisfied --epsilon 2 --balance-projects -o allocation.csv

Python
------

.. code-block:: python

   from student_project_allocation import allocate

   allocate(
       {"alice-bob": ["P1", "P2"], "carol": ["P2", "P1"]},
       projects=["P1", "P2", "P3"],
       capacity={"P1": (0, 1), "P2": (0, 1), "P3": (0, 1)},
       weights={"carol": 0.5},
       scores=[10, 5],
   )
   # {'alice-bob': 'P1', 'carol': 'P2'}

.. autofunction:: student_project_allocation.allocate

Mathematical formulation
------------------------

Let :math:`G` be the set of groups and :math:`P` the set of projects. The
binary variable :math:`x_{gp}` is 1 when group :math:`g` gets project
:math:`p`. The satisfaction :math:`s_{gp} = w_g \, \sigma_r` is the group's
weight :math:`w_g` times the score :math:`\sigma_r` of the rank :math:`r` at which
:math:`g` chose :math:`p`, or 0 if :math:`g` did not choose :math:`p`. With the
default scores and :math:`k` choices, :math:`\sigma_r = k - r + 1`.

The allocation solves

.. math::

   S^* = \max_{x} \sum_{g \in G} \sum_{p \in P} s_{gp} \, x_{gp}
   \quad \text{subject to} \quad
   \begin{cases}
   \sum_{p \in P} x_{gp} = 1 & \forall g \in G
      \quad \text{(one project per group)} \\
   m_p \le \sum_{g \in G} x_{gp} \le M_p & \forall p \in P
      \quad \text{(capacity of each project)} \\
   x_{gp} \in \{0, 1\}
   \end{cases}

The options add objectives, optimized one after the other. Each step keeps the
optimum of the previous ones as a constraint, so the order sets the priorities:
unsatisfied groups, then total satisfaction, then the least satisfied project
(which may cost up to :math:`\varepsilon` of the total).

**Fewest unsatisfied groups** (``fewest_unsatisfied``), solved first. A group is
unsatisfied when it gets a project it did not choose. Let :math:`u_{gp}` be 1 if
:math:`g` did not choose :math:`p` and 0 otherwise. The number of unsatisfied
groups is linear in :math:`x`, so no extra variable is needed:

.. math::

   U^* = \min_{x} \sum_{g \in G} \sum_{p \in P} u_{gp} \, x_{gp}
   \quad \text{subject to the constraints above}

The problem giving :math:`S^*` above then gets the extra constraint
:math:`\sum_{g \in G} \sum_{p \in P} u_{gp} \, x_{gp} \le U^*`, and so do the next
ones. Groups count once whatever their size, and a group that gave no choice is
always unsatisfied.

**Least satisfied project** (``balance_projects``). The minimum of the projects'
satisfactions is linearized with one more variable :math:`\theta`, bounded by
each of them:

.. math::

   \theta^* = \max_{x, \theta} \theta
   \quad \text{subject to} \quad
   \begin{cases}
   \theta \le \sum_{g \in G} s_{gp} \, x_{gp} & \forall p \in P \\
   \sum_{g \in G} \sum_{p \in P} s_{gp} \, x_{gp} \ge S^* - \varepsilon \\
   \text{the constraints above}
   \end{cases}

A last problem then maximizes the total satisfaction again with every project's
satisfaction at least :math:`\theta^*`, so no satisfaction is given up for
nothing.

Each problem is solved to optimality (a relative gap of 0 for HiGHS, instead of
its default 0.01 %), since its optimum becomes a constraint of the next ones.

Many allocations are often equally good. The solver returns one of them, so two
solvers, or two versions of one, may assign some groups differently with the
same total satisfaction.

Acknowledgements
----------------

The integer programming formulation follows explanations by Sourour Elloumi.
