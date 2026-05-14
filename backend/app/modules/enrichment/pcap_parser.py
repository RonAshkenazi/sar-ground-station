from __future__ import annotations

import datetime as dt
import struct
from pathlib import Path
from typing import Any


LINKTYPE_ETHERNET = 1
LINKTYPE_IEEE802_11 = 105
LINKTYPE_RADIOTAP = 127
REID_IE_TAGS = {1, 50, 45, 127, 221}


def parse_wifi_pcap(pcap_path: Path) -> list[dict[str, Any]]:
    """
    Parse a Wi-Fi PCAP and return frame dictionaries.

    This parser handles standard libpcap records for IEEE 802.11 captures and
    Ethernet-like test captures. Missing fields are returned as None.
    """
    frames: list[dict[str, Any]] = []
    with pcap_path.open("rb") as file:
        header = file.read(24)
        if len(header) < 24:
            return frames
        endian, nano = _pcap_endian(header[:4])
        if endian is None:
            return frames
        _, _, _, _, _, _, linktype = struct.unpack(f"{endian}IHHIIII", header)
        divisor = 1_000_000_000 if nano else 1_000_000

        while True:
            record_header = file.read(16)
            if len(record_header) == 0:
                break
            if len(record_header) < 16:
                break
            ts_sec, ts_frac, incl_len, _orig_len = struct.unpack(f"{endian}IIII", record_header)
            payload = file.read(incl_len)
            if len(payload) < incl_len:
                break
            timestamp = ts_sec + (ts_frac / divisor)
            parsed = _parse_payload(payload, linktype)
            parsed["timestamp_utc"] = _iso_from_unix(timestamp)
            parsed["frame_len"] = len(payload)
            frames.append(parsed)
    return frames


def parse_ble_pcap(pcap_path: Path) -> list[dict[str, Any]]:
    # TODO: TBD BLE PCAP parsing
    return []


def _pcap_endian(magic: bytes) -> tuple[str | None, bool]:
    if magic == b"\xd4\xc3\xb2\xa1":
        return ("<", False)
    if magic == b"\xa1\xb2\xc3\xd4":
        return (">", False)
    if magic == b"\x4d\x3c\xb2\xa1":
        return ("<", True)
    if magic == b"\xa1\xb2\x3c\x4d":
        return (">", True)
    return (None, False)


def _parse_payload(payload: bytes, linktype: int) -> dict[str, Any]:
    frame = {
        "src_mac": None,
        "dst_mac": None,
        "bssid": None,
        "seq_ctl": None,
        "ie_ids": None,
        "ie_fingerprint": None,
        "ie_vendor_ouis": None,
        "frame_type": None,
        "channel": None,
    }
    if linktype == LINKTYPE_ETHERNET and len(payload) >= 14:
        frame.update(
            {
                "dst_mac": _format_mac(payload[0:6]),
                "src_mac": _format_mac(payload[6:12]),
                "bssid": None,
                "frame_type": "ethernet",
            }
        )
        return frame

    if linktype == LINKTYPE_IEEE802_11 and len(payload) >= 24:
        frame_control = int.from_bytes(payload[0:2], "little")
        type_id = (frame_control >> 2) & 0b11
        subtype = (frame_control >> 4) & 0b1111
        to_ds = bool(frame_control & 0x0100)
        from_ds = bool(frame_control & 0x0200)
        addr1 = _format_mac(payload[4:10])
        addr2 = _format_mac(payload[10:16])
        addr3 = _format_mac(payload[16:22])
        seq_ctl = int.from_bytes(payload[22:24], "little")
        src_mac, dst_mac, bssid = _wifi_addresses(addr1, addr2, addr3, to_ds, from_ds)
        frame.update(
            {
                "src_mac": src_mac,
                "dst_mac": dst_mac,
                "bssid": bssid,
                "seq_ctl": seq_ctl,
                "frame_type": f"wifi_type_{type_id}_subtype_{subtype}",
            }
        )
        if type_id == 0:
            if subtype in (4,):
                ie_offset = 24
            elif subtype in (5, 8):
                ie_offset = 36
            else:
                ie_offset = 24
            ies = _parse_information_elements(payload[ie_offset:])
            frame.update(ies)
    if linktype == LINKTYPE_RADIOTAP and len(payload) >= 4:
        rt_len = struct.unpack_from("<H", payload, 2)[0]
        if rt_len < len(payload):
            return _parse_payload(payload[rt_len:], LINKTYPE_IEEE802_11)
    return frame


def _wifi_addresses(
    addr1: str | None,
    addr2: str | None,
    addr3: str | None,
    to_ds: bool,
    from_ds: bool,
) -> tuple[str | None, str | None, str | None]:
    if not to_ds and not from_ds:
        return (addr2, addr1, addr3)
    if to_ds and not from_ds:
        return (addr2, addr3, addr1)
    if from_ds and not to_ds:
        return (addr3, addr1, addr2)
    return (addr2, addr1, addr3)


def _parse_information_elements(data: bytes) -> dict[str, str | None]:
    ids: list[str] = []
    fingerprint: list[str] = []
    vendor_ouis: list[str] = []
    index = 0
    while index + 2 <= len(data):
        element_id = data[index]
        length = data[index + 1]
        value = data[index + 2 : index + 2 + length]
        if len(value) < length:
            break
        ids.append(str(element_id))
        if element_id in REID_IE_TAGS:
            fingerprint.append(f"{element_id}:{value.hex()}")
        if element_id == 221 and len(value) >= 3:
            vendor_ouis.append(value[:3].hex(":"))
        index += 2 + length
    return {
        "ie_ids": ",".join(ids) if ids else None,
        "ie_fingerprint": ";".join(fingerprint) if fingerprint else None,
        "ie_vendor_ouis": ",".join(vendor_ouis) if vendor_ouis else None,
    }


def _format_mac(raw: bytes) -> str | None:
    if len(raw) != 6:
        return None
    return ":".join(f"{byte:02x}" for byte in raw)


def _iso_from_unix(timestamp: float) -> str:
    return dt.datetime.fromtimestamp(timestamp, tz=dt.timezone.utc).isoformat().replace("+00:00", "Z")
