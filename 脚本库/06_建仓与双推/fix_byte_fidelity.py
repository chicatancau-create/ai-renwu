"""The first `git add -A` in D:\\Skills ran BEFORE .gitattributes existed, so 79
files were committed with CRLF->LF normalisation.  `git rm -r --cached .` did not
actually clear the index (the migration JSONs stayed staged, which was the tell).
Re-stage every file with the current attributes so the blob bytes equal disk bytes.
"""
import hashlib
import os
import subprocess
import sys

sys.stdout.reconfigure(errors="replace")
GIT = r"D:\Git\cmd\git.exe"
LIVE = r"D:\Skills"
env = dict(os.environ, GIT_TERMINAL_PROMPT="0")


def git(args, timeout=900):
    r = subprocess.run([GIT] + args, cwd=LIVE, capture_output=True, text=True,
                       timeout=timeout, env=env, encoding="utf-8", errors="replace")
    return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()


print("=== 1. confirm the difference really is line endings ===")
for rel in ("brave-web-search/SKILL.md", "dws/SKILL.md"):
    p = os.path.join(LIVE, rel.replace("/", os.sep))
    disk = open(p, "rb").read()
    rc, blob, _ = git(["show", "HEAD:" + rel])
    rc2, out, _ = git(["cat-file", "-p", "HEAD:" + rel])
    # get raw blob bytes via cat-file --batch is awkward; use hash-object comparison
    rc3, h_disk, _ = git(["hash-object", "--no-filters", p])
    rc4, h_idx, _ = git(["rev-parse", "HEAD:" + rel])
    print("  %-32s disk_crlf=%d disk_lf_only=%d  blob==disk_nofilter:%s"
          % (rel, disk.count(b"\r\n"), disk.count(b"\n") - disk.count(b"\r\n"),
             h_disk == h_idx))

print("\n=== 2. attributes in force ===")
rc, out, err = git(["check-attr", "text", "--", "brave-web-search/SKILL.md", "dws/SKILL.md"])
print(" ", out or err)
rc, out, _ = git(["config", "core.autocrlf"])
print("  core.autocrlf =", out)

print("\n=== 3. renormalise the index (store bytes exactly as on disk) ===")
rc, out, err = git(["add", "--renormalize", "."])
print("  add --renormalize rc=%d %s" % (rc, err[:200]))
rc, out, _ = git(["diff", "--cached", "--name-only"])
changed = [f for f in out.splitlines() if f.strip()]
print("  re-staged files: %d" % len(changed))
for f in changed[:8]:
    print("   ", f)

print("\n=== 4. verify every staged blob now equals disk bytes ===")
rc, out, _ = git(["diff", "--cached", "--name-only"])
bad = []
for rel in [f for f in out.splitlines() if f.strip()]:
    p = os.path.join(LIVE, rel.replace("/", os.sep))
    if not os.path.isfile(p):
        continue
    rc1, h_disk, _ = git(["hash-object", "--no-filters", p])
    rc2, h_idx, _ = git(["ls-files", "-s", "--", rel])
    idx_sha = h_idx.split()[1] if h_idx else ""
    if h_disk != idx_sha:
        bad.append(rel)
print("  mismatches after renormalise: %d %s" % (len(bad), bad[:5]))

if not bad and changed:
    rc, out, err = git(["commit", "-q", "-m",
                        "修正备份字节一致性：首次 add 早于 .gitattributes，79 个文件被 CRLF->LF 规范化\n\n"
                        "git add --renormalize . 重新按 * -text 入库，使 blob 字节等于磁盘字节。\n"
                        "发现方式：从两个远端浅克隆后逐文件 sha256 比对，79 个不一致。\n"
                        "QoderToolkit 无此问题（它的 .gitattributes 在首次 add 之前就位）。"])
    print("  commit rc=%d %s" % (rc, err[:200]))
    rc, out, _ = git(["log", "--oneline", "-1"])
    print(" ", out)
else:
    print("  NOT committing (bad=%d changed=%d)" % (len(bad), len(changed)))
