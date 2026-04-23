export default function CoverageTracker({ data = [] }: any) {
  return (
    <div className="p-4 bg-white rounded shadow">
      <h3>Data Coverage</h3>

      {data.length === 0 ? (
        <p>No data coverage available yet.</p>
      ) : (
        <p>{data.length} days tracked</p>
      )}
    </div>
  );
}