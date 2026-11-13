# create_gitcode_repo.py - create PRIVATE repo ai-renwu under zhoumoyukuai via GitCode v5 API.
# Real endpoint: https://gitcode.com/api/v5/user/repos (handbook-verified). Reads credential via
# CredReadW; NEVER prints the token. Prints only repo metadata / status.
import ctypes
import json
import urllib.request
import urllib.error
from ctypes import wintypes

advapi32 = ctypes.WinDLL('advapi32', use_last_error=True)


class CREDENTIALW(ctypes.Structure):
    _fields_ = [
        ('Flags', wintypes.DWORD),
        ('Type', wintypes.DWORD),
        ('TargetName', wintypes.LPWSTR),
        ('Comment', wintypes.LPWSTR),
        ('LastWritten', wintypes.FILETIME),
        ('CredentialBlobSize', wintypes.DWORD),
        ('CredentialBlob', ctypes.POINTER(ctypes.c_byte)),
        ('Persist', wintypes.DWORD),
        ('AttributeCount', wintypes.DWORD),
        ('Attributes', ctypes.c_void_p),
        ('TargetAlias', wintypes.LPWSTR),
        ('UserName', wintypes.LPWSTR),
    ]


advapi32.CredReadW.argtypes = [
    wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
    ctypes.POINTER(ctypes.POINTER(CREDENTIALW)),
]
advapi32.CredReadW.restype = wintypes.BOOL
advapi32.CredFree.argtypes = [ctypes.c_void_p]


def read_secret(target):
    p = ctypes.POINTER(CREDENTIALW)()
    if not advapi32.CredReadW(target, 1, 0, ctypes.byref(p)):
        return None, None
    c = p.contents
    blob = ctypes.string_at(c.CredentialBlob, c.CredentialBlobSize)
    secret = blob.decode('utf-16-le')
    user = c.UserName
    advapi32.CredFree(p)
    return user, secret


user, token = read_secret('git:https://gitcode.com')
print('credential user =', user, '| token length =', len(token) if token else 0)
if not token:
    raise SystemExit('no credential found')

body = json.dumps({
    'name': 'ai-renwu',
    'private': True,
    'auto_init': False,
    'description': 'AI renwu workspace scripts backup (dual-push)',
}).encode('utf-8')
req = urllib.request.Request('https://gitcode.com/api/v5/user/repos', data=body, method='POST')
req.add_header('Authorization', 'Bearer ' + token)
req.add_header('Content-Type', 'application/json')
try:
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read().decode('utf-8'))
        print('STATUS', r.status)
        print('full_name =', data.get('full_name') or data.get('path_with_namespace') or data.get('path'))
        print('private =', data.get('private'))
        print('html_url =', data.get('html_url'))
except urllib.error.HTTPError as e:
    print('HTTPError', e.code)
    print(e.read().decode('utf-8', 'replace')[:600])
except Exception as e:
    print('ERR', type(e).__name__, str(e)[:200])
