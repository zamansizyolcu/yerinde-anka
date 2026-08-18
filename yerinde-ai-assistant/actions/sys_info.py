"""
Sistem bilgisi — CachyOS (Arch Linux) için psutil + nmcli/iwgetid kullanır.
"""

import subprocess
import datetime

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


def sys_info(query: str) -> str:
    query = query.lower().strip()
    results = []

    if query in ("battery", "pil", "all"):
        results.append(_battery())
    if query in ("cpu", "işlemci", "all"):
        results.append(_cpu())
    if query in ("ram", "bellek", "memory", "all"):
        results.append(_ram())
    if query in ("disk", "depolama", "all"):
        results.append(_disk())
    if query in ("gpu", "ekran kartı", "ekran karti", "all"):
        results.append(_gpu())
    if query in ("time", "saat", "zaman", "all"):
        now = datetime.datetime.now()
        results.append(f"Saat: {now.strftime('%H:%M:%S')}")
    if query in ("date", "tarih", "all"):
        now = datetime.datetime.now()
        results.append(f"Tarih: {now.strftime('%d %B %Y, %A')}")
    if query in ("network", "ağ", "wifi", "all"):
        results.append(_network())

    if not results:
        results.append(f"Bilinmeyen sorgu: {query}. battery/cpu/ram/disk/gpu/time/date/network/all kullanın.")

    return "\n".join(r for r in results if r)


def _battery() -> str:
    if HAS_PSUTIL:
        bat = psutil.sensors_battery()
        if bat:
            status = "Şarj oluyor" if bat.power_plugged else "Pilde"
            return f"Pil: %{bat.percent:.0f} — {status}"
    return "Pil bilgisi alınamadı (masaüstü bilgisayarda pil olmayabilir)."


def _cpu() -> str:
    if HAS_PSUTIL:
        usage = psutil.cpu_percent(interval=0.5)
        count = psutil.cpu_count(logical=True)
        freq = psutil.cpu_freq()
        freq_str = f", {freq.current:.0f} MHz" if freq else ""
        return f"CPU: %{usage:.1f} kullanım — {count} çekirdek{freq_str}"
    return "CPU bilgisi alınamadı."


def _ram() -> str:
    if HAS_PSUTIL:
        vm = psutil.virtual_memory()
        total = vm.total / (1024 ** 3)
        used = vm.used / (1024 ** 3)
        pct = vm.percent
        return f"RAM: {used:.1f}GB / {total:.1f}GB kullanımda (%{pct:.0f})"
    return "RAM bilgisi alınamadı."


def _disk() -> str:
    if HAS_PSUTIL:
        du = psutil.disk_usage("/")
        total = du.total / (1024 ** 3)
        used = du.used / (1024 ** 3)
        free = du.free / (1024 ** 3)
        return f"Disk (/): {used:.1f}GB kullanıldı, {free:.1f}GB boş (toplam {total:.1f}GB)"
    return "Disk bilgisi alınamadı."


def _network() -> str:
    # nmcli ile aktif WiFi/bağlantı adı
    try:
        out = subprocess.check_output(
            ["nmcli", "-t", "-f", "active,ssid", "dev", "wifi"],
            text=True, timeout=5, stderr=subprocess.DEVNULL,
        )
        for line in out.splitlines():
            if line.startswith("yes:"):
                ssid = line.split(":", 1)[-1].strip()
                if ssid:
                    return f"WiFi: {ssid} bağlı"
    except Exception:
        pass
    # iwgetid fallback
    try:
        out = subprocess.check_output(["iwgetid", "-r"], text=True, timeout=5,
                                       stderr=subprocess.DEVNULL)
        ssid = out.strip()
        if ssid:
            return f"WiFi: {ssid} bağlı"
    except Exception:
        pass
    # IP fallback
    if HAS_PSUTIL:
        try:
            for iface, addrs in psutil.net_if_addrs().items():
                if iface == "lo":
                    continue
                for addr in addrs:
                    if addr.family.name == "AF_INET" and not addr.address.startswith("169."):
                        return f"Ağ: {iface} üzerinden IP {addr.address}"
        except Exception:
            pass
    return "Ağ bağlantısı bulunamadı."


def _gpu() -> str:
    status = get_gpu_status()
    if not status:
        return "Ekran kartı bilgisi alınamadı."
    if status.get("usage_pct") is not None:
        return f"GPU: {status['name']} — %{status['usage_pct']:.0f} kullanım"
    return f"GPU: {status['name']}"


def get_gpu_status() -> dict | None:
    """
    UI'daki sistem panelinde göstermek için GPU adı ve (varsa) kullanım
    yüzdesini döner: {"name": str, "usage_pct": float|None}.
    Önce nvidia-smi (NVIDIA), sonra rocm-smi (AMD), yoksa lspci ile sadece isim.
    """
    # NVIDIA — hem isim hem kullanım yüzdesi
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=name,utilization.gpu",
             "--format=csv,noheader,nounits"],
            text=True, timeout=4, stderr=subprocess.DEVNULL,
        )
        line = out.strip().splitlines()[0]
        name, usage = [p.strip() for p in line.split(",")]
        return {"name": name, "usage_pct": float(usage)}
    except Exception:
        pass

    # AMD — rocm-smi ile kullanım yüzdesi
    try:
        out = subprocess.check_output(
            ["rocm-smi", "--showuse"],
            text=True, timeout=4, stderr=subprocess.DEVNULL,
        )
        for line in out.splitlines():
            if "%" in line:
                usage = float(line.split()[-1].replace("%", ""))
                return {"name": "AMD GPU", "usage_pct": usage}
    except Exception:
        pass

    # Genel — sadece isim, lspci ile
    try:
        out = subprocess.check_output(
            ["lspci"], text=True, timeout=4, stderr=subprocess.DEVNULL,
        )
        for line in out.splitlines():
            if "VGA" in line or "3D controller" in line:
                name = line.split(": ", 1)[-1].strip()
                return {"name": name, "usage_pct": None}
    except Exception:
        pass

    return None
