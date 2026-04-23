type Props = {
  data: any;
};

export default function KPICards({ data }: Props) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
      <Card title="Revenue" value={data.revenue} />
      <Card title="Expenses" value={data.operating_expenses} />
      <Card title="Net Profit" value={data.net_profit} />
      <Card title="Gross Margin" value={data.gross_margin} />
      <Card title="Cash Flow" value={data.cashflow?.net_cashflow || 0} />
    </div>
  );
}

function Card({ title, value }: any) {
  return (
    <div className="p-4 bg-white shadow rounded-xl border">
      <div className="text-gray-500 text-sm">{title}</div>
      <div className="text-xl font-bold mt-1">
        {typeof value === "number" ? `$${value.toLocaleString()}` : value}
      </div>
    </div>
  );
}