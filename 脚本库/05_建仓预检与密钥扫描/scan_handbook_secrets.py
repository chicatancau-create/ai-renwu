import os, re, json, sys

ROOT = r"G:\AIrenwu\本地AI使用手册"

PATTERNS = [
    ("AWS_AKID",        re.compile(r"AKIA[0-9A-Z]{16}")),
    ("GitHub_PAT",      re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}")),
    ("OpenAI_key",      re.compile(r"sk-[A-Za-z0-9_\-]{20,}")),
    ("Anthropic_key",   re.compile(r"sk-ant-[A-Za-z0-9_\-]{20,}")),
    ("GitCode_token",   re.compile(r"\b[0-9a-f]{32}\b")),
    ("Slack_token",     re.compile(r"xox[baprs]-[A-Za-z0-9\-]{10,}")),
    ("PrivateKeyBlock", re.compile(r"-----BEGIN (RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----")),
    ("Bearer_literal",  re.compile(r"Bearer\s+[A-Za-z0-9._\-]{25,}")),
    ("PasswordAssign",  re.compile(r"(?i)(password|passwd|pwd|secret|api[_-]?key|token)\s*[:=]\s*['\"]?[A-Za-z0-9!@#$%^&*._\-]{12,}")),
]

hits = []
nfiles = 0
total = 0
for dirpath, dirnames, filenames in os.walk(ROOT):
    for fn in filenames:
        p = os.path.join(dirpath, fn)
        try:
            b = open(p, "rb").read()
        except OSError as e:
            hits.append({"file": p, "error": str(e)})
            continue
        total += len(b)
        nfiles += 1
        if b"\x00" in b[:4096]:
            continue
        try:
            t = b.decode("utf-8", "replace")
        except Exception:
            continue
        for name, rx in PATTERNS:
            for m in rx.finditer(t):
                s = max(0, m.start() - 40)
                ctx = t[s:m.end() + 40].replace("\n", " ")
                hits.append({"file": os.path.relpath(p, ROOT), "rule": name, "match": m.group(0)[:16] + "…", "ctx": ctx[:120]})

print("files=%d bytes=%d" % (nfiles, total))
print("hits=%d" % len(hits))
for h in hits:
    print(json.dumps(h, ensure_ascii=False))
