"use client";

export default function BASFlow({ data }: any) {
  if (!data) return null;

  return (
    <div className="border rounded p-4 bg-white shadow">
      <h2 className="text-lg font-bold mb-4">
        Business Activity Flow
      </h2>

      <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">

        <Box title="Revenue" value={data.revenue} />
        <Box title="COGS" value={data.cogs} />
        <Box title="Gross Margin" value={data.gross_margin} />

        <Box title="Operating Expenses" value={data.operating_expenses} />
        <Box title="Net Profit" value={data.net_profit} />
        <Box title="Cash Flow" value={data.cash_flow} />

      </div>
    </div>
  );
}

function Box({ title, value }: any) {
  return (
    <div className="p-3 border rounded bg-gray-50">
      <div className="text-gray-500">{title}</div>
      <div className="text-lg font-semibold">
        {Number(value || 0).toLocaleString()}
      </div>
    </div>
  );
}