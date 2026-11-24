"""
MeshProtocolSimulator
=====================
Rigorous BLE / Wi-Fi Direct V2X mesh network simulator for offline emergency
data relay through passing connected vehicles and Roadside Units (RSUs).

Responsibilities:
  - Binary packet encoding (struct.pack) with CRC-32 checksum.
  - Ad-hoc hop topology simulation (3–7 relay nodes: RSUs, connected cars, ambulances).
  - Packet loss (15% per hop), bit-flip corruption (5% per hop).
  - Automatic checksum validation and retransmission logic (max 3 retries).
  - Produces a structured transmission log and Common Alerting Protocol (CAP) payload.
"""

from __future__ import annotations

import asyncio
import binascii
import json
import logging
import random
import struct
import time
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PACKET_LOSS_PROBABILITY   = 0.15   # 15% per hop
BIT_FLIP_PROBABILITY      = 0.05   # 5% per hop
MAX_RETRANSMISSIONS       = 3
HOP_LATENCY_MS_MIN        = 20
HOP_LATENCY_MS_MAX        = 120
RADIO_RANGE_METRES        = 50

# Packet format (binary struct layout):
#   lat        : float  (4 bytes)  — latitude
#   lon        : float  (4 bytes)  — longitude
#   urgency    : float  (4 bytes)  — urgency index
#   timestamp  : uint32 (4 bytes)  — epoch seconds
#   sequence   : uint16 (2 bytes)  — sequence number
#   flags      : uint8  (1 byte)   — bit flags
#   reserved   : uint8  (1 byte)   — padding
# Total payload: 20 bytes + 4 bytes CRC-32 = 24 bytes
STRUCT_FORMAT = "!fffIHBB"   # network byte order
STRUCT_SIZE   = struct.calcsize(STRUCT_FORMAT)  # 20 bytes


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class MeshPacket:
    latitude:   float
    longitude:  float
    urgency:    float
    timestamp:  int
    sequence:   int   = 0
    flags:      int   = 0b00000001  # bit0 = emergency flag


@dataclass
class HopLog:
    hop_number:        int
    relay_node_id:     str
    distance_to_next:  float       # metres (simulated)
    latency_ms:        float
    status:            str         # "PASS" | "CORRUPTED" | "LOST" | "RETRANSMIT_OK" | "RETRANSMIT_FAIL"
    retransmit_count:  int
    rssi_dbm:          float       # simulated signal strength
    crc_expected:      str
    crc_received:      str
    notes:             str


@dataclass
class TransmissionResult:
    success:          bool
    total_hops:       int
    hops_completed:   int
    hop_logs:         list[HopLog]
    delivery_ratio:   float        # 0.0 – 1.0
    total_latency_ms: float
    raw_payload_hex:  str
    final_status:     str          # "DELIVERED" | "FAILED"
    cap_alert_json:   str = ""     # Standard Common Alerting Protocol payload


# ---------------------------------------------------------------------------
# Encoding & checksum
# ---------------------------------------------------------------------------

def _encode_packet(pkt: MeshPacket) -> bytes:
    """Serialize packet to binary and append CRC-32."""
    payload = struct.pack(
        STRUCT_FORMAT,
        pkt.latitude,
        pkt.longitude,
        pkt.urgency,
        pkt.timestamp,
        pkt.sequence & 0xFFFF,
        pkt.flags & 0xFF,
        0,   # reserved
    )
    crc = struct.pack("!I", binascii.crc32(payload) & 0xFFFFFFFF)
    return payload + crc


def _decode_and_verify(raw: bytes) -> tuple[bool, str, str]:
    """
    Verify CRC-32. Returns (is_valid, expected_crc_hex, received_crc_hex).
    """
    if len(raw) < STRUCT_SIZE + 4:
        return False, "N/A", "TRUNCATED"

    payload  = raw[:STRUCT_SIZE]
    crc_recv = raw[STRUCT_SIZE:]

    expected_crc = binascii.crc32(payload) & 0xFFFFFFFF
    received_crc = struct.unpack("!I", crc_recv)[0]

    return (
        expected_crc == received_crc,
        f"{expected_crc:08X}",
        f"{received_crc:08X}",
    )


def _flip_random_bit(data: bytes) -> bytes:
    """Flip a single random bit in the byte string to simulate RF corruption."""
    data_arr = bytearray(data)
    byte_idx = random.randint(0, len(data_arr) - 1)
    bit_idx  = random.randint(0, 7)
    data_arr[byte_idx] ^= (1 << bit_idx)
    return bytes(data_arr)


# ---------------------------------------------------------------------------
# Topology generator
# ---------------------------------------------------------------------------

