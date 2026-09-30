from app.pii import scrub_text


def test_scrub_email() -> None:
    out = scrub_text("Email me at student@vinuni.edu.vn")
    assert "student@" not in out
    assert "REDACTED_EMAIL" in out


def test_scrub_common_vietnamese_phone_formats() -> None:
    phone_numbers = (
        "0901234567",
        "090 123 4567",
        "090.123.4567",
        "090-123-4567",
        "+84 90 123 4567",
    )

    for phone_number in phone_numbers:
        out = scrub_text(f"Contact: {phone_number}")
        assert phone_number not in out
        assert "REDACTED_PHONE_VN" in out


def test_scrub_cccd() -> None:
    assert scrub_text("CCCD: 012345678901") == "CCCD: [REDACTED_CCCD]"


def test_scrub_credit_card_formats() -> None:
    for card in ("4111111111111111", "4111 1111 1111 1111", "4111-1111-1111-1111"):
        assert scrub_text(f"Card: {card}") == "Card: [REDACTED_CREDIT_CARD]"


def test_scrubber_runs_before_file_and_console_rendering(monkeypatch, tmp_path, capsys):
    import json
    from app import logging_config
    from structlog.contextvars import clear_contextvars

    clear_contextvars()
    path = tmp_path / "safe.jsonl"
    monkeypatch.setattr(logging_config, "LOG_PATH", path)
    logging_config.configure_logging()
    logging_config.get_logger().info(
        "Contact student@example.com",
        session_id="student@example.com",
        payload={"nested": [{"cccd": "012345678901", "card": "4111 1111 1111 1111"}]},
    )
    saved = path.read_text()
    console = capsys.readouterr().out
    for output in (saved, console):
        assert "student@example.com" not in output
        assert "012345678901" not in output
        assert "4111 1111 1111 1111" not in output
        assert "[REDACTED_EMAIL]" in output
        assert "[REDACTED_CCCD]" in output
        assert "[REDACTED_CREDIT_CARD]" in output
    assert json.loads(saved)["session_id"] == "[REDACTED_EMAIL]"
