module weights_rom (
    input  wire [15:0] symbol_id,
    output reg  [15:0] weight
);
    always @(*) begin
        case (symbol_id)
            16'd0: weight = 16'd3061; // AAPL
            16'd1: weight = 16'd856;  // TSLA
            16'd2: weight = 16'd845;  // GOOGL
            16'd3: weight = 16'd502;  // NFLX
            16'd4: weight = 16'd1193; // NVDA
            16'd5: weight = 16'd167;  // MRVL
            16'd6: weight = 16'd390;  // AMD
            16'd7: weight = 16'd279;  // QCOM
            16'd8: weight = 16'd2623; // MSFT
            16'd9: weight = 16'd84;   // PLTR
            default: weight = 16'd0;
        endcase
    end
endmodule
