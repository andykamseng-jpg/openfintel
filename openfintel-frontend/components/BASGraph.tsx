"use client";

import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  Handle,
  Position,
} from "reactflow";
import "reactflow/dist/style.css";

// 🎯 Custom Node (SaaS Card Style)
function KPIBox({ data }: any) {
  const color = getColor(data.label, data.value);

  return (
    <div className="bg-white rounded-2xl shadow-md px-4 py-3 border w-[160px]">
      <div className="text-xs text-gray-500">{data.label}</div>
      <div className={`text-lg font-bold ${color}`}>
        {format(data.value)}
      </div>

      <Handle type="target" position={Position.Left} />
      <Handle type="source" position={Position.Right} />
    </div>
  );
}

const nodeTypes = {
  kpi: KPIBox,
};

export default function BASGraph({ data }: any) {
  if (!data) return null;

  const nodes = [
    {
      id: "revenue",
      type: "kpi",
      position: { x: 50, y: 50 },
      data: { label: "Revenue", value: data.revenue },
    },
    {
      id: "cogs",
      type: "kpi",
      position: { x: 250, y: 200 },
      data: { label: "COGS", value: data.cogs },
    },
    {
      id: "gross",
      type: "kpi",
      position: { x: 350, y: 50 },
      data: { label: "Gross Margin", value: data.gross_margin },
    },
    {
      id: "opex",
      type: "kpi",
      position: { x: 550, y: 200 },
      data: { label: "Operating Expenses", value: data.operating_expenses },
    },
    {
      id: "profit",
      type: "kpi",
      position: { x: 650, y: 50 },
      data: { label: "Net Profit", value: data.net_profit },
    },
    {
      id: "cash",
      type: "kpi",
      position: { x: 850, y: 50 },
      data: { label: "Cash Flow", value: data.cash_flow },
    },
  ];

  const edges = [
    edge("revenue", "gross"),
    edge("cogs", "gross"),
    edge("gross", "profit"),
    edge("opex", "profit"),
    edge("profit", "cash"),
  ];

  return (
    <div className="h-[420px] rounded-xl border bg-gray-50">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
      >
        <MiniMap />
        <Controls />
        <Background gap={16} />
      </ReactFlow>
    </div>
  );
}

// 🎨 Edge Styling
function edge(source: string, target: string) {
  return {
    id: `${source}-${target}`,
    source,
    target,
    animated: true,
    style: { strokeWidth: 2 },
  };
}

// 🎨 Color Logic
function getColor(label: string, value: number) {
  if (label.includes("Revenue")) return "text-green-600";
  if (label.includes("Profit") || label.includes("Cash")) {
    return value >= 0 ? "text-green-600" : "text-red-600";
  }
  if (label.includes("COGS") || label.includes("Expenses")) {
    return "text-red-500";
  }
  return "text-gray-800";
}

// 🔢 Format
function format(num: number) {
  return Number(num || 0).toLocaleString();
}