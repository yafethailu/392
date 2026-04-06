# 392

---
title: "Low-Latency Weighted Index on FPGA with Real-Time Anomaly Detection"
subtitle: "Combined Capstone Specification — Path A / Path B — DE2-115"
author: "Capstone Design Document"
date: "2026"
---

\newpage

# Executive Summary

This document describes a **single capstone project** formed by combining two ideas: a **streaming weighted index engine** driven by replayed market-data–style updates (host-framed records), and a **hardware anomaly detector** operating on **one derived time series** to keep scope feasible in approximately **ten weeks**.

**Recommended merge (Path A):** compute the **weighted index** in the FPGA, then run **rolling-window statistics** (velocity, deviation from a short-term mean) on **the index only**, with **graded LED alerts** and **7-segment display** output on the **Terasic DE2-115** board.

**Input (system):** Host-replayed **PCAP-derived or synthetic** traffic, reduced to a **simple binary record format** per quote update.

**Output (system):** Continuous **index value**; **anomaly alarm state** and **displayed metrics**; optional **UART log** for latency and verification plots.

\newpage

# 1. Problem Statement

Modern electronic markets emit **high-rate**, **bursty** streams of quote updates. Systems that derive actionable quantities (here: a **weighted index**) must do so with **low latency** and, for many designs, **predictable behavior under microbursts**—not only good average throughput.

Software-only paths introduce **OS scheduling jitter** and less predictable worst-case delay. An **FPGA** can offer **cycle-accurate** control, **deterministic pipelining**, and **on-chip state** for many symbols, with explicit **FIFO depth** and **backpressure** behavior under stress.

Separately, **anomaly-style monitoring** (large short-term move vs. recent baseline) is often needed as a **tripwire** on a derived price series. Doing this in **hardware** next to the index register keeps **alert latency** bounded relative to a thread scheduled on a CPU.

This capstone **does not** implement a full exchange **TCP/network stack** on the FPGA. The **host** replays captures, extracts fields, and streams **framed records** to the FPGA—matching realistic industry splits (smart NIC / feed normalizer vs. FPGA accelerator) while fitting the **academic timeline**.

\newpage

# 2. Target Platform

| Item | Detail |
|------|--------|
| Board | **Terasic DE2-115** (Altera/Intel **Cyclone IV EP4CE115**) |
| Tools | **Quartus Prime** (device family Cyclone IV E), **ModelSim** or Questasim (per course license) |
| Host link | **UART** typical for framed records; optional second UART or logging for metrics |
| I/O for demo | **LEDs** (graded alert), **7-segment displays** (index / deviation / velocity), **slide switches** (runtime thresholds) |

*Note: The DE2-115 exposes **Ethernet PHY** hardware; using a full **MAC + stack** on-chip is **not** assumed in the baseline scope unless the course supplies reference IP and lab time.*

\newpage

# 3. What the "Combined Project" Is

The design is **one pipeline, two stages**, solving two problems:

1. **Aggregation** — Turn many **quote updates** into **one number**: a **weighted index** \(I_t\) that updates when any **tracked** symbol’s mid changes.
2. **Monitoring** — On **one time series** (Path A: **the index**), compute **short-horizon velocity** and **deviation from a rolling mean**, compare to **thresholds**, and drive **visible alerts**.

**Why merge this way:** Anomaly logic on **every** symbol scales as **O(N)** duplicate windows (memory, multipliers, control). Anomaly on **the index only** stays **O(1)** in \(N\) for the detector while still using a **multi-symbol** streaming path for realism.

\newpage

# 4. Inputs and Outputs (System Boundaries)

## 4.1 Host → FPGA (digital input stream)

**Goal:** Deliver an unambiguous stream: “symbol *s* has a new **bid** and **ask**.”

### 4.1.1 Framed record (course-defined)

The team **defines** a fixed binary layout, for example:

| Field | Description |
|-------|----------------|
| `symbol_id` | Small integer \(0 \ldots N-1\) or compact encoding |
| `bid` | Fixed-point / scaled integer |
| `ask` | Fixed-point / scaled integer |
| Optional | Sync byte, length, simple CRC, `valid` framing |

**Source of records:**

