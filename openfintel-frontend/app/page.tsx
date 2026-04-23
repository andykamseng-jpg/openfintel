import Navbar from "@/components/Navbar";
import KPICards from "@/components/KPICards";
import UploadPanel from "@/components/UploadPanel";
import FileTable from "@/components/FileTable";
import CoverageTracker from "@/components/CoverageTracker";

export default function Home() {
  const mockData = {
    revenue: 1105550,
    operating_expenses: 837195,
    net_profit: 268355,
    gross_margin: 0.69,
    cashflow: { net_cashflow: 163090 }
  };

  return (
    <div>
      <Navbar />
      <div className="p-6 space-y-6">
        <KPICards data={mockData} />
        <UploadPanel />
        <FileTable />
        <CoverageTracker />
      </div>
    </div>
  );
}