"""Create the GitCode mirror repo and push. Secret is read from Windows Credential
Manager and never printed. Usage: gitcode_push.py <repo-name> <local-path> [--create-only]
"""
import ctypes
import ctypes.wintypes as wt
import json
import os
import ssl
import subprocess
import sys
import urllib.error
import urllib.request

sys.stdout.reconfigure(errors="replace")
GIT = r"D:\Git\cmd\git.exe"
NS = "zhoumoyukuai"
API = "https://gitcode.com/api/v5"


def cred(target="git:https://gitcode.com"):
    class CREDENTIAL(ctypes.Structure):
        _fields_ = [("Flags", wt.DWORD), ("Type", wt.DWORD),
                    ("TargetName", wt.LPWSTR), ("Comment", wt.LPWSTR),
                    ("LastWritten", wt.FILETIME), ("CredentialBlobSize", wt.DWORD),
                    ("CredentialBlob", ctypes.POINTER(ctypes.c_char)),
                    ("Persist", wt.DWORD), ("AttributeCount", wt.DWORD),
                    ("Attributes", ctypes.c_void_p), ("TargetAlias", wt.LPWSTR),
                    ("UserName", wt.LPWSTR)]
    adv = ctypes.windll.advapi32
    p = ctypes.POINTER(CREDENTIAL)()
    if not adv.CredReadW(target, 1, 0, ctypes.byref(p)):
        raise SystemExit("no stored credential for " + target)
    c = p.contents
    blob = ctypes.string_at(c.CredentialBlob, c.CredentialBlobSize)
    adv.CredFree(p)
    try:
        return blob.decode("utf-16-le")
    except UnicodeDecodeError:
        return blob.decode("utf-8", "replace")


def api(path, token, data=None, method=None):
    hdr = {"User-Agent": "skill-backup", "Accept": "application/json",
           "Authorization": "Bearer " + token}
    body = None
    if data is not None:
        body = json.dumps(data).encode()
        hdr["Content-Type"] = "application/json"
    r = urllib.request.Request(API + path, data=body, headers=hdr, method=method)
    try:
        with urllib.request.urlopen(r, timeout=60, context=ssl.create_default_context()) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return None, "%s: %s" % (type(e).__name__, e)


def git(args, cwd=None, timeout=1800):
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
    r = subprocess.run([GIT] + args, cwd=cwd, capture_output=True, text=True,
                       timeout=timeout, env=env, encoding="utf-8", errors="replace")
    return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()


name = sys.argv[1]
path = sys.argv[2]
token = cred()
print("=== GitCode repo %s/%s ===" % (NS, name))
st, body = api("/repos/%s/%s" % (NS, name), token)
if st == 200:
    print("  already exists")
    j = json.loads(body)
    print("  private=%s  html=%s" % (j.get("private"), j.get("html_url")))
else:
    print("  GET -> %s, creating…" % st)
    st, body = api("/user/repos", token, {
        "name": name,
        "description": "本机 AI 技能库个人备份（许可受限内容已排除，见 BACKUP_SCOPE.md）",
        "private": True,
        "auto_init": False,
        "has_issues": False,
        "has_wiki": False,
    }, method="POST")
    print("  POST /user/repos -> %s" % st)
    if st not in (200, 201):
        print("  body:", body[:600])
        raise SystemExit("create failed")
    j = json.loads(body)
    print("  created: %s  private=%s" % (j.get("html_url"), j.get("private")))

if "--create-only" in sys.argv:
    raise SystemExit(0)

url = "https://gitcode.com/%s/%s.git" % (NS, name)
rc, out, err = git(["remote", "remove", "gitcode"], cwd=path)
rc, out, err = git(["remote", "add", "gitcode", url], cwd=path)
print("  remote add rc=%d %s" % (rc, err[:200]))
print("  pushing (this may take a while)…")
rc, out, err = git(["push", "-u", "gitcode", "main"], cwd=path)
print("  push rc=%d" % rc)
for ln in (out + "\n" + err).splitlines():
    if ln.strip():
        print("   ", ln[:200])
rc, out, err = git(["ls-remote", "--heads", "gitcode"], cwd=path)
print("  ls-remote rc=%d -> %s" % (rc, out[:200]))
