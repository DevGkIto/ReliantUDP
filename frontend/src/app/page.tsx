"use client";

import { useTelemetry } from "./hooks/useTelemetry";
import { useState } from "react";

export default function Dashboard() {
  // Notice we are pulling 'metrics' out of the hook now!
  const { events, isConnected, packetState, metrics } = useTelemetry("ws://localhost:8000/api/ws", 100);
  const [chaos, setChaos] = useState(0);

  // Send the new chaos rate to the FastAPI bridge
  const updateChaos = async (rate: number) => {
    setChaos(rate);
    try {
      await fetch("http://localhost:8000/api/chaos", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ drop_rate: rate }),
      });
    } catch (e) {
      console.error("Failed to update chaos", e);
    }
  };

  // Helper to color the grid squares
  const getStatusColor = (status: string) => {
    if (status === 'acked') return 'bg-green-500 shadow-[0_0_10px_rgba(34,197,94,0.5)]';
    if (status === 'lost') return 'bg-red-500 animate-pulse shadow-[0_0_10px_rgba(239,68,68,0.8)]';
    if (status === 'sent') return 'bg-yellow-500 shadow-[0_0_5px_rgba(234,179,8,0.5)]';
    return 'bg-neutral-800';
  };

  // Get the highest sequence number to size our grid
  const maxSeq = Math.max(0, ...Object.keys(packetState).map(Number));
  const gridBlocks = Array.from({ length: maxSeq + 1 }, (_, i) => i);

  return (
    <main className="min-h-screen bg-neutral-950 text-neutral-200 p-8 font-mono">
      <div className="max-w-6xl mx-auto space-y-6">
        
        {/* Top Bar */}
        <div className="flex justify-between items-center border-b border-green-900/50 pb-4">
          <h1 className="text-2xl font-bold text-green-400 tracking-wider">ARQ TELEMETRY DASHBOARD</h1>
          <div className="flex items-center gap-2">
            <div className={`w-3 h-3 rounded-full ${isConnected ? "bg-green-500 animate-pulse" : "bg-red-500"}`}></div>
            <span className="text-sm font-bold text-green-400">{isConnected ? "LIVE" : "OFFLINE"}</span>
          </div>
        </div>

        {/* Analytics Row */}
        <div className="grid grid-cols-3 gap-6">
          <div className="bg-neutral-900 border border-neutral-800 p-4 rounded shadow-lg">
            <h3 className="text-neutral-500 text-xs font-bold mb-1">DATA VERIFIED</h3>
            <p className="text-2xl text-green-400 font-bold">
              {(metrics.totalBytesAcked / 1024).toFixed(2)} <span className="text-sm text-neutral-500">KB</span>
            </p>
          </div>
          <div className="bg-neutral-900 border border-neutral-800 p-4 rounded shadow-lg">
            <h3 className="text-neutral-500 text-xs font-bold mb-1">PACKETS DROPPED</h3>
            <p className="text-2xl text-red-400 font-bold">
              {metrics.packetsLost} <span className="text-sm text-neutral-500">pkts</span>
            </p>
          </div>
          <div className="bg-neutral-900 border border-neutral-800 p-4 rounded shadow-lg">
            <h3 className="text-neutral-500 text-xs font-bold mb-1">RETRANSMISSIONS</h3>
            <p className="text-2xl text-yellow-500 font-bold">
              {metrics.retransmits} <span className="text-sm text-neutral-500">pkts</span>
            </p>
          </div>
        </div>

        {/* Dashboard Grid Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* LEFT COLUMN: Controls & Log */}
          <div className="space-y-6 flex flex-col h-[60vh]">
            
            {/* Chaos Controller */}
            <div className="bg-neutral-900 border border-neutral-800 p-6 rounded shadow-lg">
              <div className="flex justify-between mb-4">
                <h2 className="text-neutral-400 font-bold text-sm">CHAOS INJECTOR</h2>
                <span className={chaos > 0 ? "text-red-400 font-bold text-sm" : "text-green-400 text-sm"}>{chaos}% LOSS</span>
              </div>
              <input 
                type="range" 
                min="0" max="100" 
                value={chaos} 
                onChange={(e) => updateChaos(parseInt(e.target.value))}
                className="w-full accent-red-500"
              />
            </div>

            {/* Event Log */}
            <div className="bg-neutral-900 border border-neutral-800 p-4 rounded shadow-lg flex-grow flex flex-col overflow-hidden">
              <h2 className="text-neutral-400 font-bold mb-4 border-b border-neutral-800 pb-2 flex justify-between text-sm">
                <span>EVENT STREAM</span>
                <span>(LATEST 100)</span>
              </h2>
              <div className="overflow-y-auto flex-grow space-y-1 pr-2 custom-scrollbar">
                {events.map((ev, idx) => (
                  <div key={idx} className="text-[10px] flex gap-3 hover:bg-neutral-800 p-1 rounded transition-colors">
                    <span className="text-neutral-500 w-16">[{ev.ts ? new Date(ev.ts * 1000).toISOString().split('T')[1].slice(0, -1) : ''}]</span>
                    <span className={`w-24 ${ev.event.includes('timeout') || ev.event.includes('retransmit') ? 'text-red-400 font-bold' : 'text-neutral-300'}`}>
                      {ev.event.toUpperCase()}
                    </span>
                    <span className="text-neutral-400">SQ:{ev.seq}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* RIGHT COLUMN: The Visual Grid */}
          <div className="lg:col-span-2 bg-neutral-900 border border-neutral-800 p-6 rounded shadow-lg h-[60vh] flex flex-col">
            <h2 className="text-neutral-400 font-bold mb-4 border-b border-neutral-800 pb-2 flex justify-between text-sm">
              <span>PACKET MATRIX</span>
              <div className="flex gap-4 text-xs">
                <span className="flex items-center gap-1"><div className="w-2 h-2 bg-yellow-500 rounded-sm"></div> In-Flight</span>
                <span className="flex items-center gap-1"><div className="w-2 h-2 bg-red-500 rounded-sm"></div> Dropped</span>
                <span className="flex items-center gap-1"><div className="w-2 h-2 bg-green-500 rounded-sm"></div> ACKed</span>
              </div>
            </h2>
            
            <div className="overflow-y-auto flex-grow pr-2">
              <div className="flex flex-wrap gap-1 content-start">
                {gridBlocks.map(seq => (
                  <div 
                    key={seq} 
                    title={`Sequence ${seq} | Status: ${packetState[seq] || 'unknown'}`}
                    className={`w-3 h-3 sm:w-4 sm:h-4 rounded-sm transition-all duration-200 ${getStatusColor(packetState[seq])}`}
                  ></div>
                ))}
                {gridBlocks.length === 0 && (
                  <div className="w-full text-center mt-20 text-neutral-600 animate-pulse">
                    Waiting for transfer to begin...
                  </div>
                )}
              </div>
            </div>
          </div>

        </div>
      </div>
    </main>
  );
}