import { Route, Routes } from "react-router-dom";
import Layout from "./components/layout/Layout";
import Dashboard from "./pages/Dashboard";
import Generate from "./pages/Generate";
import Validate from "./pages/Validate";
import Export from "./pages/Export";
import Settings from "./pages/Settings";

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/generate" element={<Generate />} />
        <Route path="/validate" element={<Validate />} />
        <Route path="/export" element={<Export />} />
        <Route path="/settings" element={<Settings />} />
      </Routes>
    </Layout>
  );
}
