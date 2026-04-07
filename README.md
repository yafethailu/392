FPGA-Based Low-Latency Index Engine with Real-Time Anomaly Detection Under Burst Market Traffic

1. Project Overview

Modern electronic financial markets generate extremely high-rate streams of quote updates, especially during periods of elevated volatility such as market open, earnings releases, macroeconomic announcements, or sudden liquidity shocks. These updates arrive in bursts, often referred to as microbursts, where a very large number of quote changes occur within an extremely short time interval.

Traditional software systems process these updates using CPU threads and operating-system scheduling, which introduces non-deterministic latency and tail-latency spikes under burst traffic. This project aims to solve this problem by designing an FPGA-based low-latency streaming analytics engine that computes a continuously updated weighted market index in real time and performs hardware-based anomaly detection directly on the derived index.

The core idea is to build a deterministic hardware pipeline that performs market aggregation, statistical monitoring, burst buffering, and real-time alert generation with bounded latency.

2. High-Level System Architecture

The full system consists of four major stages:

Host Replay → Burst FIFO → Index Engine → Statistical Monitor → Alerts / Displays

Each stage solves a specific real-world systems problem.

The host software replays market data from historical PCAP captures or synthetic traffic and converts it into a simplified binary quote-update record format.

The FPGA receives this stream and first stores incoming records in an input burst FIFO, which absorbs traffic spikes and prevents pipeline stalls during microbursts.

The next stage computes the weighted market index in real time.

The final stage performs anomaly detection on the index time series using rolling-window statistics.

3. Input Data and Quote Updates

Each incoming quote update represents a market change for a tracked symbol.

For this project, each record should contain:

- symbol_id
- bid price
- ask price
- optional timestamp

Example:

AAPL, 19320, 19322

where prices are stored as scaled integers for fixed-point arithmetic.

The FPGA computes the symbol midprice as:

\[
m_i = \frac{bid_i + ask_i}{2}
\]

This midprice becomes the symbol’s contribution to the index.

4. Weighted Index Engine

The weighted index is the primary computed output of the system.

It represents one continuously updated market-wide value derived from multiple symbols.

The full definition is:

\[
I_t = \sum_{i=1}^{N} w_i m_i
\]

where:

N = number of tracked symbols  
w_i = symbol weight  
m_i = current symbol midprice  

This can represent a simplified NASDAQ-like index.

Important Design Suggestion: Incremental Index Update

Rather than recomputing the full summation every tick, the FPGA should use an incremental update architecture.

This is one of the most important design optimizations.

Instead of:

\[
I_t = \sum_i w_i m_i
\]

every update, use:

\[
I_{new} = I_{old} + w_i\left(m_{i,new} - m_{i,old}\right)
\]

This dramatically reduces latency and logic usage.

Only the symbol that changed needs to update the index.

This is likely the best architecture for your capstone.

5. Burst FIFO (Strong Recommendation)

This is one of my strongest suggestions to include.

During market microbursts, quote updates may arrive faster than the computation pipeline can process in a single cycle.

To handle this, the FPGA should include an input FIFO buffer.

Purpose:

- absorb burst traffic
- smooth incoming stream
- prevent dropped records
- preserve deterministic pipeline timing

Architecture:

UART RX → FIFO → parser → index engine

This also lets you study:

- FIFO occupancy
- queue depth under bursts
- latency vs burst size

This gives strong systems-level analysis for your final report.

You should absolutely include performance plots such as:

- burst size vs latency
- burst size vs FIFO occupancy

This strengthens the research component significantly.

6. Rolling Statistical Monitor

After computing the index, the system treats the index as a streaming time series.

Example live index values:

1253.40  
1253.44  
1253.49  
1252.80  
1249.10  

These are the current index values over time.

This is what I meant when I said the “index changed.”

The FPGA stores recent index values in a rolling window.

Power-of-Two Rolling Window (Strong Recommendation)

Use a power-of-two window size.

Recommended:

8  
16  
32  

Best recommendation:

16

This is because the rolling mean becomes a bit shift.

For window size 16:

\[
\mu_t = \frac{1}{16}\sum_{k=0}^{15} I_{t-k}
\]

Division by 16 is simply:

>> 4

which is extremely FPGA-friendly.

This is a very important implementation optimization.

7. Statistical Metrics

The detector computes two quantities.

Velocity

This measures instantaneous market movement.

\[
v_t = I_t - I_{t-1}
\]

Large velocity indicates sudden market movement.

Deviation

This measures distance from recent average.

\[
d_t = \left|I_t - \mu_t\right|
\]

This identifies whether the current market state is far from normal behavior.

8. Threshold Architecture

Use two independent thresholds.

This is very important.

T_v for velocity

T_d for deviation

T_v, T_d

The detection condition becomes:

\[
|v_t| > T_v \text{ and } d_t > T_d
\]

These should be controlled independently using slide switches.

Example:

