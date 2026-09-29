import pytest

from student_project_allocation import allocate, main


def test_everyone_gets_first_choice_when_possible():
    choices = {"a": ["P1", "P2"], "b": ["P2", "P1"], "c": ["P3"]}
    assert allocate(choices, ["P1", "P2", "P3"]) == {"a": "P1", "b": "P2", "c": "P3"}


def test_capacity_and_weights():
    # Everyone wants P1 but only one group fits: the heaviest group gets it.
    choices = {"a": ["P1", "P2"], "b": ["P1", "P2"], "c": ["P1", "P2"]}
    result = allocate(choices, ["P1", "P2"], capacity={"P1": (0, 1), "P2": (0, 3)}, weights={"c": 2})
    assert result == {"a": "P2", "b": "P2", "c": "P1"}


def test_unchosen_project_is_filled_by_min_capacity():
    choices = {"a": ["P1"], "b": ["P1"]}
    result = allocate(choices, ["P1", "P2"], capacity=(1, 1))
    assert sorted(result.values()) == ["P1", "P2"]


def test_errors():
    with pytest.raises(ValueError, match="unknown"):
        allocate({"a": ["P9"]}, ["P1"])
    with pytest.raises(ValueError, match="cannot fit"):
        allocate({"a": ["P1"]}, ["P1", "P2"], capacity=(1, 1))


def test_cli(tmp_path, capsys):
    answers = tmp_path / "answers.csv"
    answers.write_text(
        "name,first,second\nAlice & Bob,P1,P2\nCarol,P1,\nDan & Eve,P1,P2\nFrank,,P2\n", encoding="utf-8"
    )
    main([str(answers), "--choices", "first", "second", "--max", "2"])
    out, err = capsys.readouterr()
    assert out.splitlines()[0] == "name,first,second,project,rank"
    assert sorted(line.split(",")[-2] for line in out.splitlines()[1:]) == ["P1", "P1", "P2", "P2"]
    assert "Frank,,P2,P2,2" in out  # a blank choice keeps its position
    assert "choice 1: 2" in err and "choice 2: 2" in err


def unsatisfied(choices, result):
    return sum(result[g] not in choices[g] for g in choices)


def least_satisfied_project(choices, result, scores):
    total = dict.fromkeys(result.values(), 0)
    for g, p in result.items():
        if p in choices[g]:
            total[p] += scores[choices[g].index(p)]
    return min(total.values())


def test_balance_projects():
    # Everyone prefers P1; balancing gives up 1 point so that P2 is not left at 0.
    choices = {g: ["P1", "P2"] for g in "abcd"}
    assert set(allocate(choices, ["P1", "P2"], capacity=(0, 4)).values()) == {"P1"}
    result = allocate(
        choices, ["P1", "P2"], capacity=(0, 4), epsilon=1, balance_projects=True
    )
    assert sorted(result.values()) == ["P1", "P1", "P1", "P2"]
    # Balancing first, whatever the cost: two groups in each project
    result = allocate(
        choices, ["P1", "P2"], capacity=(0, 4), epsilon=float("inf"), balance_projects=True
    )
    assert sorted(result.values()) == ["P1", "P1", "P2", "P2"]


def test_fewest_unsatisfied():
    # One place per project. The best total (20) leaves b on a project it did not
    # choose; with the option every group gets one of its choices (total 12).
    choices = {"a": ["P1", "P2"], "b": ["P1", "P2"], "c": ["P2", "P3"]}
    kwargs = dict(projects=["P1", "P2", "P3"], capacity=(0, 1), scores=[10, 1])
    assert unsatisfied(choices, allocate(choices, **kwargs)) == 1
    result = allocate(choices, fewest_unsatisfied=True, **kwargs)
    assert unsatisfied(choices, result) == 0 and result["c"] == "P3"


def test_options_give_up_nothing_when_nothing_to_gain():
    # Everyone already gets a first choice: no satisfaction may be given up.
    choices = {"a": ["P1", "P2"], "b": ["P2", "P1"]}
    for option in ("fewest_unsatisfied", "balance_projects"):
        result = allocate(choices, ["P1", "P2"], capacity=(0, 2), epsilon=5, **{option: True})
        assert result == {"a": "P1", "b": "P2"}


def test_fewest_unsatisfied_comes_before_balance_projects():
    # Balancing alone leaves b outside its choices to raise the least satisfied
    # project to 3; with both options everyone is satisfied and it only reaches 2.
    choices = {
        "a": ["P2", "P1"],
        "b": ["P3"],
        "c": ["P3", "P1"],
        "d": ["P3"],
        "e": ["P3", "P1"],
        "f": ["P1", "P2"],
    }
    kwargs = dict(projects=["P1", "P2", "P3"], capacity=(2, 3), scores=[3, 1], epsilon=8)
    result = allocate(choices, balance_projects=True, **kwargs)
    assert unsatisfied(choices, result) == 1
    assert least_satisfied_project(choices, result, [3, 1]) == 3
    result = allocate(choices, fewest_unsatisfied=True, balance_projects=True, **kwargs)
    assert unsatisfied(choices, result) == 0
    assert least_satisfied_project(choices, result, [3, 1]) == 2


def test_capacities_file(tmp_path, capsys):
    answers = tmp_path / "answers.csv"
    answers.write_text("name,first,second\nA,P1,P2\nB,P1,P2\nC,P1,P2\n", encoding="utf-8")
    capacities = tmp_path / "capacities.csv"
    capacities.write_text("project,min,max\nP1,0,1\nP2,1,3\nP3,1,1\n", encoding="utf-8")
    main([str(answers), "--choices", "first", "second", "--capacities", str(capacities)])
    out, _ = capsys.readouterr()
    assert sorted(line.split(",")[-2] for line in out.splitlines()[1:]) == ["P1", "P2", "P3"]
    with pytest.raises(SystemExit, match="cannot fit"):
        capacities.write_text("project,min,max\nP1,0,1\nP2,0,1\n", encoding="utf-8")
        main([str(answers), "--choices", "first", "second", "--capacities", str(capacities)])
