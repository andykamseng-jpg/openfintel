export default function FileTable({ files }: { files: any[] }) {
  if (!files.length) {
    return (
      <div className="bg-white p-4 rounded-2xl shadow border">
        <h2 className="text-lg font-semibold mb-2">Recent Uploads</h2>
        <p className="text-gray-500">No files uploaded yet</p>
      </div>
    );
  }

  return (
    <div className="bg-white p-4 rounded-2xl shadow border">
      <h2 className="text-lg font-semibold mb-4">Recent Uploads</h2>

      <table className="w-full text-sm">
        <thead>
          <tr className="text-left border-b">
            <th>Filename</th>
            <th>Type</th>
            <th>Rows</th>
            <th>Inserted</th>
          </tr>
        </thead>

        <tbody>
          {files.map((f, i) => (
            <tr key={i} className="border-b">
              <td>{f.filename}</td>
              <td>{f.doc_type}</td>
              <td>{f.rows_uploaded}</td>
              <td>{f.rows_inserted}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}