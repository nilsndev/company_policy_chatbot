import pytest

from app.services.chunking import chunk_markdown, parse_document


def test_parse_document_extracts_frontmatter_and_body():
    raw = """---
title: Remote Work Policy
department: IT & Security
version: 2
supersedes: remote-work-policy-v1
references:
  - acceptable-use-policy
  - password-and-access-management-policy
---

## Purpose

Body text here.
"""
    meta, body = parse_document(raw)

    assert meta.title == "Remote Work Policy"
    assert meta.department == "IT & Security"
    assert meta.version == 2
    assert meta.supersedes == "remote-work-policy-v1"
    assert meta.references == ["acceptable-use-policy", "password-and-access-management-policy"]
    assert body.strip().startswith("## Purpose")


def test_parse_document_defaults_version_and_optional_fields():
    raw = """---
title: Company Wide Policy
---

body
"""
    meta, _ = parse_document(raw)

    assert meta.version == 1
    assert meta.department is None
    assert meta.supersedes is None
    assert meta.references == []


def test_parse_document_requires_frontmatter():
    with pytest.raises(ValueError, match="frontmatter"):
        parse_document("## Purpose\nno frontmatter here\n")


def test_parse_document_requires_title():
    with pytest.raises(ValueError, match="title"):
        parse_document("---\nversion: 1\n---\nbody\n")


def test_chunk_markdown_splits_on_headings_and_keeps_section():
    body = """## Purpose

Explains why this policy exists.

## Scope

Applies to everyone.
"""
    chunks = chunk_markdown(body)

    assert [c.section for c in chunks] == ["Purpose", "Scope"]
    assert chunks[0].content == "Explains why this policy exists."
    assert chunks[0].chunk_index == 0
    assert chunks[1].chunk_index == 1


def test_chunk_markdown_splits_oversized_section_with_overlap():
    long_section = "## Details\n\n" + " ".join(f"word{i}" for i in range(1500))
    chunks = chunk_markdown(long_section)

    assert len(chunks) > 1
    assert all(c.section == "Details" for c in chunks)
    # consecutive chunks overlap
    first_words = chunks[0].content.split()
    second_words = chunks[1].content.split()
    assert first_words[-1] != second_words[0] or set(first_words[-80:]) & set(second_words[:80])


def test_chunk_markdown_skips_empty_sections():
    body = "## Empty\n\n## Purpose\n\ncontent\n"
    chunks = chunk_markdown(body)

    assert len(chunks) == 1
    assert chunks[0].section == "Purpose"
