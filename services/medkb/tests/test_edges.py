from medkb.graph.edges import should_grade, should_rewrite, should_check_grounded


def test_should_grade_regular_skips():
    state = {"config": {"strategy": "regular"}}
    assert should_grade(state) == "generate"


def test_should_grade_crag_grades():
    state = {"config": {"strategy": "crag"}}
    assert should_grade(state) == "grade_docs"


def test_should_rewrite_good_generates():
    state = {"doc_grade": "good", "rewrite_count": 0, "config": {"max_retries": 2}}
    assert should_rewrite(state) == "generate"


def test_should_rewrite_bad_rewrites():
    state = {"doc_grade": "bad", "rewrite_count": 0, "config": {"max_retries": 2}}
    assert should_rewrite(state) == "rewrite_query"


def test_should_rewrite_max_retries_generates():
    state = {"doc_grade": "bad", "rewrite_count": 2, "config": {"max_retries": 2}}
    assert should_rewrite(state) == "generate"


def test_should_check_grounded_regular_skips():
    state = {"config": {"strategy": "regular"}}
    assert should_check_grounded(state) == "format_cite"


def test_should_check_grounded_srag_checks():
    state = {"config": {"strategy": "srag"}}
    assert should_check_grounded(state) == "check_grounded"
