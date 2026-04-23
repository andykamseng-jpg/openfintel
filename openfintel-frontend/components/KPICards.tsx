export default function KPICards({ data }: any) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      <Card title="Revenue" value={data?.revenue} />
      <Card title="Expenses" value={data?.expenses} />
      <Card title="Net Profit" value={data?.net_profit} />
      <Card title="Gross Margin" value={(data?.gross_margin ?? 0) * 100 + "%"} />
    </div>
  );
}

function Card({ title, value }: any) {
  return (
    <div className="p-4 bg-white shadow rounded">
      <p className="text-gray-500">{title}</p>
      <h2 className="text-xl font-bold">{value ?? 0}</h2>
    </div>
  );
}