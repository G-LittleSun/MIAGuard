import yaml

from rag_mia_data.io_utils import (
    iter_tsv,
    read_jsonl,
    sha256_file,
    write_jsonl_atomic,
    write_yaml_atomic,
)


def test_iter_tsv_preserves_dash_header(tmp_path):
    path = tmp_path / "qrels.tsv"
    path.write_text("qid\t-\tpid\trel\n1\t0\t9\t3\n", encoding="utf-8")

    assert list(iter_tsv(path)) == [
        {"qid": "1", "-": "0", "pid": "9", "rel": "3"}
    ]


def test_atomic_jsonl_round_trip_and_hash(tmp_path):
    path = tmp_path / "rows.jsonl"

    write_jsonl_atomic(path, [{"text": "中文"}, {"text": "第二行"}])

    assert list(read_jsonl(path)) == [{"text": "中文"}, {"text": "第二行"}]
    assert len(sha256_file(path)) == 64
    assert not path.with_suffix(path.suffix + ".tmp").exists()


def test_iter_tsv_supports_text_larger_than_csv_default_limit(tmp_path):
    path = tmp_path / "collection.tsv"
    long_text = "中" * 131_073
    path.write_text(f"pid\ttext\n1\t{long_text}\n", encoding="utf-8")

    assert list(iter_tsv(path))[0]["text"] == long_text


def test_atomic_yaml_round_trip(tmp_path):
    path = tmp_path / "resolved.yaml"
    value = {"profile": "smoke", "include": ["ag_news"], "enabled": True}

    write_yaml_atomic(path, value)

    assert yaml.safe_load(path.read_text(encoding="utf-8")) == value
    assert not path.with_suffix(path.suffix + ".tmp").exists()
