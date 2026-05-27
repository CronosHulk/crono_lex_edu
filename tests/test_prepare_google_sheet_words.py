from __future__ import annotations

import json
from pathlib import Path

from word_base.prepare_google_sheet_words import prepare_dataset


def test_prepare_dataset_handles_headers_swapped_columns_and_exact_duplicates(tmp_path: Path) -> None:
    input_csv = tmp_path / "sheet.csv"
    output_dir = tmp_path / "prepared"
    input_csv.write_text(
        "\n".join(
            [
                'id,word,pos,lvl,tags,trans_uk,trans_ru,trans_pl,phonetic_us,phonetic_uk,examples_json,synonyms_ids',
                '1,accept,v.,A2,actions,приймати,принимать,akceptować,/əkˈsept/,/əkˈsept/,"[""Please accept it.""]",2',
                '2,acquiesce,v.,C2,"behavior, formal",погоджуватися,уступать,przystać,/ˌækwiˈes/,/ˌækwiˈes/,"[""He acquiesced.""]",1',
                'id,word,pos,lvl,tags,trans_uk,trans_ru,trans_pl,phonetic_us,phonetic_uk,examples_json,synonyms_ids',
                '3,acceptable,B1,adj.,quality,прийнятний,приемлемый,akceptowalny,/əkˈseptəbl/,/əkˈseptəbl/,"[""An acceptable result.""]",',
                '4,accept,v.,A2,actions,приймати,принимать,akceptować,/əkˈsept/,/əkˈsept/,"[""Please accept it.""]",2',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    bundle = prepare_dataset(input_csv, output_dir)

    entries = bundle["entries"]
    assert len(entries) == 3
    acceptable = next(entry for entry in entries if entry["word"] == "acceptable")
    assert acceptable["parts_of_speech"] == ["adjective"]
    assert acceptable["level_code"] == "B1"

    report = bundle["validation_report"]
    assert report["stats"]["exact_duplicates_removed_count"] == 1
    assert report["stats"]["prepared_entry_count"] == 3
    assert len(report["issues_by_kind"]["repeated_header"]) == 1
    assert len(report["issues_by_kind"]["swapped_pos_level"]) == 1

    clean_words_json = json.loads((output_dir / "clean_words.json").read_text(encoding="utf-8"))
    assert len(clean_words_json["entries"]) == 3


def test_prepare_dataset_handles_phrasal_header_and_missing_reverse_synonym(tmp_path: Path) -> None:
    input_csv = tmp_path / "sheet.csv"
    output_dir = tmp_path / "prepared"
    input_csv.write_text(
        "\n".join(
            [
                'id,word,pos,lvl,tags,trans_uk,trans_ru,trans_pl,phonetic_us,phonetic_uk,examples_json,synonyms_ids',
                '11,abuse,n.,B2,"law, behavior",зловживання,злоупотребление,nadużycie,/əˈbjuːs/,/əˈbjuːs/,"[""Abuse of power.""]",5005',
                '5005,exploitation,n.,C2,"law, business","експлуатація, визиск","эксплуатация, использование",wyzysk,/ˌeksplɔɪˈteɪʃn/,/ˌeksplɔɪˈteɪʃn/,"[""Child exploitation.""]",',
                'id,word,phrasal verb,lvl,tags,trans_uk,trans_ru,trans_pl,phonetic_us,examples_json,synonyms_ids,',
                '41,bring back,phrasal verb,A2,general,повертати,возвращать,zwracać,/brɪŋ bæk/,"[""Bring back my book.""]",,',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    bundle = prepare_dataset(input_csv, output_dir)

    phrasal = next(entry for entry in bundle["entries"] if entry["source_ref"] == "phrasal_verb:41")
    assert phrasal["parts_of_speech"] == ["phrasal verb"]
    assert phrasal["entry_type"] == "phrasal_verb"
    assert phrasal["transcription"] == "/brɪŋ bæk/"

    report = bundle["validation_report"]
    assert len(report["issues_by_kind"]["asymmetric_synonym_link"]) == 1


def test_prepare_dataset_removes_linguistically_random_synonym_pair(tmp_path: Path) -> None:
    input_csv = tmp_path / "sheet.csv"
    output_dir = tmp_path / "prepared"
    input_csv.write_text(
        "\n".join(
            [
                'id,word,pos,lvl,tags,trans_uk,trans_ru,trans_pl,phonetic_us,phonetic_uk,examples_json,synonyms_ids',
                '1,apple,n.,A1,food,яблуко,яблоко,jabłko,/ˈæp.əl/,/ˈæp.əl/,"[""An apple a day.""]",2',
                '2,compile,v.,B1,it,компілювати,компилировать,kompilować,/kəmˈpaɪl/,/kəmˈpaɪl/,"[""Compile the source code.""]",1',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    bundle = prepare_dataset(input_csv, output_dir)

    entries = {entry["source_ref"]: entry for entry in bundle["entries"]}
    assert entries["core:1"]["synonym_source_refs"] == []
    assert entries["core:2"]["synonym_source_refs"] == []

    cleanup = bundle["synonym_cleanup_report"]
    assert cleanup["kept_pair_count"] == 0
    assert cleanup["removed_pair_count"] == 1
    assert cleanup["removed_pairs"][0]["reason"] == "part_of_speech_mismatch"


def test_prepare_dataset_normalizes_translation_separators(tmp_path: Path) -> None:
    input_csv = tmp_path / "sheet.csv"
    output_dir = tmp_path / "prepared"
    input_csv.write_text(
        "\n".join(
            [
                'id,word,pos,lvl,tags,trans_uk,trans_ru,trans_pl,phonetic_us,phonetic_uk,examples_json,synonyms_ids',
                '1,else,adv.,A1,logic,"ще, крім того; інакше","еще, кроме того; иначе","jeszcze|inaczej",/els/,/els/,"[""What else did you buy?""]",',
                '2,ride,v.,A1,movement,їздити верхи / на велосипеді,ездить верхом / на велосипеде,jechać,/raɪd/,/raɪd/,"[""I learned to ride a bike when I was six.""]",',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    bundle = prepare_dataset(input_csv, output_dir)
    entries = {entry["word"]: entry for entry in bundle["entries"]}

    assert entries["else"]["translation_uk"] == "ще, крім того, інакше"
    assert entries["else"]["translation_ru"] == "еще, кроме того, иначе"
    assert entries["else"]["translation_pl"] == "jeszcze, inaczej"
    assert entries["ride"]["translation_uk"] == "їздити верхи, на велосипеді"
    assert entries["ride"]["translation_ru"] == "ездить верхом, на велосипеде"


def test_prepare_dataset_builds_unique_entry_keys_for_same_word_pos_and_translation(tmp_path: Path) -> None:
    input_csv = tmp_path / "sheet.csv"
    output_dir = tmp_path / "prepared"
    input_csv.write_text(
        "\n".join(
            [
                "id,word,phrasal verb,lvl,tags,trans_uk,trans_ru,trans_pl,phonetic_us,examples_json,synonyms_ids,",
                '42,call back,phrasal verb,A2,general,передзвонити,перезвонить,oddzwonić,/kɔːl bæk/,"[""I will call you back later.""]",,',
                '423,call back,phrasal verb,A1,general,передзвонити,перезвонить,oddzwonić,/kɔːl bæk/,"[""Please call me back tomorrow.""]",,',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    bundle = prepare_dataset(input_csv, output_dir)

    entry_keys = {entry["source_ref"]: entry["entry_key"] for entry in bundle["entries"]}
    assert entry_keys["phrasal_verb:42"] == "call-back__phrasal verb__entry__phrasal-verb-42"
    assert entry_keys["phrasal_verb:423"] == "call-back__phrasal verb__entry__phrasal-verb-423"
    assert len(set(entry_keys.values())) == 2


def test_prepare_dataset_uniquifies_colliding_source_refs_and_keeps_raw_source_refs(tmp_path: Path) -> None:
    input_csv = tmp_path / "sheet.csv"
    output_dir = tmp_path / "prepared"
    input_csv.write_text(
        "\n".join(
            [
                "id,word,pos,lvl,tags,trans_uk,trans_ru,trans_pl,phonetic_us,phonetic_uk,examples_json,synonyms_ids",
                '30,across,prep.,A1,general,через,через,przez,/əˈkrɔːs/,/əˈkrɔːs/,"[""Walk across the bridge.""]",',
                "id,word,pos,lvl,tags,trans_uk,trans_ru,trans_pl,phonetic_us,phonetic_uk,examples_json,synonyms_ids",
                '30,pick up,phrasal verb,B1,general,"підбирати, забирати","подбирать, забирать",odebrać,/pɪk ʌp/,/pɪk ʌp/,"[""Please pick up the package.""]",',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    bundle = prepare_dataset(input_csv, output_dir)

    source_refs = {entry["word"]: entry["source_ref"] for entry in bundle["entries"]}
    assert source_refs["across"].startswith("core:30__")
    assert source_refs["pick up"].startswith("core:30__")
    assert source_refs["across"] != source_refs["pick up"]

    raw_refs = {entry["word"]: entry["source_raw_refs"] for entry in bundle["entries"]}
    assert raw_refs["across"] == [source_refs["across"], "core:30"]
    assert raw_refs["pick up"] == [source_refs["pick up"], "core:30"]

    assert bundle["validation_report"]["duplicate_source_refs"] == []


def test_prepare_dataset_excludes_non_ascii_words(tmp_path: Path) -> None:
    input_csv = tmp_path / "sheet.csv"
    output_dir = tmp_path / "prepared"
    input_csv.write_text(
        "\n".join(
            [
                "id,word,pos,lvl,tags,trans_uk,trans_ru,trans_pl,phonetic_us,phonetic_uk,examples_json,synonyms_ids",
                '1,ennuyé,adj.,C2,formal,знуджений,скучающий,znudzony,/ˌɒnwiˈeɪ/,/ˌɒnwiˈeɪ/,"[""He looked ennuyé during the lecture.""]",',
                '2,bored,adj.,A2,general,нудьгуючий,скучающий,znudzony,/bɔːrd/,/bɔːrd/,"[""He looked bored during the lecture.""]",',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    bundle = prepare_dataset(input_csv, output_dir)

    assert [entry["word"] for entry in bundle["entries"]] == ["bored"]
    assert len(bundle["validation_report"]["issues_by_kind"]["non_ascii_word"]) == 1
