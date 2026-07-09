import { Outlet } from "react-router-dom";
import Header from "./Header";
import Footer from "./Footer";

const Layout = () => {
  return (
    <div className="min-h-screen text-emd-text flex flex-col">
      <Header />
      <main className="w-full max-w-screen-xl mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-10 flex-1">
        <Outlet />
      </main>
      <Footer />
    </div>
  );
};

export default Layout;
