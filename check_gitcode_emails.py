# Read-only: check which emails are bound to the GitCode account.
# Reads the stored credential via CredReadW (never prints the secret),
# then GETs the v5 emails endpoints with Bearer auth.
import ctypes
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


user, secret = read_secret('git:https://gitcode.com')
print('credential user =', user, '| secret length =', len(secret) if secret else 0)
if not secret:
    raise SystemExit('no credential found')

for url in (
    'https://gitcode.com/api/v5/emails',
    'https://gitcode.com/api/v5/user/emails',
):
    req = urllib.request.Request(
        url,
        headers={'Authorization': 'Bearer ' + secret, 'User-Agent': 'curl/8'},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            print(url, '->', r.status, r.read().decode('utf-8')[:800])
    except urllib.error.HTTPError as e:
        print(url, '->', e.code, e.read().decode('utf-8')[:300])
    except Exception as e:
        print(url, '-> ERR', repr(e))
