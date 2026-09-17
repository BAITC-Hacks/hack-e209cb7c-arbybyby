import { Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import OperatorPage from "./pages/OperatorPage";
import DashboardPage from "./pages/DashboardPage";

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<OperatorPage />} />
        <Route path="/dashboard" element={<DashboardPage />} />
      </Routes>
    </Layout>
  );
}
