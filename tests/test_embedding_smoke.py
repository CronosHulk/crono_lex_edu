from __future__ import annotations

from app.embedding_smoke import run_embedding_smoke


def test_run_embedding_smoke_returns_dimensions(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.embedding_smoke.ensure_user_import_embedding",
        lambda **kwargs: ([0.1, 0.2, 0.3], {"status": "ok", "model": kwargs["model_name"], "device": kwargs["device"]}, None),
    )

    payload = run_embedding_smoke()

    assert payload["status"] == "ok"
    assert payload["embedding_dimensions"] == 3


def test_run_embedding_smoke_raises_on_failure(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.embedding_smoke.ensure_user_import_embedding",
        lambda **kwargs: (None, {"status": "error"}, "model failed"),
    )

    try:
        run_embedding_smoke()
    except RuntimeError as error:
        assert "model failed" in str(error)
    else:  # pragma: no cover
        raise AssertionError("RuntimeError was expected")
