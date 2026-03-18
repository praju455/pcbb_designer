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
        background: "#16100d",
        foreground: "#d8d1c5"
      },
      fontFamily: "JetBrains Mono, monospace",
      fontSize: 12
    });
    const fitAddon = new FitAddon();
    terminal.loadAddon(fitAddon);
    terminal.open(terminalRef.current);
    fitAddon.fit();
    if (!jobId) {
      terminal.writeln("[NEXUS] waiting for a generation run...");
      return () => terminal.dispose();
    }
    const socket = connectToLogs(jobId, (message) => terminal.writeln(`[${message.step.toUpperCase()}] ${message.message}`));
    return () => {
      socket.close();
      terminal.dispose();
    };
  }, [jobId]);

  return <div ref={terminalRef} className="glass rounded-[2rem] p-3" style={{ height: 320 }} />;
}
