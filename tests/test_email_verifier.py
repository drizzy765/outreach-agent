from tools.email_verifier import generate_email_permutations, EmailVerifier

def test_generate_email_permutations():
    perms = generate_email_permutations("Elon", "Musk", "x.com")
    assert "elon.musk@x.com" in perms
    assert "elon@x.com" in perms
    assert "emusk@x.com" in perms
    assert "elonmusk@x.com" in perms

def test_email_verifier_syntax():
    verifier = EmailVerifier()
    res = verifier.verify("invalid-email-format")
    assert res["status"] == "INVALID_SYNTAX"
