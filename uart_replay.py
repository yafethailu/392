"""
uart_replay.py   (path B: 7-byte XDP-derived frames)

Reads a binary file produced by xdp_quote_parser_fpga.py (uart_frames.bin) and
streams it byte-for-byte out a serial port to the FPGA.

Wire format (per record, 7 bytes total):

    byte[0]            = 0xAA                          sync
    byte[1]            = {4'b0, sym[3:0]}              high nibble zero
    byte[2]            = bid_q9[19:12]
    byte[3]            = bid_q9[11: 4]
    byte[4][7:4]       = bid_q9[ 3: 0]
    byte[4][3:0]       = ask_q9[19:16]
    byte[5]            = ask_q9[15: 8]
    byte[6]            = ask_q9[ 7: 0]

Q11.9 means the 20-bit price field is USD * 2^9 = USD * 512. To decode for
human display: usd = q9 / 512.0.

Usage:
    python uart_replay.py --port COM4 --bin uart_frames.bin
    python uart_replay.py --port /dev/ttyUSB0 --bin uart_frames.bin --delay-us 100
    python uart_replay.py --port COM4 --bin uart_frames.bin --preview 4 --no-send
"""

import argparse
import sys
import time
from pathlib import Path

try:
    import serial
except ImportError as exc:
    raise SystemExit("pyserial is required. Install with: pip install pyserial") from exc


RECORD_BYTES   = 7
SYNC_BYTE      = 0xAA
PRICE_SCALE    = 512          # USD * 2^9
SYM_LOCAL_NAMES = {
    1: "AAPL", 2: "TSLA", 3: "GOOGL", 4: "NFLX", 5: "NVDA",
    6: "MRVL", 7: "AMD",   8: "QCOM",  9: "MSFT", 10: "PLTR",
}


def decode_record(rec: bytes) -> tuple[int, int, int]:
    """Return (sym, bid_q9, ask_q9) for a 7-byte record. Raises on bad sync."""
    if len(rec) != RECORD_BYTES:
        raise ValueError(f"record must be {RECORD_BYTES} bytes, got {len(rec)}")
    if rec[0] != SYNC_BYTE:
        raise ValueError(f"missing sync 0xAA, got 0x{rec[0]:02X}")

    # Glue the 6 payload bytes into a 48-bit integer, MSB-first (matches the FPGA).
    val = 0
    for b in rec[1:]:
        val = (val << 8) | b

    sym    = (val >> 40) & 0xF
    bid_q9 = (val >> 20) & 0xFFFFF
    ask_q9 = (val >>  0) & 0xFFFFF
    return sym, bid_q9, ask_q9


def hex_preview(data: bytes, n_records: int) -> str:
    lines = []
    n = min(n_records, len(data) // RECORD_BYTES)
    for i in range(n):
        rec = data[i * RECORD_BYTES:(i + 1) * RECORD_BYTES]
        try:
            sym, bid_q9, ask_q9 = decode_record(rec)
            sym_name = SYM_LOCAL_NAMES.get(sym, f"id{sym}")
            hexs = " ".join(f"{b:02X}" for b in rec)
            lines.append(
                f"  rec[{i:>4}] {hexs}  ->  sym={sym:2d} ({sym_name:5s}) "
                f"bid=${bid_q9/PRICE_SCALE:>9.4f} (q9={bid_q9:>7}) "
                f"ask=${ask_q9/PRICE_SCALE:>9.4f} (q9={ask_q9:>7})"
            )
        except ValueError as e:
            hexs = " ".join(f"{b:02X}" for b in rec)
            lines.append(f"  rec[{i:>4}] {hexs}  ->  BAD: {e}")
    return "\n".join(lines)


def validate_file(data: bytes) -> tuple[int, list[int]]:
    """Walk every record; return (n_records, list of bad indices)."""
    if len(data) % RECORD_BYTES != 0:
        raise ValueError(
            f"file size {len(data)} not divisible by record size {RECORD_BYTES}"
        )
    n = len(data) // RECORD_BYTES
    bad = []
    for i in range(n):
        if data[i * RECORD_BYTES] != SYNC_BYTE:
            bad.append(i)
    return n, bad


def main() -> None:
    ap = argparse.ArgumentParser(description="Replay path B UART frames to the FPGA.")
    ap.add_argument("--port", required=True, help="Serial port, e.g. COM4 or /dev/ttyUSB0")
    ap.add_argument("--baud", type=int, default=115200, help="Baud rate (default 115200)")
    ap.add_argument("--bin",  required=True, help="uart_frames.bin from xdp_quote_parser_fpga.py")
    ap.add_argument("--record-bytes", type=int, default=RECORD_BYTES,
                    help=f"Bytes per record (default {RECORD_BYTES})")
    ap.add_argument("--delay-us", type=int, default=0,
                    help="Inter-record delay in microseconds (best-effort; OS-limited)")
    ap.add_argument("--preview", type=int, default=4,
                    help="Decode and print this many records before sending (0 = none)")
    ap.add_argument("--no-send", action="store_true",
                    help="Validate + preview only; do not open the serial port")
    ap.add_argument("--max-records", type=int, default=0,
                    help="If > 0, only send the first N records")
    args = ap.parse_args()

    data = Path(args.bin).read_bytes()
    if len(data) == 0:
        sys.exit("ERROR: input binary is empty")

    n_records, bad_records = validate_file(data)

    print(f"File           : {args.bin}")
    print(f"Total bytes    : {len(data)}")
    print(f"Record bytes   : {args.record_bytes}")
    print(f"Total records  : {n_records}")
    if bad_records:
        print(f"WARNING        : {len(bad_records)} records have bad sync byte "
              f"(first few indices: {bad_records[:5]})")

    if args.max_records and args.max_records < n_records:
        n_records = args.max_records
        data = data[: n_records * args.record_bytes]
        print(f"Truncated to   : {n_records} records (per --max-records)")

    if args.preview > 0:
        print("Preview:")
        print(hex_preview(data, args.preview))

    if args.no_send:
        print("\n--no-send set; exiting without opening serial port.")
        return

    print(f"\nOpening {args.port} @ {args.baud} baud ...")
    with serial.Serial(args.port, args.baud, timeout=1, write_timeout=5) as ser:
        ser.reset_input_buffer()
        ser.reset_output_buffer()

        t0 = time.time()
        for i in range(n_records):
            start = i * args.record_bytes
            end = start + args.record_bytes
            ser.write(data[start:end])
            if args.delay_us > 0:
                # Note: time.sleep is not actually µs-accurate on most OSes.
                time.sleep(args.delay_us / 1_000_000.0)

            if (i + 1) % 1000 == 0:
                print(f"  sent {i + 1}/{n_records} records")

        ser.flush()
        elapsed = time.time() - t0

    bits = n_records * args.record_bytes * 10  # 8 data + 1 start + 1 stop
    print("\nReplay complete.")
    print(f"  records sent : {n_records}")
    print(f"  bytes sent   : {n_records * args.record_bytes}")
    print(f"  elapsed      : {elapsed:.3f} s")
    if elapsed > 0:
        print(f"  effective    : {bits / elapsed:,.0f} bits/s "
              f"(line rate {args.baud:,} bits/s)")


if __name__ == "__main__":
    main()