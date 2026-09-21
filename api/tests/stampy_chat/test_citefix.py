from stampy_chat.citefix import rewrite, Rewriter, CORE_DOCS

TP = CORE_DOCS["TP"][1]

def test_plain_code_becomes_link():
    assert rewrite("as argued [TP].") == f"as argued [TP]({TP})."

def test_numbers_untouched_and_mixed_groups_split():
    assert rewrite("x [1, 3] y") == "x [1, 3] y"
    assert rewrite("x [1, TP] y") == f"x [1] [TP]({TP}) y"

def test_unknown_codes_and_links_untouched():
    assert rewrite("[XX] [TP](already)") == "[TP](already)".join(["[XX] ", ""])

def test_streaming_split_across_tokens():
    r = Rewriter(); out = ""
    for tok in ["see ", "[", "T", "P", "]", " and [", "LL", ", 2] done"]:
        out += r.feed(tok)
    out += r.flush()
    assert out == f"see [TP]({TP}) and [LL]({CORE_DOCS['LL'][1]}) [2] done"

def test_streaming_does_not_hold_ordinary_brackets_forever():
    r = Rewriter()
    out = r.feed("[" + "a" * 60)
    assert out.startswith("[aaa")
    assert r.flush() == ""
