"use client";

export default function BASGraph({ data }: any) {
  if (!data) {
    return (
      <div className="border p-4 rounded">
        <h2 className="text-lg font-semibold mb-2">Business Flow</h2>
        <p>No data available</p>
      </div>
    );
  }

  const {
    revenue = 0,
    cogs = 0,
    operating_expenses = 0,
    net_profit = 0,
  } = data;

  return (
    <div className="border p-4 rounded">
      <h2 className="text-lg font-semibold mb-4">Business Flow (BAS)</h2>

      <div className="space-y-2">

        <div className="flex justify-between">
          <span>Revenue</span>
          <span className="text-green-600 font-semibold">
            ${revenue.toLocaleString()}
          </span>
        </div>

        <div className="flex justify-between">
          <span>COGS</span>
          <span className="text-red-500">
            -${cogs.toLocaleString()}
          </span>
        </div>

        <div className="flex justify-between">
          <span>Operating Expenses</span>
          <span className="text-red-500">
            -${operating_expenses.toLocaleString()}
          </span>
        </div>

        <hr />

        <div className="flex justify-between text-lg font-bold">
          <span>Net Profit</span>
          <span className={net_profit >= 0 ? "text-green-600" : "text-red-600"}>
            ${net_profit.toLocaleString()}
          </span>
        </div>

      </div>
    </div>
  );
}