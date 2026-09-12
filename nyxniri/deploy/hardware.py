"""Pure PCI device classification for diagnostic reports."""


def classify_gpu_devices(lspci_text: str) -> str:
    """Describe listed GPU vendors, without inferring the active renderer."""
    vendors = set()
    for raw in lspci_text.splitlines():
        line = raw.lower()
        if any(kind in line for kind in (
            "vga compatible controller:", "display controller:", "3d controller:",
        )):
            vendors.add("nvidia" if "nvidia" in line else "other")
    if vendors == {"nvidia", "other"}:
        return "NVIDIA + other GPU devices"
    if vendors == {"nvidia"}:
        return "NVIDIA GPU devices only"
    if vendors == {"other"}:
        return "Other GPU devices only"
    return "Unknown"
