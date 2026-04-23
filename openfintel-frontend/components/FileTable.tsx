export default function FileTable({ files = [] }: any) {
  return (
    <div className="p-4 bg-white rounded shadow">
      <h3 className="mb-2">Recent Uploads</h3>

      {files.length === 0 ? (
        <p>No files uploaded yet</p>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr>
              <th>File</th>
              <th>Type</th>
            </tr>
          </thead>
          <tbody>
            {files.map((f: any, i: number) => (
              <tr key={i}>
                <td>{f.file_name}</td>
                <td>{f.doc_type}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}