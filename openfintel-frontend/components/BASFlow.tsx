"use client";

import { useEffect, useState } from "react";

type GraphData = Record<string, number>;

const EDITABLE_NODES = [
  "units",
  "price",
  "variable_costs",
  "fixed_costs",
  "pos",
  "supplier_payments",
];

export default function BASFlow({ data }: { data: GraphData }) {
  const [graph, setGraph] = useState<GraphData>({});
  const [editingNode, setEditingNode] = useState<string | null>(null);
  const [inputValue, setInputValue] = useState("");

  useEffect(() => {
    setGraph(data);
  }, [data]);

  const handleEdit = (nodeId: string, value: number) => {
    if (!EDITABLE_NODES.includes(nodeId)) return;
    setEditingNode(nodeId);
    setInputValue(String(value));
  };

  const handleSubmit = async () => {
    if (!editingNode) return;

    const newValue = parseFloat(inputValue);
    if (isNaN(newValue)) {
      setEditingNode(null);
      return;
    }

    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/simulate`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            overrides: { [editingNode]: newValue },
          }),
        }
      );

      const result = await res.json();
      if (result?.graph) setGraph(result.graph);

    } catch (err) {
      console.error("Simulation error:", err);
    }

    setEditingNode(null);
  };

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
      {Object.entries(graph).map(([key, value]) => {
        const isEditable = EDITABLE_NODES.includes(key);

        return (
          <div
            key={key}
            className={`p-4 rounded-2xl shadow ${
              isEditable ? "bg-blue-50 cursor-pointer" : "bg-gray-100"
            }`}
            onClick={() => handleEdit(key, value)}
          >
            <div className="text-sm text-gray-500">
              {key.replace(/_/g, " ")}
            </div>

            {editingNode === key ? (
              <input
                autoFocus
                type="number"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onBlur={handleSubmit}
                onKeyDown={(e) => {
                  if (e.key === "Enter") handleSubmit();
                }}
                className="mt-2 w-full border rounded px-2 py-1"
              />
            ) : (
              <div className="text-xl font-bold mt-2">
                {Number(value).toLocaleString()}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}