- **PCAP replay:** Software parses packets and **extracts** quote fields, then **emits** framed records (recommended for realism).
- **Synthetic:** Script generates byte-identical records for golden testing.

**Rationale:** Raw **SoupBinTCP / TCP** termination on the FPGA is a **large** separate project; the host **normalizes** external formats into this **academic** interface.

## 4.2 FPGA → Human (DE2-115 outputs)

| Output | Purpose |
|--------|---------|
| **7-segment displays** | Show e.g. **scaled index**, **deviation**, or **velocity** (pick what reads best live) |
| **LEDs** | **Graded anomaly alert** (e.g. green / yellow / red bands from threshold breaches) |
| **Slide switches** | **Runtime thresholds** \(T_v\), \(T_d\) (and mode bits if needed) |

## 4.3 Optional FPGA → Host (logging)

Same **UART** (or alternate channel) to stream tuples for plots:

- Cycle or timestamp
- Current **index**
- Alert level
- Optional per-message **latency** in cycles

\newpage

# 5. Financial / Numeric Definitions

## 5.1 Midprice

For symbol \(i\) with best bid \(B_i\) and best ask \(A_i\) (in fixed-point integers):

\[
m_i = \frac{B_i + A_i}{2}
\]

In RTL, often implemented as **arithmetic right shift** with a documented scale (e.g. tick size × \(10^k\)).

## 5.2 Weighted index

Let weights \(w_i\) satisfy \(\sum_i w_i = 1\) in real arithmetic; on FPGA use **fixed-point weights** (e.g. Q16 or sum to a power of two for cheap normalization).

\[
I = \sum_i w_i \, m_i
\]

## 5.3 Incremental update (efficient)

When only symbol \(k\) updates, avoid recomputing the full sum each time. Store previous mid \(m_k^{\mathrm{old}}\) (or stored contribution \(C_k = w_k m_k\)).

\[
I \leftarrow I - w_k m_k^{\mathrm{old}} + w_k m_k^{\mathrm{new}}
\]

Then update stored state for symbol \(k\).

\newpage

# 6. FPGA Internal Architecture (Detailed)

## 6.1 Stage 1 — Ingress, parse, filter

| Step | Function |
|------|-----------|
| Ingress | UART RX → byte FIFO → frame assembler |
| Parse | Extract `symbol_id`, `bid`, `ask` |
| Filter | If `symbol_id` not in **index universe**, **drop** (no state / index change) |

**Goal:** Pay only for symbols that contribute to \(I\).

## 6.2 Stage 2 — Per-symbol state and mid

For each universe symbol, storage holds latest \(B_i, A_i\) (or only \(m_i\)). On accepted update, compute \(m_i\) in fixed-point.

## 6.3 Stage 3 — Weighted index

Maintain running \(I\) using **incremental** updates. Initialize \(I\) after first valid mids (e.g. cold-start rule: require all symbols touched once, or use last known mids and document).

## 6.4 Stage 4 — Latency and microburst instrumentation

Per accepted record:

- Latch **free-running cycle counter** at **record accepted**.
- Latch again when **index update** completes (same clock domain as design permits).

**Difference** → processing delay in **cycles**; multiply by clock period for **nanoseconds**. The host replays **bursts** to characterize **average vs tail** delay and **FIFO stress**.

## 6.5 Stage 5 — Anomaly detection (Project 2 style, single stream)

### Path A (recommended)

**Input series:** \(I_0, I_1, \ldots\) each time the **index changes** (or on a fixed cadence—**choose one rule** and document it).

**Typical features (fixed-point):**

- **Rolling mean** \(\mu_t\) over window \(W\) on **levels** \(I_t\) or on **returns** \(\Delta I_t = I_t - I_{t-1}\).
- **Deviation:** \(d_t = I_t - \mu_t\) (or demeaned returns).
- **Velocity:** e.g. \(v_t = I_t - I_{t-1}\), or short EMA of \(|\Delta I|\).

**Example alert rule (illustrative):**

\[
|v_t| > T_v \quad \land \quad |d_t| > T_d \quad \Rightarrow \quad \text{escalate LED state}
\]

\(T_v, d_d\) derived from **slide switches** (quantized) for demo.

