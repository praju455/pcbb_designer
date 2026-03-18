import { useConfig } from "../../hooks/useConfig";
import Footer from "./Footer";
import Header from "./Header";

export default function Layout({ children }) {
  const { healthQuery } = useConfig();

  return (
    <div className="min-h-screen px-4 py-5 text-text md:px-6">
      <div className="mx-auto max-w-[1480px]">
        <Header health={healthQuery.data} healthQuery={healthQuery} />
        <main className="editorial-panel min-h-[calc(100vh-14rem)] rounded-[2.5rem] px-5 py-8 md:px-8 md:py-10">
          {children}
          <Footer />
        </main>
      </div>
    </div>
  );
}
