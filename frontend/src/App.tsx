import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import TopNav from "./components/TopNav";
import Footer from "./components/Footer";
import DashboardPage from "./pages/DashboardPage.tsx";
import MyBotsPage from "./pages/MyBotsPage";

function App() {
    return (
      <BrowserRouter>
        <div className="layout">
          <TopNav />
          <main className="main">
            <Routes>
              <Route path="/" element={<Navigate to="/dashboard" replace />} />
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/my-bots" element={<MyBotsPage />} />
            </Routes>
          </main>
          <Footer />
        </div>
      </BrowserRouter>
    );
  }
  export default App;