**Important:** This is a **transparent tripwire**, not a claim of optimal crash prediction—appropriate for academic scope.

### Path B (optional variant)

Same **index pipeline** for the finance story, but the **detector** runs on **one constituent** \(m_{K,t}\) (e.g. largest weight). **Harder to explain** for audiences: two focal series (constituent vs index) unless the report is very clear.

\newpage

# 7. Path A vs Path B (Comparison)

| Aspect | Path A — Anomaly on **index** | Path B — Anomaly on **one stock** |
|--------|--------------------------------|-------------------------------------|
| Detector complexity | **One** window, one mean pipeline | **One** window (same HW), different input tap |
| Narrative | “Alert on **portfolio-level** dislocation” | “Alert on **flagship** name during replay” |
| Dilution | Large move in one name may be diluted if others flat | Localized to one ticker |
| Demo clarity | **Simplest** to present | Needs careful labeling in UI/report |

**Recommendation:** **Path A** as default; Path B only if the team wants a specific **flash-crash** story on one ticker and accepts extra exposition.

\newpage

# 8. Scope Caps (Explicit)

To finish in **~10 weeks** on **DE2-115**:

| Cap | Rationale |
|-----|-----------|
| **One** logical quote / record type | Limits parser FSM and verification |
| **Modest universe** (e.g. **8–32** symbols) | BRAM/register budget and incremental update debugging |
| **Anomaly on one series** (index in Path A) | Avoids **N** rolling windows |
| Host does PCAP → framed records | Avoids full TCP on FPGA |
| Fixed-point throughout | Predictable RTL, no floating-point cores required |

\newpage

# 9. Deliverables Checklist

| Deliverable | Description |
|-------------|-------------|
| RTL | Verilog or SystemVerilog: UART/framing, parse/filter, mids, incremental index, anomaly, LED/7-seg/switch glue |
| Testbench | ModelSim: golden vectors from host or Python reference |
| Host tools | PCAP or synthetic **replay**; **software reference** index + optional reference anomaly |
| Metrics | Resource utilization (Quartus), **Fmax**, **throughput**, latency plots under burst |
| Demo | Live DE2-115: index + graded alert under replay |
| Report | Diagrams, message format spec, fixed-point scales, limitations |

\newpage

# 10. Suggested Milestones (10 Weeks)

| Week | Focus |
|------|--------|
| 1 | Freeze **record format**, weights, universe size; reference model outputs golden files |
| 2–3 | UART + parser + filter + per-symbol mids (simulation) |
| 4–5 | Incremental **weighted index**; match software reference |
| 6 | Ingress FIFO + **cycle-accurate latency** counters; burst tests in sim |
| 7 | Anomaly block + switch thresholds + LED / 7-seg integration |
| 8 | Quartus synthesis, timing, pin assignments for DE2-115 |
| 9 | End-to-end replay + plots + corner cases (bad length, unknown symbol) |
| 10 | Final report, poster, demo polish |

\newpage

# 11. Compliance and Data (Academic)

- Use **publicly documented** PCAP or **synthetic** traffic; **cite** dataset URL, date, and license in the report.
- Do not submit **employer proprietary** code, specifications, or non-public data as part of graded work unless explicitly permitted.
- Index **weights** and **universe** are **project parameters**, not claims about a real published index unless you license and document them.

\newpage

# 12. One-Sentence Project Goal (Proposal-Ready)

**Input:** Replay of quote updates as **host-framed binary records**. **Output:** A **continuous fixed-point weighted index** on the FPGA, **measured processing latency** under burst replay, and **real-time graded anomaly indication** when short-term **index motion** exceeds **switch-programmed thresholds**, with verification against a **software reference**.

\newpage

# References (Placeholders — Replace With Your Citations)

- Terasic DE2-115 documentation and user manual.
- Intel Quartus Prime documentation, Cyclone IV device handbook.
- Public market microstructure texts (e.g. Harris, Hasbrouck) for **motivation only**.
- SEC / academic reports on market events if used for **narrative** only (Path B / flash-crash context): cite properly.
- IEEE papers suggested by the course (anomaly / market monitoring): cite if used.

---

*End of document.*
