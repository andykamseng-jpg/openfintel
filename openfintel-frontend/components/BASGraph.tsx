"use client";

export default function BASGraph({ data }: any) {
  if (!data) return null;

  return (
    <div className="bg-white p-4 rounded-2xl shadow border">
      <h2 className="text-lg font-semibold mb-4">
        Business Flow (BAS)
      </h2>

      <div className="space-y-2">

        <div className="flex justify-between">
          <span>Revenue</span>
          <span className="text-green-600">
            ${data.revenue?.toLocaleString()}
          </span>
        </div>

        <div className="flex justify-between">
          <span>COGS</span>
          <span className="text-red-500">
            -${data.cogs?.toLocaleString()}
          </span>
        </div>

        <div className="flex justify-between">
          <span>Operating Expenses</span>
          <span className="text-red-500">
            -${data.operating_expenses?.toLocaleString()}
          </span>
        </div>

        <hr />

        <div className="flex justify-between font-bold">
          <span>Net Profit</span>
          <span className="text-green-600">
            ${data.net_profit?.toLocaleString()}
          </span>
        </div>

      </div>
    </div>
  );
}