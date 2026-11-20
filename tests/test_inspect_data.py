from rag_mia_data.inspect_data import inspect_dataset


def test_inspection_reports_fields_counts_hashes_and_broken_links(tiny_config):
    result = inspect_dataset(tiny_config)
    files = {item["path"]: item for item in result["files"]}
    collection = files["DataSet/T2Ranking/collection.tsv"]

    assert collection["fields"] == ["pid", "text"]
    assert collection["record_count"] == 3
    assert len(collection["sha256"]) == 64
    assert result["relations"]["qrels_unknown_query_ids"] == 1
    assert result["relations"]["qrels_unknown_document_ids"] == 1
    assert result["raw_data_modified"] is False
    assert (tiny_config.manifests_dir / "source_dataset_manifest.json").is_file()
    assert (tiny_config.reports_dir / "source_dataset_profile.md").is_file()