def _generate_hop_topology(num_hops: int) -> list[str]:
    """
    Generate relay node IDs simulating passing vehicles and smart infrastructure.
    """
    v2x_actors = [
        "AMB-102 (CATS Emergency Ambulance)",
        "PCR-09 (Delhi Police Highway Patrol)",
        "BUS-412 (DTC Electric City Bus)",
        "RSU-07 (NHAI Smart Roadside Unit)",
        "V2X-882 (Connected Commercial Vehicle)",
        "RSU-14 (Delhi Traffic Smart Gantry)",
        "MEDIC-03 (Rapid Two-Wheeler Medic)",
        "EV-901 (Connected Passenger Car)",
    ]
    random.shuffle(v2x_actors)
    return v2x_actors[:num_hops]


def _simulate_rssi() -> float:
    """Simulated RSSI in dBm. Range: -40 (excellent) to -85 (poor)."""
    return round(random.uniform(-85.0, -40.0), 1)


def _simulate_distance() -> float:
    """Distance to next relay node in metres (within radio range)."""
    return round(random.uniform(5.0, RADIO_RANGE_METRES), 1)


# ---------------------------------------------------------------------------
# CAP (Common Alerting Protocol) Payload Generator
# ---------------------------------------------------------------------------

def generate_cap_payload(
    latitude: float,
    longitude: float,
    urgency: float,
    incident_type: str = "Road Accident",
    dispatched_units: Optional[list[str]] = None,
    nearest_hospital: Optional[str] = None,
) -> str:
    """
    Generate an ITU-T X.1303 / OASIS CAP compliant emergency broadcast JSON
    for integration into National Emergency Response Systems (ERSS 112 / CATS).
    """
    alert = {
        "identifier": f"IN-DEL-ERSS-{int(time.time())}-{random.randint(1000, 9999)}",
        "sender": "GuardianNodes-RoadSoS-CentralCommand",
        "sent": time.strftime("%Y-%m-%dT%H:%M:%S+05:30"),
        "status": "Actual",
        "msgType": "Alert",
        "scope": "Restricted",
        "info": {
            "category": "Safety",
            "event": f"Urgent Emergency Dispatch - {incident_type}",
            "urgency": "Immediate" if urgency >= 8.0 else "Expected" if urgency >= 5.0 else "Future",
            "severity": "Extreme" if urgency >= 8.0 else "Severe" if urgency >= 6.0 else "Moderate",
            "certainty": "Observed",
            "area": {
                "areaDesc": "Delhi NCR Emergency Road Network Corridor",
                "circle": f"{latitude:.6f},{longitude:.6f},0.5",
            },
            "parameters": {
                "urgency_index": f"{urgency:.2f}/10.00",
                "dispatched_units": dispatched_units or ["Ambulance ALS"],
                "designated_trauma_centre": nearest_hospital or "AIIMS Apex Trauma Centre",
                "transport_protocol": "BLE-5.0 / 802.11p V2X Mesh Ad-Hoc Relay",
            },
        },
    }
    return json.dumps(alert, indent=2)


# ---------------------------------------------------------------------------
# Core simulator
# ---------------------------------------------------------------------------

