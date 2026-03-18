import { useConfig } from "../../hooks/useConfig";
import Footer from "./Footer";
import Header from "./Header";
import Sidebar from "./Sidebar";

export default function Layout({ children }) {
  const { healthQuery } = useConfig();

  return (
    <div className="min-h-screen p-4 text-text">
      <div className="mx-auto flex max-w-[1600px] gap-4">
        <Sidebar />
        <main className="flex-1">
          <Header health={healthQuery.data} />
          {children}
          <Footer />
        </main>
      </div>
    </div>
  );
}
