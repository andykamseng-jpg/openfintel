import React, { useState } from "react";
import axios from "axios";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer
} from "recharts";

function App() {
  const [data, setData] = useState(null);

  const handleUpload = async (e) => {
    const file = e.target.files[0];

    const formData = new FormData();
    formData.append("file", file);
    formData.append("doc_type", "income_statement");

    const res = await axios.post("http://127.0.0.1:8000/api/upload", formData);

    setData(res.data);
  };

  const chartData = data
    ? Object.keys(data.category_breakdown).map((key) => ({
        name: key,
        value: Math.abs(data.category_breakdown[key])
      }))
    : [];

  return (
    <div style={{ padding: 30 }}>
      <h1>Financial Dashboard</h1>

      <input type="file" onChange={handleUpload} />

      {data && (
        <>
          <div style={{ display: "flex", gap: 20, marginTop: 30 }}>
            <Card title="Revenue" value={data.revenue} />
            <Card title="Expenses" value={data.operating_expenses} />
            <Card title="Net Profit" value={data.net_profit} />
            <Card title="Margin %" value={(data.gross_margin * 100).toFixed(1)} />
          </div>

          <div style={{ marginTop: 50 }}>
            <h3>Category Breakdown</h3>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={chartData}>
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="value" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </>
      )}
    </div>
  );
}

function Card({ title, value }) {
  return (
    <div style={{
      padding: 20,
      border: "1px solid #ddd",
      borderRadius: 10,
      width: 200
    }}>
      <h4>{title}</h4>
      <h2>${value.toLocaleString()}</h2>
    </div>
  );
}

export default App;