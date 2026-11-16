import copy
import json
import pytest
from agent import groq_brain as gb

ARTICLE = {"title": "Best Draft Stoppers", "url": "https://example.com/a/", "description": "d",
           "headings": [{"level": "h2", "text": "How to choose"}], "text": "word " * 400}
BRAND = {"tone": ["helpful"]}


class Resp:
    def __init__(self, code=200, content="", text="", headers=None):
        self.status_code, self.headers = code, headers or {}
        self._content = content
        self.text = text or content

    def json(self):
        return {"choices": [{"message": {"content": self._content}}]}


def pins_json(first, k):
    return json.dumps({"pins": [{"number": first + i, "angle": "a", "headline": f"Headline {first + i}",
                                 "subheadline": "", "title": f"Title {first + i}", "description": "Desc",
                                 "keywords": [], "hashtags": [], "board": "B", "visual_direction": "v",
                                 "image_prompt": "p", "claims_used": []} for i in range(k)]})


ANALYSIS = json.dumps({"article_analysis": {"topic": "draft stoppers", "audience": "homeowners"},
                       "keyword_suggestions": {"note": "n", "phrases": ["door draft stopper"]},
                       "board_suggestions": ["Home Tips"]})


def fake_server(monkeypatch, replies):
    sent = []

    def post(url, headers=None, json=None, timeout=0):
        sent.append(copy.deepcopy(json))
        return replies.pop(0)

    monkeypatch.setattr(gb.requests, "post", post)
    monkeypatch.setattr(gb.time, "sleep", lambda s: None)
    return sent


def test_full_plan_in_batches(monkeypatch):
    sent = fake_server(monkeypatch, [Resp(content=ANALYSIS), Resp(content=pins_json(1, 5)),
                                     Resp(content=pins_json(6, 5))])
    plan = gb.analyze_and_plan("key", "m", ARTICLE, BRAND, 10)
    assert [p["number"] for p in plan["pins"]] == list(range(1, 11))
    assert len(sent) == 3 and all(s["max_tokens"] <= 3500 for s in sent)
    assert "Headline 1" in sent[2]["messages"][1]["content"]          # later batches see earlier headlines


def test_reply_with_text_around_json_and_wrong_count_is_retried(monkeypatch):
    wrapped = "Sure! ```json\n" + pins_json(1, 3) + "\n```"
    sent = fake_server(monkeypatch, [Resp(content=ANALYSIS), Resp(content=wrapped), Resp(content=pins_json(1, 5))])
    plan = gb.analyze_and_plan("key", "m", ARTICLE, BRAND, 5)
    assert len(plan["pins"]) == 5 and len(sent) == 3


def test_rate_limit_is_waited_out(monkeypatch):
    msg = "Rate limit reached on tokens per minute (TPM): Limit 8000, Used 6873, Requested 2596. Please try again in 11.0s."
    sent = fake_server(monkeypatch, [Resp(429, text=msg)] * 12 + [Resp(content=ANALYSIS), Resp(content=pins_json(1, 5))])
    plan = gb.analyze_and_plan("key", "m", ARTICLE, BRAND, 5)
    assert len(plan["pins"]) == 5 and len(sent) == 14


def test_daily_limit_and_oversized_request_fail_clearly(monkeypatch):
    fake_server(monkeypatch, [Resp(429, text="tokens per day (TPD): Limit 200000")])
    with pytest.raises(gb.GroqError, match="daily limit"):
        gb.analyze_and_plan("key", "m", ARTICLE, BRAND, 5)
    fake_server(monkeypatch, [Resp(413, text="Request too large on tokens per minute (TPM): Limit 6000, Requested 9000.")])
    with pytest.raises(gb.GroqError, match="ARTICLE_CHAR_LIMIT"):
        gb.analyze_and_plan("key", "m", ARTICLE, BRAND, 5)


def test_output_token_limit_lowers_max_tokens(monkeypatch):
    msg = "Request too large on output tokens per minute (OTPM): Limit 1000, Requested 2500."
    sent = fake_server(monkeypatch, [Resp(429, text=msg), Resp(content=ANALYSIS), Resp(content=pins_json(1, 5))])
    gb.analyze_and_plan("key", "m", ARTICLE, BRAND, 5)
    assert sent[1]["max_tokens"] < 1000 <= sent[0]["max_tokens"]


def test_json_mode_rejected_falls_back_to_plain_prompt(monkeypatch):
    sent = fake_server(monkeypatch, [Resp(400, text="response_format is not supported for this model"),
                                     Resp(content=ANALYSIS), Resp(content=pins_json(1, 5))])
    gb.analyze_and_plan("key", "m", ARTICLE, BRAND, 5)
    assert "response_format" in sent[0] and "response_format" not in sent[1]


def test_missing_key_is_reported():
    with pytest.raises(ValueError, match="GROQ_API_KEY"):
        gb.analyze_and_plan("", "m", ARTICLE, BRAND, 5)
