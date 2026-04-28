"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
} from "recharts";

export default function MonthlyChart({ data }: { data: any[] }) {
  if (!data || data.length === 0) {
    return (
      <div className="bg-white p-4 rounded-2xl shadow">
        <h2 className="text-lg font-semibold">Monthly Performance</h2>
        <p className="text-gray-500 mt-2">No data available</p>
      </div>
    );
  }

  const formatted = data.map((d) => ({
    ...d,
    month: new Date(d.month).toLocaleString("default", {
      month: "short",
    }),
  }));

  return (
    <div className="bg-white p-4 rounded-2xl shadow">
      <h2 className="text-lg font-semibold mb-4">
        Monthly Performance
      </h2>

      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={formatted}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="month" />
          <YAxis />
          <Tooltip />
          <Legend />

          <Line type="monotone" dataKey="revenue" stroke="#16a34a" />
          <Line type="monotone" dataKey="expenses" stroke="#dc2626" />
          <Line type="monotone" dataKey="profit" stroke="#2563eb" />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}