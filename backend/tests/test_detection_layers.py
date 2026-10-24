from privacyforge.detection.custom_rules import CustomRule, dry_run_rule
from privacyforge.detection.dataset_aware import DatasetAwareDetector


def test_student_id_column_flagged():
    det = DatasetAwareDetector()
    vals = [f"STU-2026-{i:05d}" for i in range(50)]
    f = det.detect_column("student_id", vals)
    assert f and f[0].entity_type == "STUDENT_ID"


def test_unknown_high_cardinality_shape_flagged_for_review():
    det = DatasetAwareDetector()
    vals = [f"AB-{i:04d}" for i in range(40)]
    f = det.detect_column("mystery", vals)
    assert f and f[0].review_needed


def test_low_cardinality_category_not_flagged():
    det = DatasetAwareDetector()
    vals = ["red", "blue", "red", "blue"] * 10
    f = det.detect_column("color", vals)
    assert f == []


def test_custom_regex_rule_dry_run():
    rule = CustomRule(id="r1", entity_type="BADGE", pattern=r"BDG-\d{4}")
    matches = dry_run_rule(rule, "employee BDG-1234 entered")
    assert len(matches) == 1