class MeshProtocolSimulator:
    """
    Simulates BLE/Wi-Fi Direct offline mesh relay of an emergency packet
    through ad-hoc vehicle relay nodes.
    """

    def __init__(self, seed: Optional[int] = None) -> None:
        if seed is not None:
            random.seed(seed)
        self._sequence_counter = 0

    async def transmit(
        self,
        latitude:  float,
        longitude: float,
        urgency:   float,
        num_hops:  Optional[int] = None,
        incident_type: str = "Road Accident",
        dispatched_units: Optional[list[str]] = None,
        nearest_hospital: Optional[str] = None,
    ) -> TransmissionResult:
        """
        Asynchronously simulate end-to-end mesh packet transmission.
        """
        self._sequence_counter += 1
        pkt = MeshPacket(
            latitude=round(latitude, 6),
            longitude=round(longitude, 6),
            urgency=round(urgency, 2),
            timestamp=int(time.time()),
            sequence=self._sequence_counter,
        )

        encoded = _encode_packet(pkt)
        raw_hex = encoded.hex().upper()

        if num_hops is None:
            num_hops = random.randint(3, 6)

        relay_nodes = _generate_hop_topology(num_hops)
        hop_logs: list[HopLog] = []
        total_latency = 0.0
        hops_completed = 0

        for hop_idx, relay_id in enumerate(relay_nodes):
            latency = random.uniform(HOP_LATENCY_MS_MIN, HOP_LATENCY_MS_MAX)
            await asyncio.sleep(latency / 10_000)
            total_latency += latency

            hop_result, hop_log = await self._simulate_hop(
                hop_number=hop_idx + 1,
                relay_id=relay_id,
                encoded_packet=encoded,
                latency_ms=latency,
            )
            hop_logs.append(hop_log)

            if hop_result:
                hops_completed += 1

        successful_hops = sum(
            1 for h in hop_logs
            if h.status in ("PASS", "RETRANSMIT_OK")
        )
        delivery_ratio = successful_hops / num_hops if num_hops > 0 else 0.0

        success = delivery_ratio >= 0.5
        final_status = "DELIVERED" if success else "FAILED"

        cap_alert = generate_cap_payload(
            latitude=latitude,
            longitude=longitude,
            urgency=urgency,
            incident_type=incident_type,
            dispatched_units=dispatched_units,
            nearest_hospital=nearest_hospital,
        )

        return TransmissionResult(
            success=success,
            total_hops=num_hops,
            hops_completed=hops_completed,
            hop_logs=hop_logs,
            delivery_ratio=round(delivery_ratio, 3),
            total_latency_ms=round(total_latency, 1),
            raw_payload_hex=raw_hex,
            final_status=final_status,
            cap_alert_json=cap_alert,
        )

    def transmit_sync(
        self,
        latitude:  float,
        longitude: float,
        urgency:   float,
        num_hops:  Optional[int] = None,
        incident_type: str = "Road Accident",
        dispatched_units: Optional[list[str]] = None,
        nearest_hospital: Optional[str] = None,
    ) -> TransmissionResult:
        """Run the packet transmission simulation synchronously without event loop dependencies."""
        self._sequence_counter += 1
        pkt = MeshPacket(
            latitude=round(latitude, 6),
            longitude=round(longitude, 6),
            urgency=round(urgency, 2),
            timestamp=int(time.time()),
            sequence=self._sequence_counter,
        )

        encoded = _encode_packet(pkt)
        raw_hex = encoded.hex().upper()

        if num_hops is None:
            num_hops = random.randint(3, 6)

        relay_nodes = _generate_hop_topology(num_hops)
        hop_logs: list[HopLog] = []
        total_latency = 0.0
        hops_completed = 0

        for hop_idx, relay_id in enumerate(relay_nodes):
            latency = random.uniform(HOP_LATENCY_MS_MIN, HOP_LATENCY_MS_MAX)
            total_latency += latency

            hop_result, hop_log = self._simulate_hop_sync(
                hop_number=hop_idx + 1,
                relay_id=relay_id,
                encoded_packet=encoded,
                latency_ms=latency,
            )
            hop_logs.append(hop_log)

            if hop_result:
                hops_completed += 1

        successful_hops = sum(
            1 for h in hop_logs
            if h.status in ("PASS", "RETRANSMIT_OK")
        )
        delivery_ratio = successful_hops / num_hops if num_hops > 0 else 0.0

        success = delivery_ratio >= 0.5
        final_status = "DELIVERED" if success else "FAILED"

        cap_alert = generate_cap_payload(
            latitude=latitude,
            longitude=longitude,
            urgency=urgency,
            incident_type=incident_type,
            dispatched_units=dispatched_units,
            nearest_hospital=nearest_hospital,
        )

        return TransmissionResult(
            success=success,
            total_hops=num_hops,
            hops_completed=hops_completed,
            hop_logs=hop_logs,
            delivery_ratio=round(delivery_ratio, 3),
            total_latency_ms=round(total_latency, 1),
            raw_payload_hex=raw_hex,
            final_status=final_status,
            cap_alert_json=cap_alert,
        )

    def _simulate_hop_sync(
        self,
        hop_number: int,
        relay_id:   str,
        encoded_packet: bytes,
        latency_ms: float,
    ) -> tuple[bool, HopLog]:
        """Simulate a single RF hop synchronously with packet loss, corruption, and retransmission."""
        rssi         = _simulate_rssi()
        distance     = _simulate_distance()
        retries      = 0
        current_data = encoded_packet

        for attempt in range(MAX_RETRANSMISSIONS + 1):
            if random.random() < PACKET_LOSS_PROBABILITY:
                if attempt < MAX_RETRANSMISSIONS:
                    retries += 1
                    continue
                else:
                    log = HopLog(
                        hop_number=hop_number,
                        relay_node_id=relay_id,
                        distance_to_next=distance,
                        latency_ms=latency_ms,
                        status="RETRANSMIT_FAIL",
                        retransmit_count=retries,
                        rssi_dbm=rssi,
                        crc_expected="N/A",
                        crc_received="N/A",
                        notes=f"Packet dropped over RF after {retries} retry(ies). RSSI={rssi} dBm",
                    )
                    return False, log

            if random.random() < BIT_FLIP_PROBABILITY:
                current_data = _flip_random_bit(current_data)

            valid, exp_crc, recv_crc = _decode_and_verify(current_data)

            if valid:
                status = "PASS" if retries == 0 else "RETRANSMIT_OK"
                notes = (
                    f"Clean delivery. RSSI={rssi} dBm, range={distance} m"
                    if retries == 0
                    else f"CRC verified after {retries} retry(ies). RSSI={rssi} dBm"
                )
                log = HopLog(
                    hop_number=hop_number,
                    relay_node_id=relay_id,
                    distance_to_next=distance,
                    latency_ms=latency_ms,
                    status=status,
                    retransmit_count=retries,
                    rssi_dbm=rssi,
                    crc_expected=exp_crc,
                    crc_received=recv_crc,
                    notes=notes,
                )
                return True, log
            else:
                if attempt < MAX_RETRANSMISSIONS:
                    current_data = encoded_packet
                    retries += 1
                    continue
                else:
                    log = HopLog(
                        hop_number=hop_number,
                        relay_node_id=relay_id,
                        distance_to_next=distance,
                        latency_ms=latency_ms,
                        status="CORRUPTED",
                        retransmit_count=retries,
                        rssi_dbm=rssi,
                        crc_expected=exp_crc,
                        crc_received=recv_crc,
                        notes=(
                            f"CRC Mismatch (0x{exp_crc} != 0x{recv_crc}). "
                            f"Bit-flip persistent after {retries} retries."
                        ),
                    )
                    return False, log

        return False, HopLog(
            hop_number=hop_number,
            relay_node_id=relay_id,
            distance_to_next=distance,
            latency_ms=latency_ms,
            status="FAILED",
            retransmit_count=retries,
            rssi_dbm=rssi,
            crc_expected="N/A",
            crc_received="N/A",
            notes="Unknown transmission failure",
        )

    async def _simulate_hop(
        self,
        hop_number: int,
        relay_id:   str,
        encoded_packet: bytes,
        latency_ms: float,
    ) -> tuple[bool, HopLog]:
        """
        Simulate a single RF hop with packet loss, corruption, and retransmission.
        """
        rssi         = _simulate_rssi()
        distance     = _simulate_distance()
        retries      = 0
        current_data = encoded_packet

        for attempt in range(MAX_RETRANSMISSIONS + 1):
            if random.random() < PACKET_LOSS_PROBABILITY:
                if attempt < MAX_RETRANSMISSIONS:
                    retries += 1
                    await asyncio.sleep(0.001)
                    continue
                else:
                    log = HopLog(
                        hop_number=hop_number,
                        relay_node_id=relay_id,
                        distance_to_next=distance,
                        latency_ms=latency_ms,
                        status="RETRANSMIT_FAIL",
                        retransmit_count=retries,
                        rssi_dbm=rssi,
                        crc_expected="N/A",
                        crc_received="N/A",
                        notes=f"Packet dropped over RF after {retries} retry(ies). RSSI={rssi} dBm",
                    )
                    return False, log

            if random.random() < BIT_FLIP_PROBABILITY:
                current_data = _flip_random_bit(current_data)

            valid, exp_crc, recv_crc = _decode_and_verify(current_data)

            if valid:
                status = "PASS" if retries == 0 else "RETRANSMIT_OK"
                notes = (
                    f"Clean delivery. RSSI={rssi} dBm, range={distance} m"
                    if retries == 0
                    else f"CRC verified after {retries} retry(ies). RSSI={rssi} dBm"
                )
                log = HopLog(
                    hop_number=hop_number,
                    relay_node_id=relay_id,
                    distance_to_next=distance,
                    latency_ms=latency_ms,
                    status=status,
                    retransmit_count=retries,
                    rssi_dbm=rssi,
                    crc_expected=exp_crc,
                    crc_received=recv_crc,
                    notes=notes,
                )
                return True, log

            else:
                if attempt < MAX_RETRANSMISSIONS:
                    current_data = encoded_packet
                    retries += 1
                    await asyncio.sleep(0.001)
                    continue
                else:
                    log = HopLog(
                        hop_number=hop_number,
                        relay_node_id=relay_id,
                        distance_to_next=distance,
                        latency_ms=latency_ms,
                        status="CORRUPTED",
                        retransmit_count=retries,
                        rssi_dbm=rssi,
                        crc_expected=exp_crc,
                        crc_received=recv_crc,
                        notes=(
                            f"CRC Mismatch (0x{exp_crc} != 0x{recv_crc}). "
                            f"Bit-flip persistent after {retries} retries."
                        ),
                    )
                    return False, log

        return False, HopLog(
            hop_number=hop_number, relay_node_id=relay_id,
            distance_to_next=distance, latency_ms=latency_ms,
            status="LOST", retransmit_count=retries,
            rssi_dbm=rssi, crc_expected="N/A", crc_received="N/A",
            notes="Unknown failure.",
        )
