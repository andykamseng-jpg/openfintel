type CoverageRow = {
  doc_type: string;
  records: number;
};

export default function CoverageTracker({ data }: { data: CoverageRow[] }) {
  if (!data || data.length === 0) {
    return (
      <div className="bg-white p-4 rounded-2xl shadow">
        <h2 className="text-lg font-semibold mb-2">Data Coverage</h2>
        <p className="text-gray-500">No data coverage available yet.</p>
      </div>
    );
  }

  return (
    <div className="bg-white p-4 rounded-2xl shadow">
      <h2 className="text-lg font-semibold mb-4">Data Coverage</h2>

      {data.map((c, i) => (
        <div key={i} className="text-sm">
          {c.doc_type}: {c.records} records
        </div>
      ))}
    </div>
  );
}
