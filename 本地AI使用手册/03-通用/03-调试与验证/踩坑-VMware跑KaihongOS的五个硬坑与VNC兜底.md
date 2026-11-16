# 踩坑：VMware 里跑 KaihongOS 的五个硬坑 + OpenHarmony 客户机的 VNC 兜底

> verified 2026-11-15。severity high（其中第 3 条直接导致用户虚拟机打不开、被误判为「VMX 文件损坏」）。

## 背景

本机 VMware Workstation 25.0.0 build-24995812，客户机为深开鸿 KaihongOS 桌面版 6.1.1.15（x86，OpenHarmony 底座），镜像 `kaihong-installer-6.1-20261113.iso`。四台虚拟机统一放在 `D:\VMxiton`。

## 症状与根因（逐条实测）

### 1. 创建虚拟机时 PCIe 插槽冲突

按常规配置新建（NVMe + USB XHCI）会在开机时直接报 `usb_xhci` / `nvme0` **无可用 PCIe 插槽**，虚拟机起不来。

**根因**：KaihongOS 需要的设备组合（EFI + 大显存 + SATA/NVMe + USB）在默认 `virtualHW.version` 下插槽分配不足。

**可用写法**（vmx 手写，改前必须结束所有 `vmware*` 进程，否则 GUI 会回写覆盖）：

- 磁盘改 **SATA**：`sata0:0.present/fileName/deviceType`
- 显式 4 组 PCIe 根端口：`pciBridge0/4/5/6/7.present = "TRUE"`、`pciBridgeN.pciBridge:0.present = "TRUE"`（`pcieRootPort`）、`functions = 8`
- **不要手写 `pciSlotNumber`**，留给 VMware 分配

### 2. 共享文件夹在客户机里看不见

vmx 已写了完整的 `sharedFolder0.*`，装好工具后 guest 文件管理器里仍然没有共享。

**根因**：`isolation.tools.hgfs.disable` 被 VMware 改写成了 `"TRUE"`（HGFS 被禁用）。手工改回 `"FALSE"` 并重启后，宿主日志出现 `HGFSPublish: publishing 1 shares`，guest 里出现「VMware 共享文件夹」。

**验证路径**（KaihongOS）：`此电脑 → 系统磁盘 → VMware → VMShare`。

### 3. 加密虚拟机里把配置追加到 `encryption.*` 之后 → 必报「VMX 文件损坏」

用户机器上一台 Windows 11 x64（`vmx.encryptionType = "partial"`）突然弹「无法打开虚拟机……VMX 文件损坏，是否从库中移除」。

**根因**：vmx 共 149 行，`encryption.keySafe` / `encryption.data` 位于 137–138 行，但其后 140–148 行又被追加了一段明文 `sharedFolder.*` 和重复的 `isolation.tools.hgfs.disable`。**VMware 要求加密块必须在文件末尾**，加密块之后出现任何配置行即判定损坏。

**正确做法**：共享等配置必须写在 `encryption.*` **之前**（VMware 自己在 GUI 里改配置时就是这么插入的，实测改完 146 行、加密块仍在末尾、开机正常）。

**处置**：删除加密块之后的 11 行明文，文件回到 138 行 → 报错从「VMX 文件损坏」变成「A password is required for this operation」，说明结构可解析；用户输自己的加密密码后正常开机。

**教训**：加密虚拟机的 vmx 绝对不要用脚本追加配置。必须让 VMware 在解锁状态下经 GUI 写入；`vmcli` 的 `ConfigParams` / `HGFS` 模块在加密 VM 上会挂起等密码，同样不可用。

### 4. VMware 客户机里的 OpenHarmony 收不到合成输入，VNC 是唯一通道

`cu.click` 对 VMware 窗口稳定报 `Windows input injection failed`；`SendKeys` 发 `Ctrl+D` 无反应；`VMUIFrame` 的 `GetMenu(hwnd)` 返回 **0**（菜单是自绘，无 Win32 HMENU，`WM_COMMAND` 路径不通）；UIA 能选虚拟机列表项、能读状态栏，但**不暴露菜单栏**。

**可用通道**：vmx 加

