export default function HomePage() {
  return (
    <main className="min-h-screen flex items-center justify-center p-8">
      <div className="text-center space-y-4">
        <h1 className="text-4xl font-semibold">Landloads</h1>
        <p className="text-gray-600">Foundation is up and running.</p>
        <p data-testid="health-link" className="text-sm text-gray-500">
          API base: <code className="bg-gray-100 px-2 py-1 rounded">/api</code>
        </p>
      </div>
    </main>
  );
}
