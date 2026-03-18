import { Suspense, lazy } from "react";
import { Route, Routes } from "react-router-dom";
import Layout from "./components/layout/Layout";

const Dashboard = lazy(() => import("./pages/Dashboard"));
const Generate = lazy(() => import("./pages/Generate"));
const Validate = lazy(() => import("./pages/Validate"));
const Export = lazy(() => import("./pages/Export"));
const Settings = lazy(() => import("./pages/Settings"));

export default function App() {
  return (
    <Layout>
      <Suspense fallback={<div className="rounded-[2rem] border border-border/70 bg-white/70 px-6 py-10 text-muted">Loading workspace...</div>}>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/generate" element={<Generate />} />
          <Route path="/validate" element={<Validate />} />
          <Route path="/export" element={<Export />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </Suspense>
    </Layout>
  );
}