switches 0–7 → velocity threshold  
switches 8–15 → deviation threshold  

Excellent demo feature.

9. Multiplexed 7-Segment Display (Strong Recommendation)

This is another strong improvement.

Rather than showing only index, use a mode-select switch.

Suggested modes:

mode 0 → index  
mode 1 → velocity  
mode 2 → deviation  
mode 3 → FIFO depth  

This makes the demo much stronger.

Professor can immediately inspect internal states.

Keep this in final architecture.

10. Design Decisions to Think About

These are important discussion points for partner/professor meetings.

Fixed-point precision

Decide scale factor:

x100  
x1000  
x10000  

This affects arithmetic precision.

Symbol universe size

How many symbols?

Suggested:

8–16 symbols

Good balance for capstone scope.

Burst testing methodology

Test normal traffic vs burst traffic.

Example scenarios:

1 tick / cycle  
4 ticks / cycle burst  
16 tick replay burst  
Latency measurement  

Very important final metric.

Measure:

input arrival → index update  
input arrival → LED alert  

This should be part of final plots.
FPGA-Based Low-Latency Index Engine with Real-Time Anomaly Detection Under Burst Market Traffic
1. Project Overview

Modern electronic financial markets generate extremely high-rate streams of quote updates, especially during periods of elevated volatility such as market open, earnings releases, macroeconomic announcements, or sudden liquidity shocks. These updates arrive in bursts, often referred to as microbursts, where a very large number of quote changes occur within an extremely short time interval.

Traditional software systems process these updates using CPU threads and operating-system scheduling, which introduces non-deterministic latency and tail-latency spikes under burst traffic. This project aims to solve this problem by designing an FPGA-based low-latency streaming analytics engine that computes a continuously updated weighted market index in real time and performs hardware-based anomaly detection directly on the derived index.

The core idea is to build a deterministic hardware pipeline that performs market aggregation, statistical monitoring, burst buffering, and real-time alert generation with bounded latency.

2. High-Level System Architecture

The full system consists of four major stages:

Host Replay → Burst FIFO → Index Engine → Statistical Monitor → Alerts / Displays

Each stage solves a specific real-world systems problem.

The host software replays market data from historical PCAP captures or synthetic traffic and converts it into a simplified binary quote-update record format.

The FPGA receives this stream and first stores incoming records in an input burst FIFO, which absorbs traffic spikes and prevents pipeline stalls during microbursts.

The next stage computes the weighted market index in real time.

The final stage performs anomaly detection on the index time series using rolling-window statistics.

3. Input Data and Quote Updates

Each incoming quote update represents a market change for a tracked symbol.

For this project, each record should contain:

symbol_id
bid price
ask price
optional timestamp

Example:

AAPL, 19320, 19322

where prices are stored as scaled integers for fixed-point arithmetic.

The FPGA computes the symbol midprice as:

𝑚
𝑖
=
𝑏
𝑖
𝑑
𝑖
+
𝑎
𝑠
𝑘
𝑖
2
m
i
	​

=
2
bid
i
	​

+ask
i
	​

	​


𝑚
𝑖
=
𝑏
𝑖
𝑑
𝑖
+
𝑎
𝑠
𝑘
𝑖
2
m
i
	​

=
2
bid
i
	​

+ask
i
	​

	​


This midprice becomes the symbol’s contribution to the index.

4. Weighted Index Engine

The weighted index is the primary computed output of the system.

It represents one continuously updated market-wide value derived from multiple symbols.

The full definition is:

𝐼
𝑡
=
∑
𝑖
=
1
𝑁
𝑤
𝑖
𝑚
𝑖
I
t
	​

=
i=1
∑
N
	​

w
i
	​

m
i
	​


𝐼
𝑡
=
∑
𝑖
=
1
𝑁
𝑤
𝑖
𝑚
𝑖
I
t
	​

=∑
i=1
N
	​

w
i
	​

m
i
	​


where:

𝑁
N = number of tracked symbols
𝑤
𝑖
w
i
	​

 = symbol weight
𝑚
𝑖
m
i
	​

 = current symbol midprice

This can represent a simplified NASDAQ-like index.

Important Design Suggestion: Incremental Index Update

Rather than recomputing the full summation every tick, the FPGA should use an incremental update architecture.

This is one of the most important design optimizations.

Instead of:

𝐼
𝑡
=
∑
𝑤
𝑖
𝑚
𝑖
I
t
	​

=∑w
i
	​

m
i
	​


every update, use:

𝐼
𝑛
𝑒
𝑤
=
𝐼
𝑜
𝑙
𝑑
+
𝑤
𝑖
(
𝑚
𝑖
𝑛
𝑒
𝑤
−
𝑚
𝑖
𝑜
𝑙
𝑑
)
I
new
	​

=I
old
	​

+w
i
	​

(m
i
new
	​

−m
i
old
	​

)

