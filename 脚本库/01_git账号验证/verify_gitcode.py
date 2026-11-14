# verify_gitcode.py - verify stored GitCode/AtomGit credentials against GitCode API.
# Reads Windows Credential Manager via Win32 CredReadW (read-only).
# HARD RULE: the secret itself is NEVER printed, logged, or written anywhere.
import ctypes
import ctypes.wintypes as wt
import json
import urllib.request
import urllib.error


class CREDENTIALW(ctypes.Structure):
    _fields_ = [
        ("Flags", wt.DWORD),
        ("Type", wt.DWORD),
        ("TargetName", wt.LPWSTR),
        ("Comment", wt.LPWSTR),
        ("LastWritten", wt.FILETIME),
        ("CredentialBlobSize", wt.DWORD),
        ("CredentialBlob", ctypes.c_void_p),
        ("Persist", wt.DWORD),
        ("AttributeCount", wt.DWORD),
        ("Attributes", ctypes.c_void_p),
        ("TargetAlias", wt.LPWSTR),
        ("UserName", wt.LPWSTR),
    ]


adv = ctypes.windll.advapi32
adv.CredReadW.argtypes = [wt.LPCWSTR, wt.DWORD, wt.DWORD,
                          ctypes.POINTER(ctypes.POINTER(CREDENTIALW))]
adv.CredReadW.restype = wt.BOOL


def read_cred(target):
    p = ctypes.POINTER(CREDENTIALW)()
    if not adv.CredReadW(target, 1, 0, ctypes.byref(p)):
        return None
    try:
        c = p.contents
        raw = ctypes.string_at(c.CredentialBlob, c.CredentialBlobSize)
        return {"user": c.UserName, "secret": raw.decode("utf-16-le")}
    finally:
        adv.CredFree(ctypes.cast(p, ctypes.c_void_p))


def http(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, r.read(4000).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read(1000).decode("utf-8", "replace")
    except Exception as e:
        # token is only ever in headers, never in the URL, so this is safe to print
        return None, type(e).__name__ + ": " + str(e)


# (name, url, auth style)
ENDPOINTS = [
    ("gitlab-v4", "https://gitcode.com/api/v4/user", "private-token"),
    ("gitee-v5", "https://api.gitcode.com/api/v5/user", "bearer"),
    ("gitcode-v5", "https://gitcode.com/api/v5/user", "bearer"),
]

print("== anonymous endpoint probes (no credentials sent) ==")
usable = []
for name, url, style in ENDPOINTS:
    st, body = http(url)
    print(name, url, "->", st, body[:200].replace("\n", " "))
    if st in (401, 403):
        usable.append((name, url, style))

print()
print("== stored credentials (secret never printed) ==")
creds = {}
for target in ("git:https://gitcode.com", "git:https://atomgit.com"):
    c = read_cred(target)
    if c is None:
        print(target, "-> NOT FOUND")
    else:
        print(target, "-> user =", c["user"], ", secret length =", len(c["secret"]))
        creds[target] = c

print()
print("== authenticated API check (who does the server say this token belongs to) ==")
if not usable:
    print("no usable API endpoint discovered; token validity NOT verified")
for target, c in creds.items():
    for name, url, style in usable:
        if style == "private-token":
            headers = {"PRIVATE-TOKEN": c["secret"]}
        else:
            headers = {"Authorization": "Bearer " + c["secret"]}
        st, body = http(url, headers)
        summary = body[:300]
        if st == 200:
            try:
                j = json.loads(body)
                summary = json.dumps(
                    {k: j.get(k) for k in ("id", "username", "login", "name") if k in j},
                    ensure_ascii=False)
            except Exception:
                pass
        print(target, "via", name, "->", st, summary.replace("\n", " "))
print("== DONE ==")
