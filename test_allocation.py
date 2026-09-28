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
    with pytest.raises(RuntimeError, match="no allocation"):
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


def test_balance_projects():
    # Everyone prefers P1; balancing gives up 1 point so that P2 is not left at 0.
    choices = {g: ["P1", "P2"] for g in "abcd"}
    assert set(allocate(choices, ["P1", "P2"], capacity=(0, 4)).values()) == {"P1"}
    result = allocate(choices, ["P1", "P2"], capacity=(0, 4), balance_projects=1)
    assert sorted(result.values()) == ["P1", "P1", "P1", "P2"]