𝐼
𝑛
𝑒
𝑤
=
𝐼
𝑜
𝑙
𝑑
+
𝑤
𝑖
(
𝑚
𝑖
𝑛
𝑒
𝑤
−
𝑚
𝑖
𝑜
𝑙
𝑑
)
I
new
	​

=I
old
	​

+w
i
	​

(m
i
new
	​

−m
i
old
	​

)

This dramatically reduces latency and logic usage.

Only the symbol that changed needs to update the index.

This is likely the best architecture for your capstone.

5. Burst FIFO (Strong Recommendation)

This is one of my strongest suggestions to include.

During market microbursts, quote updates may arrive faster than the computation pipeline can process in a single cycle.

To handle this, the FPGA should include an input FIFO buffer.

Purpose:

absorb burst traffic
smooth incoming stream
prevent dropped records
preserve deterministic pipeline timing

Architecture:

UART RX → FIFO → parser → index engine

This also lets you study:

FIFO occupancy
queue depth under bursts
latency vs burst size

This gives strong systems-level analysis for your final report.

You should absolutely include performance plots such as:

burst size vs latency
burst size vs FIFO occupancy

This strengthens the research component significantly.

6. Rolling Statistical Monitor

After computing the index, the system treats the index as a streaming time series.

Example live index values:

1253.40
1253.44
1253.49
1252.80
1249.10

These are the current index values over time.

This is what I meant when I said the “index changed.”

The FPGA stores recent index values in a rolling window.

Power-of-Two Rolling Window (Strong Recommendation)

Use a power-of-two window size.

Recommended:

8
16
32

Best recommendation:

16

This is because the rolling mean becomes a bit shift.

For window size 16:

𝜇
𝑡
=
1
16
∑
𝑘
=
0
15
𝐼
𝑡
−
𝑘
μ
t
	​

=
16
1
	​

k=0
∑
15
	​

I
t−k
	​


𝜇
𝑡
=
1
16
∑
𝑘
=
0
15
𝐼
𝑡
−
𝑘
μ
t
	​

=
16
1
	​

∑
k=0
15
	​

I
t−k
	​


Division by 16 is simply:

>> 4

which is extremely FPGA-friendly.

This is a very important implementation optimization.

7. Statistical Metrics

The detector computes two quantities.

Velocity

This measures instantaneous market movement.

𝑣
𝑡
=
𝐼
𝑡
−
𝐼
𝑡
−
1
v
t
	​

=I
t
	​

−I
t−1
	​


𝑣
𝑡
=
𝐼
𝑡
−
𝐼
𝑡
−
1
v
t
	​

=I
t
	​

−I
t−1
	​


Large velocity indicates sudden market movement.

Deviation

This measures distance from recent average.

𝑑
𝑡
=
∣
𝐼
𝑡
−
𝜇
𝑡
∣
d
t
	​

=∣I
t
	​

−μ
t
	​

∣

𝑑
𝑡
=
∣
𝐼
𝑡
−
𝜇
𝑡
∣
d
t
	​

=∣I
t
	​

−μ
t
	​

∣

This identifies whether the current market state is far from normal behavior.

8. Threshold Architecture

Use two independent thresholds.

This is very important.

𝑇
𝑣
T
v
	​


for velocity

𝑇
𝑑
T
d
	​


for deviation

𝑇
𝑣
,
𝑇
𝑑
T
v
	​

,T
d
	​


The detection condition becomes:

∣
𝑣
𝑡
∣
>
𝑇
𝑣
and
𝑑
𝑡
>
𝑇
𝑑
∣v
t
	​

∣>T
v
	​

andd
t
	​

>T
d
	​


∣
𝑣
𝑡
∣
>
𝑇
𝑣
and
𝑑
𝑡
>
𝑇
𝑑
∣v
t
	​

∣>T
v
	​

andd
t
	​

>T
d
	​


These should be controlled independently using slide switches.

Example:

switches 0–7 → velocity threshold
switches 8–15 → deviation threshold

Excellent demo feature.

9. Multiplexed 7-Segment Display (Strong Recommendation)

This is another strong improvement.

Rather than showing only index, use a mode-select switch.

Suggested modes:

mode 0 → index
mode 1 → velocity
mode 2 → deviation
mode 3 → FIFO depth

This makes the demo much stronger.

Professor can immediately inspect internal states.

Keep this in final architecture.

10. Design Decisions to Think About

These are important discussion points for partner/professor meetings.

Fixed-point precision

Decide scale factor:

x100
x1000
x10000

This affects arithmetic precision.

Symbol universe size

How many symbols?

Suggested:

8–16 symbols

Good balance for capstone scope.

Burst testing methodology

Test normal traffic vs burst traffic.

Example scenarios:

1 tick / cycle
4 ticks / cycle burst
16 tick replay burst
Latency measurement

Very important final metric.

Measure:

input arrival → index update
input arrival → LED alert

This should be part of final plots.