```
RemoteDisplay.vnc.enabled = "TRUE"
RemoteDisplay.vnc.port = "5901"
```

再用自写 RFB 客户端（Python socket 直连 5901）操作：`RFB 003.008` 握手 → `SecurityType=1 None` → `ClientInit` → `ServerInit` 拿 framebuffer（本机 2358×1398，早期启动阶段是 1280×800，VT 分辨率会变）→ `SetPixelFormat` 32bpp → `SetEncodings` Raw → `FramebufferUpdateRequest`。**鼠标要用 `PointerEvent`（type=5，button-mask 1=按下 / 0=释放）**，键盘用 `KeyEvent`（type=4，X11 keysym）。

关键坑：RFB 矩形头是 **12 字节**（x/y/w/h 各 2 + encoding 4），FramebufferUpdateRequest 是 **10 字节**（type/incremental 各 1 + x/y/w/h 各 2）；写错就是 `struct.error`。

**收尾必须删除这两行 vmx 配置**——无密码 VNC 监听在宿主所有网卡上，属安全隐患。本次已删并复核端口关闭。

配套脚本见 [[脚本-kaihongos-vnc-rfb.py]]（同目录）。

### 5. KaihongOS 装不了达梦 / 人大金仓

用户要求在 KaihongOS 里装达梦 DM8 与人大金仓 KingbaseES。实测不可行：

- 系统是 OpenHarmony（musl 运行时），**没有 glibc、没有 rpm/dpkg/yum**
- 组件管理里总共 12 个组件，**没有 Docker / 容器**；官方给的多系统方案只有「QEMU 模拟器」
- 官方所说的「支持安装 Linux 应用」= 开发者把应用**适配打包成 HAP**，不是直接跑 ELF/iso
- guest 侧 22 / 8710（SSH / hdc）端口全关，无命令行调试通道

**替代路线**：装到 Linux 客户机（如 uos，SSH 22 可用）或 Windows 客户机（两家都有 Win64 版）；两库端口分开（达梦 5236、金仓 54321）+ 目录/用户/服务名分开即可共存。

### 6. 移动虚拟机目录后 VMware 库条目失效

把 KaihongOS 从 `G:\AIrenwu\02_项目代码\KaihongOS\...` 整体搬到 `D:\VMxiton\KaihongOS 6.1.1.15` 后，VMware 左侧列表里的条目点不开。

**根因**：`%APPDATA%\VMware\inventory.vmls` 的 `vmlistN.config` 与 `indexN.id`、以及 `preferences.ini` 的 `pref.ws.session.windowN.tabK.file` 里存的是**绝对路径**，搬目录不会自动更新。实测这三个位置都还指着**更早的一处旧路径**（用户上一次移目录时就没同步过），所以列表条目早就失效了。

**做法**（VMware 未运行时）：备份这两个文件 → 字节级替换旧路径为新路径 → 回读确认。vmx 内部用相对路径（`sata0:0.fileName = "disk.vmdk"`），搬目录本身不影响启动。

**校验**：`robocopy /MIR` 后比对文件数、总字节、`disk.vmdk` 大小三项一致，再 `vmware-vdiskmanager -R disk.vmdk` 退出码 0，最后才删源目录。

## 规则

1. 加密虚拟机的 vmx 只能由 VMware 在解锁状态写入，脚本不得追加配置；任何配置必须在 `encryption.*` 之前。
2. 改 vmx 前先结束全部 `vmware*` 进程，改完核对 `isolation.tools.hgfs.disable` 是否被改回 `TRUE`。
3. 需要往 OpenHarmony 客户机里点鼠标时，直接上 VNC + 自写 RFB，别在 cu / SendKeys / WM_COMMAND 上耗时间；用完立删 VNC 配置。
4. 商用 Linux 数据库不往 OpenHarmony 客户机上试；先查组件库有没有容器、有没有 libc 兼容层。
5. 搬虚拟机目录后，必须同步 `inventory.vmls`（两处）与 `preferences.ini`（一处），否则库里条目失效。
6. 客户机分辨率会随启动阶段变化（1280×800 → 2358×1398），截图坐标必须现截图现换算，不能用上一轮的。
