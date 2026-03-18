import { Download } from "lucide-react";

export default function FileDownload({ label, path }) {
  return (
    <a href={path} className="flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm transition hover:border-primary/60 hover:bg-primary/10">
      <Download size={16} />
      <span>{label}</span>
    </a>
  );
}
