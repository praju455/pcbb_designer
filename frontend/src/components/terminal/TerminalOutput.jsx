import { useEffect, useRef } from "react";
import { Terminal } from "xterm";
import { FitAddon } from "xterm-addon-fit";
import "xterm/css/xterm.css";
import { connectToLogs } from "../../api/client";

export default function TerminalOutput({ jobId }) {
  const terminalRef = useRef(null);

  useEffect(() => {
    if (!terminalRef.current) return undefined;
    const terminal = new Terminal({
      theme: {
        background: "#05070d",
        foreground: "#22c55e"
      },
      fontFamily: "JetBrains Mono, monospace",
      fontSize: 12
    });
    const fitAddon = new FitAddon();
    terminal.loadAddon(fitAddon);
    terminal.open(terminalRef.current);
    fitAddon.fit();
    if (!jobId) {
      terminal.writeln("[NEXUS] waiting for job...");
      return () => terminal.dispose();
    }
    const socket = connectToLogs(jobId, (message) => terminal.writeln(`[${message.step.toUpperCase()}] ${message.message}`));
    return () => {
      socket.close();
      terminal.dispose();
    };
  }, [jobId]);

  return <div ref={terminalRef} className="glass rounded-3xl p-3" style={{ height: 320 }} />;
}
